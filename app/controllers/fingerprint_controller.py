from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel
import os, shutil, uuid, logging, base64

from .. import models, schemas
from ..database import get_db

# --- KONFIGURASI LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("backend_biometric.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BiometricRouter")

router = APIRouter(prefix="/finger", tags=["Users & Biometrics"])

PROFILE_UPLOAD_DIR = "uploads/profiles"
os.makedirs(PROFILE_UPLOAD_DIR, exist_ok=True)

# Schema Requests
class FingerprintRequest(BaseModel):
    finger_id: int
    finger_name: str
    template_data: str # Menerima string Base64 dari Android

# --- 1. SIMPAN PROFIL USER (UPSERT LOGIC) ---
@router.post("/register-profile", response_model=schemas.StandardResponse[schemas.UserResponse])
async def register_user_profile(
    nik: str = Form(...),
    nama_lengkap: str = Form(...),
    jenis_kelamin: str = Form(...),
    tempat_lahir: str = Form(...),
    tanggal_lahir: date = Form(...),
    alamat: str = Form(...),
    foto_profil: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    logger.info(f"Mencoba registrasi/update profil NIK: {nik}")
    
    # Cek apakah user dengan NIK tersebut sudah ada (Menggunakan PemiluDPT)
    db_user = db.query(models.PemiluDPT).filter(models.PemiluDPT.nik == nik).first()

    # Konversi input Android ("Laki-laki" / "Perempuan") ke Enum Database ("L" / "P")
    jk_db = 'L' if jenis_kelamin.strip().lower() == 'laki-laki' else 'P' if jenis_kelamin.strip().lower() == 'perempuan' else ''

    saved_foto_path = None
    if foto_profil and foto_profil.filename:
        try:
            # Jika update dan ada foto lama, hapus file lamanya dari storage
            if db_user and hasattr(db_user, 'foto_profil') and db_user.foto_profil:
                old_file_path = os.path.join(os.getcwd(), db_user.foto_profil)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
                    logger.info(f"Foto lama NIK {nik} dihapus.")

            ext = foto_profil.filename.split(".")[-1]
            unique_filename = f"profile_{nik}_{uuid.uuid4().hex[:5]}.{ext}"
            relative_path = f"uploads/profiles/{unique_filename}"
            full_path = os.path.join(PROFILE_UPLOAD_DIR, unique_filename)
            
            with open(full_path, "wb") as buffer:
                shutil.copyfileobj(foto_profil.file, buffer)
            saved_foto_path = relative_path
        except Exception as e:
            logger.error(f"Gagal simpan foto: {e}")

    try:
        if db_user:
            # --- LOGIKA UPDATE ---
            logger.info(f"NIK {nik} ditemukan. Memperbarui data user ID: {db_user.id}")
            db_user.nama_penduduk = nama_lengkap  # Sesuai model DB baru
            db_user.jenis_kelamin = jk_db         # Sesuai Enum DB baru
            db_user.tempat_lahir = tempat_lahir
            db_user.tanggal_lahir = tanggal_lahir
            db_user.alamat = alamat
            if saved_foto_path and hasattr(db_user, 'foto_profil'):
                db_user.foto_profil = saved_foto_path
            
            message = "Profil berhasil diperbarui"
            user_to_return = db_user
        else:
            # --- LOGIKA INSERT ---
            logger.info(f"NIK {nik} tidak ditemukan. Membuat user baru.")
            new_user = models.PemiluDPT(
                nik=nik, 
                nama_penduduk=nama_lengkap,       # Sesuai model DB baru
                jenis_kelamin=jk_db,              # Sesuai Enum DB baru
                tempat_lahir=tempat_lahir, 
                tanggal_lahir=tanggal_lahir,
                alamat=alamat
            )
            if saved_foto_path and hasattr(new_user, 'foto_profil'):
                new_user.foto_profil = saved_foto_path
                
            db.add(new_user)
            message = "Profil berhasil disimpan"
            user_to_return = new_user

        db.commit()
        db.refresh(user_to_return)
        logger.info(f"User {nama_lengkap} (ID: {user_to_return.id}) berhasil diproses.")
        return {"success": True, "message": message, "data": schemas.UserResponse.model_validate(user_to_return)}

    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Gagal menyimpan ke database")

# --- 2. SIMPAN SIDIK JARI ---
@router.post("/{pemilu_dpt_id}/fingerprint", response_model=schemas.StandardResponse[None])
async def save_fingerprint_template(
    pemilu_dpt_id: int,  # Disesuaikan menjadi pemilu_dpt_id
    request: FingerprintRequest, 
    db: Session = Depends(get_db)
):
    logger.info(f"Menyimpan sidik jari {request.finger_name} untuk PemiluDPT ID: {pemilu_dpt_id}")
    
    # Gunakan model PemiluDPT
    user = db.query(models.PemiluDPT).filter(models.PemiluDPT.id == pemilu_dpt_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    existing_fp = db.query(models.FingerprintTemplate).filter(
        models.FingerprintTemplate.pemilu_dpt_id == pemilu_dpt_id, # Disesuaikan
        models.FingerprintTemplate.finger_id == request.finger_id
    ).first()

    if existing_fp:
        existing_fp.template_data = request.template_data
        existing_fp.finger_name = request.finger_name
    else:
        new_fp = models.FingerprintTemplate(
            pemilu_dpt_id=pemilu_dpt_id, # Disesuaikan
            finger_id=request.finger_id,
            finger_name=request.finger_name,
            template_data=request.template_data
        )
        db.add(new_fp)
    
    db.commit()
    logger.info(f"Template sidik jari {request.finger_name} tersimpan.")
    return {"success": True, "message": "Sidik jari berhasil disimpan", "data": None}


# --- 3. AMBIL SEMUA DATA SIDIK JARI UNTUK DIVERIFIKASI OLEH ANDROID ---
@router.get("/all-fingerprints", response_model=schemas.StandardResponse[list])
async def get_all_fingerprints(db: Session = Depends(get_db)):
    logger.info("Mengirim semua data sidik jari ke Android untuk Local Matching")
    try:
        all_templates = db.query(models.FingerprintTemplate).all()
        data_list = []
        
        for fp in all_templates:
            # Gunakan model PemiluDPT dan filter berdasarkan pemilu_dpt_id
            user = db.query(models.PemiluDPT).filter(models.PemiluDPT.id == fp.pemilu_dpt_id).first()
            if user:
                # Menggabungkan semua atribut model User terbaru, dengan penanganan aman (getattr) 
                # untuk field yang mungkin tidak ada di skema tabel DPT
                data_list.append({
                    "finger_id": fp.finger_id,
                    "finger_name": fp.finger_name,
                    "template_data": fp.template_data,
                    "user": {
                        "id": user.id,
                        "nik": user.nik,
                        "nama_lengkap": user.nama_penduduk, # Fallback mapping untuk Android
                        "nama_penduduk": user.nama_penduduk,
                        "jenis_kelamin": user.jenis_kelamin,
                        "tempat_lahir": user.tempat_lahir,
                        "tanggal_lahir": user.tanggal_lahir,
                        "alamat": user.alamat,
                        "foto_profil": getattr(user, 'foto_profil', None),
                        "kode_pro": user.kode_pro,
                        "kode_kab": user.kode_kab,
                        "kode_kec": user.kode_kec,
                        "kode_kel": user.kode_kel,
                        "id_tps": user.id_tps,
                        "tps_no": user.tps_no,
                        "bilik_no": user.bilik_no,
                        "nama_pro": user.nama_pro,
                        "nama_kab": user.nama_kab,
                        "nama_kec": user.nama_kec,
                        "nama_desa": user.nama_desa,
                        "nkk": user.nkk,
                        "rt": user.rt,
                        "rw": user.rw,
                        "status_kawin": user.status_kawin,
                        "ket_tms": user.ket_tms,
                        "status_disabilitas": user.status_disabilitas,
                        "id_jenis_disabilitas": user.id_jenis_disabilitas,
                        "no_urut_dpt": user.no_urut_dpt,
                        "no_urut_cetak": user.no_urut_cetak
                    }
                })
                
        return {"success": True, "message": "Data berhasil diambil", "data": data_list}
    except Exception as e:
        logger.error(f"Gagal mengambil data sidik jari: {e}")
        return {"success": False, "message": "Server Error", "data": None}
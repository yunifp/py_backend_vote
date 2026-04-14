from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, date
import numpy as np
import json
import os
import shutil
import uuid
from typing import List, Optional
from pydantic import BaseModel

from .. import models, schemas, utils
from ..database import get_db

PROFILE_UPLOAD_DIR = "uploads/profiles"
os.makedirs(PROFILE_UPLOAD_DIR, exist_ok=True)

VECTOR_CACHE = {
    "is_dirty": True,
    "matrix": None,    
    "pemilu_dpt_ids": None   # Disesuaikan dari user_ids menjadi pemilu_dpt_ids
}

router = APIRouter(prefix="/users", tags=["Users & Biometrics"])

@router.post("/", response_model=schemas.StandardResponse[schemas.UserResponse])
async def create_user_and_register_face(
    nik: str = Form(..., min_length=16, max_length=16),
    nama_lengkap: str = Form(...), 
    jenis_kelamin: str = Form(...),
    tempat_lahir: str = Form(...),
    tanggal_lahir: date = Form(...),
    alamat: str = Form(...),
    foto_profil: Optional[UploadFile] = File(None),
    face_images: List[UploadFile] = File(..., description="Wajib upload TEPAT 3 foto wajah"),
    db: Session = Depends(get_db)
):
    # Menggunakan model PemiluDPT sesuai skema baru
    db_user = db.query(models.PemiluDPT).filter(models.PemiluDPT.nik == nik).first()
    
    if len(face_images) != 3:
        raise HTTPException(status_code=400, detail="Sistem memerlukan tepat 3 foto pose wajah.")

    jk_db = 'L' if jenis_kelamin.strip().lower() == 'laki-laki' else 'P' if jenis_kelamin.strip().lower() == 'perempuan' else ''

    embeddings = []
    for idx, file in enumerate(face_images):
        try:
            img = await utils.read_image_file(file)
            embedding = utils.get_face_embedding(img, is_strict=False)
            if embedding is None:
                raise ValueError("Wajah tidak terdeteksi jelas pada salah satu sudut.")
            embeddings.append(embedding)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Gagal pada foto ke-{idx + 1}: {str(e)}")

    saved_foto_path = None
    if foto_profil and foto_profil.filename:
        ext = foto_profil.filename.split(".")[-1]
        unique_filename = f"{nik}_{uuid.uuid4().hex[:8]}.{ext}"
        file_path = os.path.join(PROFILE_UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(foto_profil.file, buffer)
        saved_foto_path = file_path

    if db_user:
        # Pengecekan hasattr untuk kompatibilitas jika kolom foto_profil tidak ada di schema
        if saved_foto_path and hasattr(db_user, 'foto_profil') and db_user.foto_profil and os.path.exists(db_user.foto_profil):
            try: os.remove(db_user.foto_profil)
            except: pass
        
        db_user.nama_penduduk = nama_lengkap 
        db_user.jenis_kelamin = jk_db 
        db_user.tempat_lahir = tempat_lahir
        db_user.tanggal_lahir = tanggal_lahir
        db_user.alamat = alamat
        if saved_foto_path and hasattr(db_user, 'foto_profil'):
            db_user.foto_profil = saved_foto_path

        # Hapus face template lama
        db.query(models.FaceTemplate).filter(models.FaceTemplate.pemilu_dpt_id == db_user.id).delete()
        user_to_return = db_user
    else:
        new_user = models.PemiluDPT(
            nik=nik, nama_penduduk=nama_lengkap, jenis_kelamin=jk_db, 
            tempat_lahir=tempat_lahir, tanggal_lahir=tanggal_lahir, alamat=alamat
        )
        if hasattr(new_user, 'foto_profil') and saved_foto_path:
            new_user.foto_profil = saved_foto_path
            
        db.add(new_user)
        user_to_return = new_user

    db.flush() 

    new_template = models.FaceTemplate(
        pemilu_dpt_id=user_to_return.id, 
        embedding=json.dumps(embeddings), 
        position="All_3_Poses" 
    )
    db.add(new_template)
    db.commit()
    db.refresh(user_to_return)
    
    global VECTOR_CACHE
    VECTOR_CACHE["is_dirty"] = True
    
    return {
        "success": True, 
        "message": f"Pengguna {nama_lengkap} berhasil terdaftar (3 Pose Tersimpan).", 
        "data": schemas.UserResponse.model_validate(user_to_return)
    }

# --- ENDPOINT BARU: HANYA MENAMBAHKAN WAJAH KE USER YANG SUDAH ADA ---
@router.post("/{pemilu_dpt_id}/faces", response_model=schemas.StandardResponse[schemas.UserResponse])
async def register_faces_only(
    pemilu_dpt_id: int, # Parameter diganti jadi pemilu_dpt_id
    face_images: List[UploadFile] = File(..., description="Wajib upload TEPAT 3 foto wajah"),
    db: Session = Depends(get_db)
):
    # Filter menggunakan pemilu_dpt_id
    db_user = db.query(models.PemiluDPT).filter(models.PemiluDPT.id == pemilu_dpt_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Data User tidak ditemukan di Database.")

    if len(face_images) != 3:
        raise HTTPException(status_code=400, detail="Sistem memerlukan tepat 3 foto pose wajah.")

    embeddings = []
    for idx, file in enumerate(face_images):
        try:
            img = await utils.read_image_file(file)
            embedding = utils.get_face_embedding(img, is_strict=False)
            if embedding is None:
                raise ValueError("Wajah tidak terdeteksi jelas pada salah satu sudut.")
            embeddings.append(embedding)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Gagal pada foto ke-{idx + 1}: {str(e)}")

    # Hapus data wajah lama jika ada agar tertimpa yang baru
    db.query(models.FaceTemplate).filter(models.FaceTemplate.pemilu_dpt_id == db_user.id).delete()

    new_template = models.FaceTemplate(
        pemilu_dpt_id=db_user.id, 
        embedding=json.dumps(embeddings),
        position="All_3_Poses"
    )
    db.add(new_template)
    db.commit()
    db.refresh(db_user)

    global VECTOR_CACHE
    VECTOR_CACHE["is_dirty"] = True

    return {
        "success": True,
        "message": f"Data Biometrik Wajah untuk {db_user.nama_penduduk} berhasil disimpan.",
        "data": schemas.UserResponse.model_validate(db_user)
    }

@router.get("/", response_model=schemas.StandardResponse[List[schemas.UserResponse]])
def get_all_users(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    users = db.query(models.PemiluDPT).offset(skip).limit(limit).all()
    return {"success": True, "message": "Success", "data": [schemas.UserResponse.model_validate(u) for u in users]}

@router.delete("/{pemilu_dpt_id}", response_model=schemas.StandardResponse[None])
def delete_user(pemilu_dpt_id: int, db: Session = Depends(get_db)):
    # Parameter dan filter disesuaikan menjadi pemilu_dpt_id
    db_user = db.query(models.PemiluDPT).filter(models.PemiluDPT.id == pemilu_dpt_id).first()
    if not db_user: raise HTTPException(status_code=404, detail="User tidak ditemukan")
    db.delete(db_user)
    db.commit()
    VECTOR_CACHE["is_dirty"] = True
    return {"success": True, "message": "Deleted", "data": None}

@router.post("/recognize-face/", response_model=schemas.StandardResponse[schemas.UserResponse])
async def recognize_face(file: UploadFile = File(...), db: Session = Depends(get_db)):
    global VECTOR_CACHE
    
    # 1. Ekstrak Wajah (Sudah termasuk CLAHE & Strict Detection di utils)
    img = await utils.read_image_file(file)
    emb_raw = utils.get_face_embedding(img, is_strict=True)
    
    if emb_raw is None:
        raise HTTPException(
            status_code=400, 
            detail="Wajah tidak terdeteksi atau terhalang tangan/benda. Pastikan wajah terlihat jelas."
        )
        
    # Normalisasi L2 Unit Sphere
    u_emb = np.array(emb_raw, dtype=np.float32)
    u_emb = u_emb / (np.linalg.norm(u_emb) + 1e-10)

    # 2. Rebuild Cache (Jika diperlukan)
    if VECTOR_CACHE.get("is_dirty", True) or VECTOR_CACHE.get("matrix") is None:
        templates = db.query(models.FaceTemplate.pemilu_dpt_id, models.FaceTemplate.embedding).all()
        if not templates:
            raise HTTPException(status_code=404, detail="Database wajah kosong.")
            
        matrix3d, dpt_ids = [], []
        for t in templates:
            embs = json.loads(t.embedding)
            if len(embs) == 3:
                e_arr = np.array(embs, dtype=np.float32)
                # Normalisasi seluruh gallery
                norms = np.linalg.norm(e_arr, axis=1, keepdims=True)
                e_arr = e_arr / (norms + 1e-10)
                matrix3d.append(e_arr)
                dpt_ids.append(t.pemilu_dpt_id) # Relasi ke array cache
            
        VECTOR_CACHE["matrix"] = np.array(matrix3d, dtype=np.float32)
        VECTOR_CACHE["pemilu_dpt_ids"] = np.array(dpt_ids) # Ganti key cache
        VECTOR_CACHE["is_dirty"] = False

    known_matrix = VECTOR_CACHE["matrix"]
    known_dpt_ids = VECTOR_CACHE["pemilu_dpt_ids"]
    
    # 3. Hitung Jarak Cosine
    similarities = np.dot(known_matrix, u_emb) 
    distances = 1 - similarities # Jarak Cosine
    
    # THRESHOLD KETAT
    THRESHOLD = 0.65 
    
    matches_mask = distances < THRESHOLD
    counts_per_user = np.sum(matches_mask, axis=1)
    valid_user_indices = np.where(counts_per_user >= 1)[0]

    if len(valid_user_indices) > 0:
        best_dpt_id = None
        min_dist_found = 1.0
        
        for idx in valid_user_indices:
            # Ambil jarak dari pose yang paling mirip
            user_dists = distances[idx][matches_mask[idx]]
            current_min = np.min(user_dists)
            
            if current_min < min_dist_found:
                min_dist_found = current_min
                best_dpt_id = int(known_dpt_ids[idx])

        # Query mencari berdasarkan ID di tabel PemiluDPT
        best_user = db.query(models.PemiluDPT).filter(models.PemiluDPT.id == best_dpt_id).first()
        if best_user:
            accuracy = round((1 - min_dist_found) * 100, 2)
            return {
                "success": True, 
                "message": f"Dikenali (Akurasi: {accuracy}%)", 
                "data": schemas.UserResponse.model_validate(best_user)
            }

    raise HTTPException(status_code=404, detail="Wajah tidak dikenali dalam sistem.")
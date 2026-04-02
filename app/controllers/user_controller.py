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

# Pastikan import sesuai dengan struktur folder Anda
from .. import models, schemas, utils
from ..database import get_db

PROFILE_UPLOAD_DIR = "uploads/profiles"
os.makedirs(PROFILE_UPLOAD_DIR, exist_ok=True)

# Cache Global
VECTOR_CACHE = {
    "is_dirty": True,
    "matrix": None,    # Matrix NumPy 3D (N, 3, 512)
    "user_ids": None   # ID User (N,)
}

router = APIRouter(prefix="/users", tags=["Users & Biometrics"])

# ==========================================
# 1. CREATE USER (DAFTAR 3 WAJAH)
# ==========================================
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
    # Cek NIK
    db_user = db.query(models.User).filter(models.User.nik == nik).first()
    
    if len(face_images) != 3:
        raise HTTPException(status_code=400, detail="Sistem memerlukan tepat 3 foto wajah.")

    # Ekstrak Embedding (Sequential agar stabil)
    embeddings = []
    for idx, file in enumerate(face_images):
        try:
            img = await utils.read_image_file(file)
            embedding = utils.get_face_embedding(img)
            # if embedding is None:
            #     raise ValueError("Wajahtidak terdeteksi.")
            embeddings.append(embedding)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Gagal pada foto ke-{idx + 1}: {str(e)}")

    # Simpan Foto Profil Fisik
    saved_foto_path = None
    if foto_profil and foto_profil.filename:
        ext = foto_profil.filename.split(".")[-1]
        unique_filename = f"{nik}_{uuid.uuid4().hex[:8]}.{ext}"
        file_path = os.path.join(PROFILE_UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(foto_profil.file, buffer)
        saved_foto_path = file_path

    if db_user:
        # Update Data
        if saved_foto_path and db_user.foto_profil and os.path.exists(db_user.foto_profil):
            try: os.remove(db_user.foto_profil)
            except: pass
        
        db_user.nama_lengkap = nama_lengkap
        db_user.jenis_kelamin = jenis_kelamin
        db_user.tempat_lahir = tempat_lahir
        db_user.tanggal_lahir = tanggal_lahir
        db_user.alamat = alamat
        if saved_foto_path:
            db_user.foto_profil = saved_foto_path

        db.query(models.FaceTemplate).filter(models.FaceTemplate.user_id == db_user.id).delete()
        user_to_return = db_user
    else:
        # Insert Baru
        new_user = models.User(
            nik=nik, nama_lengkap=nama_lengkap, jenis_kelamin=jenis_kelamin,
            tempat_lahir=tempat_lahir, tanggal_lahir=tanggal_lahir, alamat=alamat,
            foto_profil=saved_foto_path
        )
        db.add(new_user)
        user_to_return = new_user

    db.flush() 

    # Simpan 3 Embedding dalam 1 Row
    new_template = models.FaceTemplate(
        user_id=user_to_return.id,
        embedding=json.dumps(embeddings), 
        position="All_3_Poses" 
    )
    db.add(new_template)
    db.commit()
    db.refresh(user_to_return)
    
    VECTOR_CACHE["is_dirty"] = True
    
    return {
        "success": True, 
        "message": f"Pengguna {nama_lengkap} berhasil terdaftar.", 
        "data": schemas.UserResponse.model_validate(user_to_return)
    }

# ==========================================
# 2. CRUD (READ ALL, GET, UPDATE, DELETE, CHECK)
# ==========================================
@router.get("/", response_model=schemas.StandardResponse[List[schemas.UserResponse]])
def get_all_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return {"success": True, "message": "Success", "data": [schemas.UserResponse.model_validate(u) for u in users]}

@router.get("/{user_id}", response_model=schemas.StandardResponse[schemas.UserResponse])
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return {"success": True, "message": "Success", "data": schemas.UserResponse.model_validate(user)}

@router.put("/{user_id}", response_model=schemas.StandardResponse[schemas.UserResponse])
def update_user(user_id: int, nik: str = Form(...), nama_lengkap: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user: raise HTTPException(status_code=404, detail="User tidak ditemukan")
    db_user.nik = nik
    db_user.nama_lengkap = nama_lengkap
    db.commit()
    return {"success": True, "message": "Updated", "data": schemas.UserResponse.model_validate(db_user)}

@router.delete("/{user_id}", response_model=schemas.StandardResponse[None])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user: raise HTTPException(status_code=404, detail="User tidak ditemukan")
    db.delete(db_user)
    db.commit()
    VECTOR_CACHE["is_dirty"] = True
    return {"success": True, "message": "Deleted", "data": None}

@router.get("/check-nik/{nik}", response_model=schemas.StandardResponse[schemas.UserResponse])
def check_user_by_nik(nik: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.nik == nik).first()
    if not user: return {"success": False, "message": "NIK belum terdaftar", "data": None}
    return {"success": True, "message": "Found", "data": schemas.UserResponse.model_validate(user)}

# =========================================================================
# ⚡ 3. RECOGNIZE FACE (OPTIMIZED & NORMALIZED)
# =========================================================================
@router.post("/recognize-face/", response_model=schemas.StandardResponse[schemas.UserResponse])
async def recognize_face(file: UploadFile = File(...), db: Session = Depends(get_db)):
    global VECTOR_CACHE
    
    # 1. Ekstrak Wajah (Sudah termasuk CLAHE & Strict Detection di utils)
    img = await utils.read_image_file(file)
    emb_raw = utils.get_face_embedding(img)
    
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
        templates = db.query(models.FaceTemplate.user_id, models.FaceTemplate.embedding).all()
        if not templates:
            raise HTTPException(status_code=404, detail="Database wajah kosong.")
            
        matrix3d, user_ids = [], []
        for t in templates:
            embs = json.loads(t.embedding)
            if len(embs) == 3:
                e_arr = np.array(embs, dtype=np.float32)
                # Normalisasi seluruh gallery
                norms = np.linalg.norm(e_arr, axis=1, keepdims=True)
                e_arr = e_arr / (norms + 1e-10)
                matrix3d.append(e_arr)
                user_ids.append(t.user_id)
            
        VECTOR_CACHE["matrix"] = np.array(matrix3d, dtype=np.float32)
        VECTOR_CACHE["user_ids"] = np.array(user_ids)
        VECTOR_CACHE["is_dirty"] = False

    known_matrix = VECTOR_CACHE["matrix"]
    known_user_ids = VECTOR_CACHE["user_ids"]
    
    # 3. Hitung Jarak Cosine
    similarities = np.dot(known_matrix, u_emb) 
    distances = 1 - similarities # Jarak Cosine
    
    # THRESHOLD KETAT
    THRESHOLD = 0.65 
    
    matches_mask = distances < THRESHOLD
    counts_per_user = np.sum(matches_mask, axis=1)
    valid_user_indices = np.where(counts_per_user >= 1)[0]

    if len(valid_user_indices) > 0:
        best_user_id = None
        min_dist_found = 1.0
        
        for idx in valid_user_indices:
            # Ambil jarak dari pose yang paling mirip
            user_dists = distances[idx][matches_mask[idx]]
            current_min = np.min(user_dists)
            
            if current_min < min_dist_found:
                min_dist_found = current_min
                best_user_id = int(known_user_ids[idx])

        best_user = db.query(models.User).filter(models.User.id == best_user_id).first()
        if best_user:
            accuracy = round((1 - min_dist_found) * 100, 2)
            return {
                "success": True, 
                "message": f"Dikenali (Akurasi: {accuracy}%)", 
                "data": schemas.UserResponse.model_validate(best_user)
            }

    raise HTTPException(status_code=404, detail="Wajah tidak dikenali dalam sistem.")
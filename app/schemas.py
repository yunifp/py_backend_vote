from pydantic import BaseModel, Field
from datetime import date
from typing import Any, Optional, Generic, TypeVar, List

T = TypeVar('T')

class StandardResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    nik: str

class UserCreate(BaseModel):
    nik: str = Field(..., min_length=16, max_length=16, description="16 Digit NIK KTP")
    nama_lengkap: str
    jenis_kelamin: str
    tempat_lahir: str
    tanggal_lahir: date
    alamat: str

class UserResponse(BaseModel):
    id: int
    nik: str
    nama_lengkap: str
    jenis_kelamin: str
    tempat_lahir: str
    tanggal_lahir: date
    alamat: str
    foto_profil: Optional[str] = None
    
    class Config:
        from_attributes = True

class FaceTemplateBase(BaseModel):
    position: Optional[str] = None

class FaceTemplateResponse(FaceTemplateBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class RegisterFaceDetail(BaseModel):
    total_foto_berhasil: int
    total_foto_gagal: int
    detail_gagal: List[dict] = []

    class Config:
        from_attributes = True
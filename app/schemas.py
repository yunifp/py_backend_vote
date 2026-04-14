from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from typing import Any, Optional, Generic, TypeVar, List

T = TypeVar('T')

class StandardResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None

    class Config:
        from_attributes = True

# RESPONSE
class UserResponse(BaseModel):
    id: int
    nik: str
    nama_penduduk: Optional[str] = None 
    nama_lengkap: Optional[str] = None 
    
    jenis_kelamin: Optional[str] = None
    tempat_lahir: Optional[str] = None
    tanggal_lahir: Optional[date] = None
    alamat: Optional[str] = None
    
    kode_pro: Optional[int] = None
    kode_kab: Optional[int] = None
    kode_kec: Optional[int] = None
    kode_kel: Optional[int] = None
    id_tps: Optional[int] = None
    tps_no: Optional[str] = None
    bilik_no: Optional[int] = None
    nama_pro: Optional[str] = None
    nama_kab: Optional[str] = None
    nama_kec: Optional[str] = None
    nama_desa: Optional[str] = None
    nkk: Optional[int] = None
    rt: Optional[str] = None
    rw: Optional[str] = None
    status_kawin: Optional[str] = None
    ket_tms: Optional[str] = None
    status_disabilitas: Optional[str] = None
    id_jenis_disabilitas: Optional[int] = None
    no_urut_dpt: Optional[int] = None
    no_urut_cetak: Optional[int] = None
    
    @validator('nama_lengkap', pre=True, always=True)
    def set_nama_lengkap(cls, v, values):
        if not v and 'nama_penduduk' in values:
            return values.get('nama_penduduk')
        return v

    @validator('nik', pre=True, always=True)
    def cast_nik_to_string(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True
        populate_by_name = True

class FaceTemplateBase(BaseModel):
    position: Optional[str] = None

class FaceTemplateResponse(FaceTemplateBase):
    id: int
    pemilu_dpt_id: int # 
    owner: Optional[UserResponse] = None 

    class Config:
        from_attributes = True

class FingerprintTemplateResponse(BaseModel):
    id: int
    pemilu_dpt_id: int 
    finger_id: int
    finger_name: str
    template_data: str
    owner: Optional[UserResponse] = None

    class Config:
        from_attributes = True

class RegisterFaceDetail(BaseModel):
    total_foto_berhasil: int
    total_foto_gagal: int
    detail_gagal: List[dict] = []

    class Config:
        from_attributes = True

class PemiluTPSResponse(BaseModel):
    id: int
    kode_pro: int
    kode_kab: int
    kode_kec: int
    kode_kel: int
    tps_no: int
    alamat: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True

# ==========================================
# SCHEMA WILAYAH (wilayahs)
# ==========================================
class WilayahResponse(BaseModel):
    wilayah_id: int
    parent: int
    children: int
    nama: Optional[str] = None
    usulan_nama: Optional[str] = None
    tingkat: int
    tingkat_label: str
    kode_pro: Optional[int] = None
    kode_kab: int
    kode_kec: int
    kode_kel: int
    status: Optional[str] = None
    singkatan: Optional[str] = None
    id_kec_lama: Optional[int] = None
    id_pro: Optional[int] = None
    id_kab: Optional[int] = None
    id_kec: Optional[int] = None
    id_kel: Optional[int] = None

    class Config:
        from_attributes = True
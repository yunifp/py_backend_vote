from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, Enum, BigInteger, CHAR, Double, DateTime, SmallInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT
from .database import Base

class PemiluDPT(Base):
    __tablename__ = "pemilu_dpt"
    
    id = Column(BigInteger, primary_key=True, index=True)
    kode_pro = Column(BigInteger, nullable=True)
    kode_kab = Column(BigInteger, nullable=True)
    kode_kec = Column(BigInteger, nullable=True)
    kode_kel = Column(BigInteger, nullable=True)
    id_tps = Column(BigInteger, default=0)
    tps_no = Column(String(255), nullable=True)
    bilik_no = Column(Integer, default=0)
    nama_pro = Column(String(255), nullable=True)
    nama_kab = Column(String(255), nullable=True)
    nama_kec = Column(String(255), nullable=True)
    nama_desa = Column(String(255), nullable=True)
    nkk = Column(BigInteger, nullable=True)
    nik = Column(String(20), unique=True, index=True) 
    
    tempat_lahir = Column(String(255), nullable=True)
    tanggal_lahir = Column(Date, nullable=True)
    
    nama_penduduk = Column(String(255), index=True, nullable=True)
    alamat = Column(Text, nullable=True)
    rt = Column(String(50), nullable=True)
    rw = Column(String(50), nullable=True)
    status_kawin = Column(Enum('B','S','P','','K','TK','J','D'), nullable=True)
    ket_tms = Column(String(100), nullable=True)
    status_disabilitas = Column(String(10), nullable=True)
    id_jenis_disabilitas = Column(Integer, default=0)
    jenis_kelamin = Column(Enum('L','P',''), nullable=True)
    no_urut_dpt = Column(BigInteger, nullable=True)
    no_urut_cetak = Column(Integer, default=0)
    
    fingerprint_templates = relationship("FingerprintTemplate", back_populates="owner", cascade="all, delete-orphan")
    face_templates = relationship("FaceTemplate", back_populates="owner", cascade="all, delete-orphan")


class FaceTemplate(Base):
    __tablename__ = "face_templates"
    id = Column(Integer, primary_key=True, index=True)

    pemilu_dpt_id = Column(BigInteger, ForeignKey("pemilu_dpt.id")) 
    
    embedding = Column(Text) 
    position = Column(String(50), nullable=True) 
    
    owner = relationship("PemiluDPT", back_populates="face_templates")


class FingerprintTemplate(Base):
    __tablename__ = "fingerprint_templates"
    id = Column(Integer, primary_key=True, index=True)
    
    pemilu_dpt_id = Column(BigInteger, ForeignKey("pemilu_dpt.id")) 
    
    finger_id = Column(Integer)
    finger_name = Column(String(50))
    template_data = Column(Text)
    
    owner = relationship("PemiluDPT", back_populates="fingerprint_templates")


class PemiluTPS(Base):
    __tablename__ = "pemilu_tps"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    kode_pro = Column(Integer, default=0, nullable=False, index=True)
    kode_kab = Column(Integer, default=0, nullable=False, index=True)
    kode_kec = Column(BigInteger, default=0, nullable=False, index=True)
    kode_kel = Column(BigInteger, default=0, nullable=False, index=True)
    tps_no = Column(Integer, default=0, nullable=False)
    alamat = Column(Text, nullable=True)
    latitude = Column(Double, nullable=True)
    longitude = Column(Double, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)


# ==========================================
# TABEL WILAYAH (wilayahs)
# ==========================================
class Wilayah(Base):
    __tablename__ = "wilayahs"

    wilayah_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    parent = Column(Integer, default=0, nullable=False, index=True)
    children = Column(Integer, default=0, nullable=False)
    nama = Column(CHAR(255), default="")
    usulan_nama = Column(CHAR(255), default="")
    tingkat = Column(SmallInteger, default=0, nullable=False, index=True)
    tingkat_label = Column(Enum('provinsi', 'kabupaten', 'kota', 'kecamatan', 'kelurahan', 'desa'), default='kelurahan', nullable=False, index=True)
    kode_pro = Column(BigInteger, default=0, index=True)
    kode_kab = Column(BigInteger, default=0, nullable=False, index=True)
    kode_kec = Column(BigInteger, default=0, nullable=False, index=True)
    kode_kel = Column(BigInteger, nullable=False, index=True)
    status = Column(Enum('active', 'pending', 'approved', 'rejected'), default='approved')
    singkatan = Column(CHAR(32), nullable=True, index=True)
    id_kec_lama = Column(Integer, nullable=True)
    id_pro = Column(Integer, nullable=True)
    id_kab = Column(Integer, nullable=True)
    id_kec = Column(Integer, nullable=True)
    id_kel = Column(Integer, nullable=True)
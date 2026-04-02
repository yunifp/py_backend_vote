from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    nik = Column(String(16), unique=True, index=True) 
    nama_lengkap = Column(String(255), index=True)
    jenis_kelamin = Column(String(20)) 
    tempat_lahir = Column(String(100))
    tanggal_lahir = Column(Date)
    alamat = Column(Text)
    foto_profil = Column(String(255), nullable=True) 

    # machine_user_id bisa dihapus atau dibiarkan kosong, karena identifikasi murni dari ID database
    machine_user_id = Column(String(50), unique=True, index=True, nullable=True) 
    
    fingerprint_templates = relationship("FingerprintTemplate", back_populates="owner", cascade="all, delete-orphan")
    face_templates = relationship("FaceTemplate", back_populates="owner", cascade="all, delete-orphan")

class FaceTemplate(Base):
    __tablename__ = "face_templates"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    embedding = Column(Text) 
    position = Column(String(50), nullable=True) 
    owner = relationship("User", back_populates="face_templates")

class FingerprintTemplate(Base):
    __tablename__ = "fingerprint_templates"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    finger_id = Column(Integer) # Contoh: Jari 1, Jari 2
    finger_name = Column(String(50)) # Labelnya: "Jempol Kanan", "Telunjuk Kiri", dll
    template_data = Column(Text) # Menampung String Base64/Hex dari Android
    owner = relationship("User", back_populates="fingerprint_templates")
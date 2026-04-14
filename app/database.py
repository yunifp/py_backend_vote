import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Memuat variabel dari file .env ke dalam sistem
load_dotenv()

# Mengambil nilai DATABASE_URL dari .env
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Validasi untuk mencegah error jika file .env lupa dibuat
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("Variabel DATABASE_URL tidak ditemukan. Pastikan file .env sudah ada.")

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
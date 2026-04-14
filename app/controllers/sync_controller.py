from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import requests
import logging
import os
import json 
from datetime import datetime

from .. import models, schemas
from ..database import get_db

logger = logging.getLogger("BiometricRouter")
router = APIRouter(prefix="/sync", tags=["Sync Database"])

def fetch_and_sync_pemilih(db: Session):
    url = os.getenv("DPT_API_URL")
    username = os.getenv("DPT_API_USERNAME")
    password = os.getenv("DPT_API_PASSWORD")
    
    if not url or not username or not password:
        logger.error("Kredensial DPT_API tidak ditemukan di file .env!")
        return
        
    payload = {'username': username, 'password': password}
    headers = {}
    
    try:
        logger.info(f"Memulai sinkronisasi data dari API external: {url}...")
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
        
        data_json = response.json()
        
        # 1. CEK JIKA JSON TER-ENCODE SEBAGAI STRING MURNI
        if isinstance(data_json, str):
            try:
                data_json = json.loads(data_json)
            except json.JSONDecodeError:
                logger.error("Response API berupa string tetapi bukan format JSON yang valid.")
                return

        # 2. EKSTRAK LIST PEMILIH (PERBAIKAN STRUKTUR JSON)
        list_pemilih = []
        if isinstance(data_json, dict):
            # Mengakses dictionary "data", lalu mengambil list "pemilih" di dalamnya
            data_block = data_json.get('data', {})
            if isinstance(data_block, dict):
                list_pemilih = data_block.get('pemilih', [])
            elif isinstance(data_block, list):
                list_pemilih = data_block
        elif isinstance(data_json, list):
            list_pemilih = data_json
            
        # 3. JIKA ISI LIST_PEMILIH TERNYATA MASIH STRING (DOUBLE STRINGIFIED)
        if isinstance(list_pemilih, str):
            try:
                list_pemilih = json.loads(list_pemilih)
            except Exception:
                pass
        
        # Pastikan list_pemilih benar-benar tipe data List
        if not isinstance(list_pemilih, list):
            logger.error(f"Format list_pemilih tidak dikenali. Tipe: {type(list_pemilih)}")
            return
            
        count_inserted = 0
        count_updated = 0
        
        for item in list_pemilih:
            # --- PROTEKSI UTAMA MENCEGAH ERROR 'STR' HAS NO ATTRIBUTE 'GET' ---
            if not isinstance(item, dict):
                continue
                
            nik_val = str(item.get('nik'))
            if not nik_val or nik_val == "None":
                continue
            
            db_user = db.query(models.User).filter(models.User.nik == nik_val).first()
            
            if not db_user:
                db_user = models.User(nik=nik_val)
                db.add(db_user)
                count_inserted += 1
            else:
                count_updated += 1
                
            # Helper untuk konversi string kosong/spasi ke None (agar tidak error integer)
            def parse_int_or_none(val):
                try:
                    if val is None or str(val).strip() == "":
                        return None
                    return int(val)
                except ValueError:
                    return None

            # Helper untuk tanggal
            def parse_date(date_str):
                try:
                    if date_str and date_str.strip() != "":
                        return datetime.strptime(date_str, "%Y-%m-%d").date()
                except Exception:
                    pass
                return None

            # Mapping Data API ke Model Database
            db_user.kode_pro = parse_int_or_none(item.get('kode_pro'))
            db_user.kode_kab = parse_int_or_none(item.get('kode_kab'))
            db_user.kode_kec = parse_int_or_none(item.get('kode_kec'))
            db_user.kode_kel = parse_int_or_none(item.get('kode_kel'))
            db_user.id_tps = parse_int_or_none(item.get('id_tps'))
            db_user.tps_no = str(item.get('tps_no', ''))
            db_user.bilik_no = parse_int_or_none(item.get('bilik_no'))
            
            db_user.nama_pro = str(item.get('nama_pro', ''))
            db_user.nama_kab = str(item.get('nama_kab', ''))
            db_user.nama_kec = str(item.get('nama_kec', ''))
            db_user.nama_desa = str(item.get('nama_desa', ''))
            db_user.nkk = parse_int_or_none(item.get('nkk'))
            db_user.tempat_lahir = str(item.get('tempat_lahir', ''))
            
            db_user.tanggal_lahir = parse_date(item.get('tanggal_lahir'))
            db_user.nama_penduduk = str(item.get('nama_penduduk', ''))
            db_user.alamat = str(item.get('alamat', ''))
            db_user.rt = str(item.get('rt', ''))
            db_user.rw = str(item.get('rw', ''))
            
            db_user.status_kawin = str(item.get('status_kawin', ''))
            db_user.ket_tms = str(item.get('ket_tms', ''))
            db_user.status_disabilitas = str(item.get('status_disabilitas', ''))
            db_user.id_jenis_disabilitas = parse_int_or_none(item.get('id_jenis_disabilitas'))
            db_user.jenis_kelamin = str(item.get('jenis_kelamin', ''))
            db_user.no_urut_dpt = parse_int_or_none(item.get('no_urut_dpt'))
            db_user.no_urut_cetak = parse_int_or_none(item.get('no_urut_cetak'))
            
        db.commit()
        logger.info(f"Sinkronisasi Selesai. Ditambahkan: {count_inserted}, Diperbarui: {count_updated}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Gagal melakukan sinkronisasi data: {e}")

@router.post("/trigger")
async def trigger_sync_data(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    background_tasks.add_task(fetch_and_sync_pemilih, db)
    return {
        "success": True, 
        "message": "Proses tarik data dari API DPT sedang berjalan di latar belakang (background task)."
    }
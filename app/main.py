import threading
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles

from .database import engine
from . import models

# Import semua controller
from .controllers import user_controller
from .controllers import fingerprint_controller

# Import fungsi background scanner untuk USB

# Buat tabel database
models.Base.metadata.create_all(bind=engine)

# Inisialisasi Event untuk mengontrol thread scanner
stop_event = threading.Event()

app = FastAPI(title="Biometric API - Solution P207 USB Mode")

# --- LIFESPAN EVENTS (STARTUP & SHUTDOWN) ---

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None
        }
    )

# --- DAFTAR ROUTER ---
@app.get("/check-connection")
async def check_connection():
    """
    Endpoint ini ada di ROOT aplikasi, jadi terhindar dari konflik {user_id}
    """
    return {
        "success": True, 
        "message": "Koneksi ke server berhasil! Backend aktif.", 
        "data": None
    }
app.include_router(user_controller.router)
app.include_router(fingerprint_controller.router)

# Mount folder upload untuk akses foto profil
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
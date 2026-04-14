import numpy as np
import cv2
from deepface import DeepFace
from fastapi import HTTPException, UploadFile

# --- KONFIGURASI BIOMETRIK ---
MODEL_NAME = "ArcFace" 
DETECTOR_BACKEND = "mtcnn" # MTCNN sangat baik dalam memberikan skor confidence

def get_face_embedding(img, is_strict: True):
    try:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        
        limg = cv2.merge((cl, a, b))
        img_final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # 2. Resize ringan untuk performa
        height, width = img_final.shape[:2]
        if max(height, width) > 800:
            scale = 800 / max(height, width)
            img_final = cv2.resize(img_final, (int(width * scale), int(height * scale)))

        # 3. Ekstraksi dengan Standar Ketat
        objs = DeepFace.represent(
            img_path=img_final, 
            model_name=MODEL_NAME, 
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True, 
            align=True              
        )
        
        if not objs:
            return None
        
        face_score = objs[0]["face_confidence"]
        
        # --- PENYESUAIAN THRESHOLD BERDASARKAN IS_STRICT ---
        threshold = 0.95 if is_strict else 0.85
        
        if face_score < threshold:
            print(f"Wajah ditolak: Skor keyakinan {face_score} di bawah standar {threshold}")
            return None

        return objs[0]["embedding"]
        
    except Exception as e:
        print(f"Detection Error: {e}")
        return None

async def read_image_file(file: UploadFile):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: raise ValueError()
        return img
    except:
        raise HTTPException(status_code=400, detail="Format gambar tidak valid")
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import create_client
from datetime import datetime
import cv2
import numpy as np
import uuid
import mediapipe as mp
import json

app = FastAPI()

# CORS
origins = ["https://aicam.infinitenxt.com", "http://localhost:5500"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase
SUPABASE_URL = "https://dehdirlguqpeecnuynqc.supabase.co"
SUPABASE_KEY = "your_supabase_key"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Mediapipe Setup
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

@app.post("/process-image/")
async def process_image(
    file: UploadFile = File(...),
    type: str = Form(...),
    subtype: str = Form(...),
    Id: str = Form(...)
):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Run Mediapipe
        with mp_pose.Pose(static_image_mode=True) as pose:
            results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            if not results.pose_landmarks:
                return JSONResponse(content={"error": "No landmarks found"}, status_code=400)

            # Calculate angles
            angle_data = calculate_posture_angles(results.pose_landmarks.landmark, type, subtype)
            angle_data = {k: v for k, v in angle_data.items() if v is not None}  # clean

            if not angle_data:
                return JSONResponse(content={"error": "Could not extract posture data"}, status_code=400)

            # Draw landmarks
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # Save image and upload
        filename = f"{uuid.uuid4()}.jpg"
        save_path = f"/tmp/{filename}"
        cv2.imwrite(save_path, image)
        with open(save_path, "rb") as f:
            supabase.storage.from_("images").upload(filename, f, {"content-type": "image/jpeg"})
        image_url = supabase.storage.from_("images").get_public_url(filename)

        # Insert into Supabase
        supabase.table("posture_data").insert({
            "image_url": image_url,
            "angle_data": angle_data,
            "type": type,
            "subtype": subtype,
            "user_id": Id,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()

        return JSONResponse(content={"image_url": image_url, "angle_data": angle_data})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ---------------------- Angle Logic ----------------------
def calculate_posture_angles(landmarks, type, subtype):
    import math
    def get_angle(a, b, c):
        ang = math.degrees(
            math.atan2(c.y - b.y, c.x - b.x) -
            math.atan2(a.y - b.y, a.x - b.x)
        )
        return abs(ang) if ang >= 0 else 360 + ang

    def safe_get_angle(lms, a, b, c):
        try:
            if lms[a].visibility < 0.5 or lms[b].visibility < 0.5 or lms[c].visibility < 0.5:
                return None
            return get_angle(lms[a], lms[b], lms[c])
        except:
            return None

    if type == "body" and subtype == "Anterior":
        return {
            "Body Alignment": safe_get_angle(landmarks, 11, 23, 25),
            "Head Shift": safe_get_angle(landmarks, 0, 11, 12),
            "Acromion": safe_get_angle(landmarks, 11, 13, 15),
            "Axillary": safe_get_angle(landmarks, 12, 14, 16),
            "Ribcage": safe_get_angle(landmarks, 11, 23, 24),
            "ASIS": safe_get_angle(landmarks, 23, 25, 27),
            "Knee": safe_get_angle(landmarks, 25, 27, 29),
            "Feet": safe_get_angle(landmarks, 27, 29, 31)
        }

    elif type == "body" and "Lateral" in subtype:
        return {
            "Body Alignment": safe_get_angle(landmarks, 11, 23, 25),
            "Head Deviation": safe_get_angle(landmarks, 0, 11, 23),
            "Shoulder": safe_get_angle(landmarks, 11, 13, 15),
            "Knee": safe_get_angle(landmarks, 25, 27, 29)
        }

    elif type == "body" and "Sitting" in subtype:
        return {
            "Head Deviation": safe_get_angle(landmarks, 0, 11, 23),
            "Shoulder": safe_get_angle(landmarks, 11, 13, 15),
            "Elbow": safe_get_angle(landmarks, 13, 15, 19),
            "Hip": safe_get_angle(landmarks, 23, 25, 27)
        }

    elif type == "head":
        return {
            "CHS": safe_get_angle(landmarks, 0, 11, 12),
            "Neck angle": safe_get_angle(landmarks, 11, 23, 25),
            "Shoulder angle": safe_get_angle(landmarks, 11, 13, 15)
        }

    return {}

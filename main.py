from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import create_client, Client
from datetime import datetime
import uuid
import cv2
import numpy as np
import mediapipe as mp
import io

app = FastAPI()

# CORS
origins = [
    "https://aicam.infinitenxt.com",
    "http://localhost:5500",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Config
SUPABASE_URL = "https://dehdirlguqpeecnuynqc.supabase.co"
SUPABASE_KEY = "your-key-here"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Posture analysis using MediaPipe
def analyze_posture(image_np, type, subtype):
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=True)
    results = pose.process(cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB))

    if not results.pose_landmarks:
        return None, {"error": "No pose landmarks detected"}

    # Example: Extracting basic landmark coordinates
    landmarks = results.pose_landmarks.landmark
    data = {
        "CHS": round(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y - landmarks[mp_pose.PoseLandmark.LEFT_HIP].y, 3),
        "Shoulder Angle": 76,
        "Neck Tilt": 12,
        "Hip Angle": 109,
    }

    # Draw landmarks on image
    mp.solutions.drawing_utils.draw_landmarks(image_np, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    return image_np, data

@app.post("/process-image/")
async def process_image(
    file: UploadFile = File(...),
    type: str = Form(...),
    subtype: str = Form(...),
    Id: str = Form(...)
):
    try:
        contents = await file.read()
        np_arr = np.frombuffer(contents, np.uint8)
        image_np = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # Process image
        processed_image, posture_data = analyze_posture(image_np, type, subtype)
        if processed_image is None:
            return JSONResponse(content={"error": "Pose not detected"}, status_code=400)

        # Encode to JPEG
        _, buffer = cv2.imencode(".jpg", processed_image)
        image_bytes = io.BytesIO(buffer).getvalue()

        # Upload to Supabase
        filename = f"{uuid.uuid4()}.jpg"
        supabase.storage.from_("images").upload(filename, image_bytes, {"content-type": "image/jpeg"})
        image_url = supabase.storage.from_("images").get_public_url(filename)

        # Save metadata to table
        supabase.table("posture_data").insert({
            "image_url": image_url,
            "angle_data": posture_data,
            "type": type,
            "subtype": subtype,
            "user_id": Id,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()

        return JSONResponse(content={"image_url": image_url, "angle_data": posture_data})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

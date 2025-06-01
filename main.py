from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import uuid
from supabase import create_client, Client
import mediapipe as mp

# --- Supabase Config ---
SUPABASE_URL = "https://dehdirlguqpeecnuynqc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlaGRpcmxndXFwZWVjbnV5bnFjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI3MjYxNjMsImV4cCI6MjA1ODMwMjE2M30.7SovkQX9lDgkr4CruUFFnw6HTCe0MNw2eEghBptSlWs"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Mediapipe Setup ---
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True)
mp_drawing = mp.solutions.drawing_utils

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production me change kar lena
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_image(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    results = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    if results.pose_landmarks:
        mp_drawing.draw_landmarks(img, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    _, processed_bytes = cv2.imencode(".png", img)

    dummy_angles = {
        "Head Deviation": 11,
        "Shoulder": 78,
        "Elbow": 176,
        "Hip": 121
    }

    return processed_bytes.tobytes(), dummy_angles

def upload_to_supabase(image_bytes):
    file_name = f"posture_{uuid.uuid4()}.png"
    supabase.storage.from_('images').upload(file_name, image_bytes)
    url = f"{SUPABASE_URL}/storage/v1/object/public/images/{file_name}"
    return url

@app.post("/process-image/")
async def process_image_api(file: UploadFile = File(...)):
    image_bytes = await file.read()
    processed_image, angles = process_image(image_bytes)
    image_url = upload_to_supabase(processed_image)

    supabase.table("posture_data").insert({
        "image_url": image_url,
        "angles": angles,
        "type": "siting-right"
    }).execute()

    return JSONResponse(content={"image_url": image_url, "angles": angles})

from fastapi import FastAPI, File, UploadFile, Query
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

# CORS config
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

# Supabase config
SUPABASE_URL = "https://dehdirlguqpeecnuynqc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlaGRpcmxndXFwZWVjbnV5bnFjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI3MjYxNjMsImV4cCI6MjA1ODMwMjE2M30.7SovkQX9lDgkr4CruUFFnw6HTCe0MNw2eEghBptSlWs"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Helper for Mediapipe processing
def process_with_mediapipe(image_np, type_, subtype):
    mp_pose = mp.solutions.pose
    results_data = {}
    
    with mp_pose.Pose(static_image_mode=True) as pose:
        results = pose.process(cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB))

        if results.pose_landmarks:
            # Draw landmarks
            mp_drawing = mp.solutions.drawing_utils
            annotated_image = image_np.copy()
            mp_drawing.draw_landmarks(annotated_image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            # Dummy sample angles (replace with real calculations)
            results_data = {
                "CHS": 123.4,
                "Neck Angle": 45.6,
                "Shoulder Tilt": 12.3
            }

            return annotated_image, results_data
        else:
            raise Exception("No pose landmarks detected")

@app.post("/process-image/")
async def process_image(
    file: UploadFile = File(...),
    id: str = Query(...),
    type: str = Query(...),
    subtype: str = Query(...)
):
    try:
        contents = await file.read()
        image_np = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)

        processed_image, angle_data = process_with_mediapipe(image_np, type, subtype)

        # Encode to .jpg
        _, buffer = cv2.imencode('.jpg', processed_image)
        processed_bytes = io.BytesIO(buffer)

        filename = f"{uuid.uuid4()}.jpg"

        # Upload to Supabase
        supabase.storage.from_('images').upload(filename, processed_bytes.getvalue(), {"content-type": "image/jpeg"})
        image_url = supabase.storage.from_('images').get_public_url(filename)

        # Save to table
        supabase.table("posture_data").insert({
            "user_id": id,
            "image_url": image_url,
            "angle_data": angle_data,
            "type": type,
            "subtype": subtype,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()

        return JSONResponse(content={
            "image_url": image_url,
            "angle_data": angle_data
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

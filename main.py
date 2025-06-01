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
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlaGRpcmxndXFwZWVjbnV5bnFjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI3MjYxNjMsImV4cCI6MjA1ODMwMjE2M30.7SovkQX9lDgkr4CruUFFnw6HTCe0MNw2eEghBptSlWs"
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

# ⬇️ Angle calculation logic
def calculate_posture_angles(landmarks, type, subtype):
    # Dummy logic: replace with real angle calculation per posture
    # type: 'head' or 'body'
    # subtype: 'LateralLeft', etc.

    def get_angle(a, b, c):
        import math
        ang = math.degrees(
            math.atan2(c.y - b.y, c.x - b.x) -
            math.atan2(a.y - b.y, a.x - b.x)
        )
        return abs(ang) if ang >= 0 else 360 + ang

    if type == "body" and subtype == "Anterior":
        return {
            "Body Alignment": get_angle(landmarks[11], landmarks[23], landmarks[25]),
            "Head Shift": get_angle(landmarks[0], landmarks[11], landmarks[12]),
            "Acromion": get_angle(landmarks[11], landmarks[13], landmarks[15]),
            "Axillary": get_angle(landmarks[12], landmarks[14], landmarks[16]),
            "Ribcage": get_angle(landmarks[11], landmarks[23], landmarks[24]),
            "ASIS": get_angle(landmarks[23], landmarks[25], landmarks[27]),
            "Knee": get_angle(landmarks[25], landmarks[27], landmarks[29]),
            "Feet": get_angle(landmarks[27], landmarks[29], landmarks[31])
        }

    elif type == "body" and "Lateral" in subtype:
        return {
            "Body Alignment": get_angle(landmarks[11], landmarks[23], landmarks[25]),
            "Head Deviation": get_angle(landmarks[0], landmarks[11], landmarks[23]),
            "Shoulder": get_angle(landmarks[11], landmarks[13], landmarks[15]),
            "Knee": get_angle(landmarks[25], landmarks[27], landmarks[29])
        }

    elif type == "body" and "Sitting" in subtype:
        return {
            "Head Deviation": get_angle(landmarks[0], landmarks[11], landmarks[23]),
            "Shoulder": get_angle(landmarks[11], landmarks[13], landmarks[15]),
            "Elbow": get_angle(landmarks[13], landmarks[15], landmarks[19]),
            "Hip": get_angle(landmarks[23], landmarks[25], landmarks[27])
        }

    elif type == "head":
        return {
            "CHS": get_angle(landmarks[0], landmarks[11], landmarks[12]),
            "Neck angle": get_angle(landmarks[11], landmarks[23], landmarks[25]),
            "Shoulder angle": get_angle(landmarks[11], landmarks[13], landmarks[15])
        }

    return {"error": "No valid posture detected"}


from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import create_client, Client
import uuid
from datetime import datetime

app = FastAPI()

# ✅ CORS Configuration
origins = [
    "https://aicam.infinitenxt.com",  # tera frontend domain
    "http://localhost:5500",          # optional local test
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Supabase Configuration
SUPABASE_URL = "https://dehdirlguqpeecnuynqc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlaGRpcmxndXFwZWVjbnV5bnFjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI3MjYxNjMsImV4cCI6MjA1ODMwMjE2M30.7SovkQX9lDgkr4CruUFFnw6HTCe0MNw2eEghBptSlWs"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ✅ Upload & Process Endpoint
@app.post("/process-image/")
async def process_image(file: UploadFile = File(...)):
    try:
        # 🟢 Step 1: Unique filename
        contents = await file.read()
        filename = f"{uuid.uuid4()}.jpg"

        # 🟢 Step 2: Upload to Supabase Storage
        supabase.storage.from_('images').upload(filename, contents, {"content-type": "image/jpeg"})

        # 🟢 Step 3: Get public URL
        image_url = supabase.storage.from_('images').get_public_url(filename)

        # 🟢 Step 4: Dummy angles (replace with real processing later)
        angle_data = {
            "Head Deviation": 11,
            "Shoulder": 78,
            "Elbow": 176,
            "Hip": 121,
        }

        # 🟢 Step 5: Insert data into Supabase table
        supabase.table("posture_data").insert({
            "image_url": image_url,
            "angle_data": angle_data,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()

        # ✅ Step 6: Return response
        return JSONResponse(content={"image_url": image_url, "angle_data": angle_data})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import create_client, Client
import uuid
from datetime import datetime

app = FastAPI()

# ✅ CORS config
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

# ✅ Supabase Config
SUPABASE_URL = "https://dehdirlguqpeecnuynqc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlaGRpcmxndXFwZWVjbnV5bnFjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI3MjYxNjMsImV4cCI6MjA1ODMwMjE2M30.7SovkQX9lDgkr4CruUFFnw6HTCe0MNw2eEghBptSlWs"  # for safety, don't commit real key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.post("/process-image/")
async def process_image(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        filename = f"{uuid.uuid4()}.jpg"
        print(f"Uploading file: {filename}")

        res = supabase.storage.from_('images').upload(filename, contents, {"content-type": "image/jpeg"})
        print(f"Upload response: {res}")

        image_url = supabase.storage.from_('images').get_public_url(filename)
        print(f"Image URL: {image_url}")

        angle_data = {
            "Head Deviation": 11,
            "Shoulder": 78,
            "Elbow": 176,
            "Hip": 121,
        }

        insert_response = supabase.table("posture_data").insert({
            "image_url": image_url,
            "angle_data": angle_data,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        print(f"Insert response: {insert_response}")

        return {"image_url": image_url, "angle_data": angle_data}

    except Exception as e:
        import traceback
        traceback.print_exc()  # Ye exact traceback console/logs me print karega
        return JSONResponse(content={"error": str(e)}, status_code=500)

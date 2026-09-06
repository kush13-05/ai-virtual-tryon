import os
import time
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from gradio_client import Client, handle_file

# --- HUMANIZED ENTERPRISE AI TRY-ON ENGINE V3 ---
app = FastAPI(title="NextGen AI Fashion Engine")

# फिक्स किया हुआ CORS बख्तरबंद सुरक्षा घेरा
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_TOKEN = os.getenv("HF_TOKEN", "hf_vRovpYxHOfiZgOnvCjIDpEaWNoZmFzdF9hcGk") 
SECURE_STAGE = "secure_fabric_stage"
os.makedirs(SECURE_STAGE, exist_ok=True)

@app.post("/api/v1/fit-garment")
async def fit_garment_pipeline(
    person_image: UploadFile = File(...),
    garment_image: UploadFile = File(...)
):
    request_id = int(time.time())
    print(f"[SYSTEM LOG] - Processing Request ID: {request_id}")

    # सुरक्षा जांच - फ़ाइलों का इमेज होना अनिवार्य है
    if not person_image.content_type.startswith("image/") or not garment_image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type.")

    safe_person_path = os.path.join(SECURE_STAGE, f"user_{request_id}.png")
    safe_garment_path = os.path.join(SECURE_STAGE, f"cloth_{request_id}.png")

    try:
        # फ़ाइलों को सुरक्षित तरीके से रैम की तरह सेव करना
        with open(safe_person_path, "wb") as buffer:
            shutil.copyfileobj(person_image.file, buffer)
        with open(safe_garment_path, "wb") as buffer:
            shutil.copyfileobj(garment_image.file, buffer)

        # AI CLUSTER CONNECTION
        ai_client = Client("yisol/IDM-VTON", token=HF_TOKEN)
        
        # फिक्स: handle_file को सीधे स्ट्रिंग पाथ देकर एआई को फ़ीड करना
        ai_response = ai_client.predict(
            dict={"background": handle_file(safe_person_path), "layers": [], "composite": None},
            garm_img=handle_file(safe_garment_path),
            garment_des="Hyper-realistic premium clothing fabric",
            is_checked=True,
            denoise_steps=30,
            seed=42,
            api_name="/tryon"
        )

        # प्राइवेसी पुरगे: काम होते ही ओरिजिनल फ़ोटो सर्वर से साफ़
        if os.path.exists(safe_person_path): os.remove(safe_person_path)
        if os.path.exists(safe_garment_path): os.remove(safe_garment_path)

        return {"status": "success", "output_image_url": ai_response}

    except Exception as server_error:
        print(f"[CRITICAL ERROR IN PIPELINE]: {str(server_error)}")
        if os.path.exists(safe_person_path): os.remove(safe_person_path)
        if os.path.exists(safe_garment_path): os.remove(safe_garment_path)
        raise HTTPException(status_code=500, detail=str(server_error))

import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import edge_tts
import boto3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement des identifiants R2 depuis l'environnement Render
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_PUBLIC_DOMAIN = os.getenv("R2_PUBLIC_DOMAIN") # ex: https://pub-xxx.r2.dev

# Client S3 pour Cloudflare R2
s3_client = boto3.client(
    service_name="s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    region_name="auto"
)

class TTSPayload(BaseModel):
    text: str
    voice: str = "fr-FR-HenriNeural" # Voix masculine française Edge

@app.get("/")
def health_check():
    return {"status": "JARVIS TTS Online"}

@app.post("/tts")
async def process_tts(data: TTSPayload):
    try:
        filename = f"jarvis_{uuid.uuid4().hex[:10]}.mp3"
        temp_path = f"/tmp/{filename}"

        # 1. Génération audio Microsoft Edge TTS
        communicate = edge_tts.Communicate(data.text, data.voice)
        await communicate.save(temp_path)

        # 2. Téléversement direct vers Cloudflare R2
        with open(temp_path, "rb") as audio_file:
            s3_client.upload_fileobj(
                audio_file,
                R2_BUCKET_NAME,
                filename,
                ExtraArgs={"ContentType": "audio/mpeg"}
            )

        # Nettoyage du fichier local
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # 3. Retourne l'URL Cloudflare R2
        audio_url = f"{R2_PUBLIC_DOMAIN}/{filename}"
        return {"status": "success", "audio_url": audio_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
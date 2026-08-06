import os
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import edge_tts

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dossier temporaire pour Render (/tmp est volatile mais accessible en écriture)
AUDIO_DIR = "/tmp/audio_cache"
os.makedirs(AUDIO_DIR, exist_ok=True)

class TTSPayload(BaseModel):
    text: str
    voice: str = "fr-FR-HenriNeural"

@app.get("/")
def health_check():
    return {"status": "JARVIS TTS Standalone Online"}

@app.post("/tts")
async def generate_tts(data: TTSPayload, request: Request):
    # 1) Validation de base
    text = (data.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texte TTS vide")

    try:
        # 2) Préparation fichier
        filename = f"jarvis_{uuid.uuid4().hex[:10]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # 3) Appel à Edge TTS
        communicate = edge_tts.Communicate(text, data.voice)

        # Méthode save() est correcte avec edge-tts récent
        await communicate.save(filepath)

        # 4) Génération de l'URL publique
        base_url = str(request.base_url).rstrip("/")
        audio_url = f"{base_url}/audio/{filename}"

        return {"status": "success", "audio_url": audio_url}

    except Exception as e:
        # Log complet côté serveur pour debug
        # Sur Render, tu verras ce str(e) + stacktrace dans les logs
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Fichier audio non trouvé")

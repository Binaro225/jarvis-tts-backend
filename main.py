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

# Dossier temporaire pour stocker les audios sur Render
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
    try:
        filename = f"jarvis_{uuid.uuid4().hex[:10]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Génération du fichier MP3 via Edge TTS
        communicate = edge_tts.Communicate(data.text, data.voice)
        await communicate.save(filepath)

        # Génération dynamique de l'URL publique de Render
        base_url = str(request.base_url).rstrip("/")
        audio_url = f"{base_url}/audio/{filename}"

        return {"status": "success", "audio_url": audio_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Fichier audio non trouvé")

import os
import re
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
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

AUDIO_DIR = "/tmp/audio_cache"
os.makedirs(AUDIO_DIR, exist_ok=True)

class TTSPayload(BaseModel):
    text: str
    voice: str = "fr-FR-HenriNeural"

def clean_text_for_speech(raw_text: str) -> str:
    """Nettoie le texte pour que la voix JARVIS ne lise pas les symboles et le Markdown."""
    # Enlever le Markdown (gras, italique, titres)
    text = re.sub(r'[*_~`#]', '', raw_text)
    # Enlever les liens HTTP/HTTPS
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # Enlever les balises HTML ou XML si présentes
    text = re.sub(r'<[^>]+>', '', text)
    # Remplacer les tirets et symboles de listes par des pauses naturelles
    text = text.replace('\n', ' ').replace('-', ' ')
    # Supprimer les espaces multiples
    text = re.sub(r'\s+', ' ', text).strip()
    return text

@app.get("/")
def health_check():
    return {"status": "JARVIS TTS Clean Speech Online"}

@app.post("/tts")
async def generate_tts(data: TTSPayload, request: Request):
    try:
        # Nettoyage strict du texte avant l'envoi à Edge TTS
        clean_text = clean_text_for_speech(data.text)
        
        if not clean_text:
            raise HTTPException(status_code=400, detail="Texte vide après nettoyage")

        filename = f"jarvis_{uuid.uuid4().hex[:10]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Synthèse vocale avec le texte nettoyé uniquement
        communicate = edge_tts.Communicate(clean_text, data.voice)
        await communicate.save(filepath)

        base_url = str(request.base_url).rstrip("/")
        audio_url = f"{base_url}/audio/{filename}"

        return {"status": "success", "audio_url": audio_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Fichier audio non trouvé")

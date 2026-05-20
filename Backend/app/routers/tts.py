import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from tts import generate_audio_file, tts_service, get_available_voices
import logging
import asyncio

log = logging.getLogger("tts_router")

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-JennyNeural"


@router.get("/voices")
def list_voices():
    return {"voices": get_available_voices()}


@router.post("/speak")
async def speak(request: TTSRequest):
    log.info(f"Generating TTS for: {request.text[:50]}...")
    try:
        output_path = generate_audio_file(request.text)

        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="TTS generation failed")

        return {"audio_url": f"/tts/audio/{os.path.basename(output_path)}"}
    except Exception as e:
        log.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak/stream")
async def speak_stream(request: TTSRequest):
    log.info(f"Generating TTS for: {request.text[:50]}...")

    try:
        output_path = generate_audio_file(request.text)

        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="TTS generation failed")

        return FileResponse(
            output_path,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline"},
        )
    except Exception as e:
        log.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

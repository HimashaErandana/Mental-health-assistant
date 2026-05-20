import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from stt import WhisperSTT
from app.mcp_client import MCPClient
from utils import get_logger
import uuid
from datetime import datetime

log = get_logger("chat_router")

router = APIRouter()

mcp_client = MCPClient()

AUDIO_FOLDER = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(AUDIO_FOLDER, exist_ok=True)


class TextMessageRequest(BaseModel):
    message: str


@router.post("/")
async def chat_with_audio(file: UploadFile = File(None)):
    log.info(f"Received audio request, file: {file}")

    if not file:
        log.error("No file provided in request")
        raise HTTPException(status_code=400, detail="No file provided")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    suffix = ".webm"
    filename = f"audio_{timestamp}_{unique_id}{suffix}"
    saved_path = os.path.join(AUDIO_FOLDER, filename)
    log.info(f"Saving audio to: {saved_path}")

    try:
        content = await file.read()
        log.info(f"File size: {len(content)} bytes")

        with open(saved_path, "wb") as f:
            f.write(content)

        log.info("Initializing Whisper STT...")
        stt = WhisperSTT(model_name="small.en")
        log.info("Transcribing audio...")
        text = stt.transcribe(saved_path)
        log.info(f"Transcribed text: {text}")

        if not text.strip():
            log.warning("Transcription returned empty text")
            return {
                "transcribed_text": "",
                "response": "Could not understand audio",
                "saved_file": filename,
            }

        log.info(f"Processing query: {text}")
        response = mcp_client.process_query(text)
        log.info(f"MCP response: {response}")

        return {"transcribed_text": text, "response": response, "saved_file": filename}
    except Exception as e:
        log.error(f"Error processing audio: {type(e).__name__}: {e}")
        import traceback

        log.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text")
def chat_with_text(request: TextMessageRequest):
    log.info(f"Received text message: {request.message}")
    try:
        response = mcp_client.process_query(request.message)
        log.info(f"MCP response: {response}")
        return {"message": request.message, "response": response}
    except Exception as e:
        log.error(f"Error processing text: {type(e).__name__}: {e}")
        import traceback

        log.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

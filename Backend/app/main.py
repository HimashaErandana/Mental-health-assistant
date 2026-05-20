import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.routers import stt, rag, chat, tts

# Create TTS output directory
TTS_DIR = Path("D:/My projects/Agentic AI/Metal helath assistance/Backend/tts_output")
TTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Mental Health AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stt.router, prefix="/stt", tags=["STT"])
app.include_router(rag.router, prefix="/rag", tags=["RAG"])
app.include_router(tts.router, prefix="/tts", tags=["TTS"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])


# Serve TTS audio files (ADD THIS BACK)
@app.get("/tts/audio/{filename}")
async def serve_audio(filename: str):
    audio_path = TTS_DIR / filename
    if audio_path.exists():
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline"},
        )
    return {"error": "File not found"}


@app.get("/")
def root():
    return {"message": "Mental Health AI Assistant API"}


@app.get("/health")
def health():
    return {"status": "healthy"}

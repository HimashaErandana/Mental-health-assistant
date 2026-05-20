import asyncio
import edge_tts
import uuid
import logging
import re
from pathlib import Path
from typing import Optional

log = logging.getLogger("tts_service")

AUDIO_DIR = Path("D:/My projects/Agentic AI/Metal helath assistance/Backend/tts_output")
AUDIO_DIR.mkdir(exist_ok=True)

VOICE_OPTIONS = [
    "en-US-JennyNeural",
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "en-GB-SoniaNeural",
    "en-GB-ThomasNeural",
]


def clean_text_for_tts(text: str) -> str:
    """Clean text to remove asterisks and markdown for better TTS"""
    # Remove bold markers **text** -> text
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    # Remove bullet markers * or - at start of lines
    text = re.sub(r"^[\*\-]\s+", "", text, flags=re.MULTILINE)
    # Remove headers # text ->
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    # Remove code blocks ``` ```
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code `
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Clean up extra whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def generate_audio_file(text: str, filename: Optional[str] = None) -> str:
    # Clean the text
    text = clean_text_for_tts(text)

    if not filename:
        filename = f"tts_{uuid.uuid4().hex}.mp3"
    output_path = str(AUDIO_DIR / filename)

    # Run the async function in a new thread with its own event loop
    import concurrent.futures

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
            loop.run_until_complete(communicate.save(output_path))
        finally:
            loop.close()
        return output_path

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(_run)
        return future.result()


async def stream_audio_async(text: str):
    communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
    async for chunk in communicate.stream():
        yield chunk


def get_available_voices():
    return VOICE_OPTIONS


class TTSService:
    def __init__(self, voice: str = "en-US-JennyNeural"):
        self.voice = voice

    def generate_audio(self, text: str, filename: Optional[str] = None) -> str:
        return generate_audio_file(text, filename)

    async def stream_audio(self, text: str):
        communicate = edge_tts.Communicate(text, self.voice)
        async for chunk in communicate.stream():
            yield chunk


tts_service = TTSService(voice="en-US-JennyNeural")

import whisper


def transcribe(audio_path: str, model_name: str = "small.en") -> str:
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path)
    return result["text"]


def load_model(model_name: str = "small.en"):
    return whisper.load_model(model_name)


class WhisperSTT:
    def __init__(self, model_name: str = "small.en"):
        self.model = whisper.load_model(model_name)

    def transcribe(self, audio_path: str) -> str:
        result = self.model.transcribe(audio_path)
        return result["text"]

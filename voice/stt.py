import sounddevice as sd
import whisper

from configs.config import WHISPER_MODEL
from voice.vad import VoiceActivityDetector


class SpeechToText:
    def __init__(self, model_name=None):
        model_name = model_name or WHISPER_MODEL
        print(f"Loading Whisper model ({model_name})...")
        self.model = whisper.load_model(model_name)
        print("Whisper ready.")
        self.vad = VoiceActivityDetector()

    def listen(self, duration=5, sample_rate=16000):
        audio = self.vad.listen()

        if audio is None:
            return ""

        result = self.model.transcribe(audio.flatten())

        return result["text"].strip()

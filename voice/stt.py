import tempfile

import sounddevice as sd
import whisper


class SpeechToText:
    def __init__(self, model_name="base"):
        print("Loading Whisper model...")
        self.model = whisper.load_model(model_name)
        print("Whisper ready.")

    def listen(self, duration=5, sample_rate=16000):
        print(f"\nSpeak now ({duration} seconds)...")

        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
        )

        sd.wait()

        result = self.model.transcribe(recording.flatten())

        return result["text"].strip()

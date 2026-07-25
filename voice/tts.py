import subprocess
from pathlib import Path

import numpy as np
import sounddevice as sd


class TextToSpeech:
    def __init__(self):
        self.piper = Path("assets/piper/piper.exe")
        self.voice = Path(
            "assets/piper/voices/en_US-lessac-medium.onnx"
        )
        self.sample_rate = 22050

    def speak(self, text: str):
        proc = subprocess.run(
            [
                str(self.piper),
                "--model",
                str(self.voice),
                "--output-raw",
            ],
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        audio = np.frombuffer(proc.stdout, dtype=np.int16)
        sd.play(audio, self.sample_rate)
        sd.wait()

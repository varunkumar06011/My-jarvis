import numpy as np
import sounddevice as sd

from openwakeword import Model

from configs.config import WAKE_WORD, WAKE_THRESHOLD, SAMPLE_RATE


class WakeWordDetector:
    def __init__(self):
        self.model = Model(
            wakeword_models=[WAKE_WORD],
            inference_framework="onnx",
        )
        self.sample_rate = SAMPLE_RATE

    def listen(self):
        target_size = 1280
        block_size = 512

        print("\n💤 Waiting for wake word... (say \"Hey Jarvis\")")

        buffer = np.zeros(0, dtype=np.float32)

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=block_size,
        ) as stream:
            while True:
                chunk, _ = stream.read(block_size)
                chunk = chunk.flatten()

                buffer = np.concatenate([buffer, chunk])

                if len(buffer) < target_size:
                    continue

                frame = buffer[:target_size]
                buffer = buffer[target_size:]

                prediction = self.model.predict(frame)
                score = prediction.get(WAKE_WORD, 0)

                if score > 0.01:
                    bar = "█" * int(score * 30)
                    print(f"  [{score:.2f}] {bar}")

                if score >= WAKE_THRESHOLD:
                    print(f"\n🔔 Wake word detected! (score: {score:.2f})")
                    return True

import torch
import numpy as np
import sounddevice as sd

from silero_vad import load_silero_vad, get_speech_timestamps

from configs.config import SAMPLE_RATE, SILENCE_TIMEOUT, MAX_RECORD_SECONDS


class VoiceActivityDetector:
    def __init__(self):
        self.model = load_silero_vad()
        self.sample_rate = SAMPLE_RATE

    def listen(self):
        chunk_duration = 0.5
        chunk_size = int(chunk_duration * self.sample_rate)

        audio_chunks = []
        total_samples = 0
        max_samples = int(MAX_RECORD_SECONDS * self.sample_rate)

        speech_detected = False
        silence_frames = 0
        silence_threshold = int(SILENCE_TIMEOUT / chunk_duration)
        waiting_frames = 0
        max_waiting_frames = int(30 / chunk_duration)

        print("\n🎤 Listening...")

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=chunk_size,
        ) as stream:
            while True:
                if total_samples >= max_samples:
                    break

                chunk, _ = stream.read(chunk_size)
                chunk = chunk.flatten()

                tensor = torch.from_numpy(chunk)
                prob = self.model(tensor, self.sample_rate).item()

                if prob > 0.5:
                    if not speech_detected:
                        speech_detected = True
                        print("🟢 Speech detected...")
                    audio_chunks.append(chunk)
                    total_samples += len(chunk)
                    silence_frames = 0
                else:
                    if speech_detected:
                        audio_chunks.append(chunk)
                        total_samples += len(chunk)
                        silence_frames += 1

                        if silence_frames >= silence_threshold:
                            print("🔴 Processing...")
                            break
                    else:
                        waiting_frames += 1
                        if waiting_frames >= max_waiting_frames:
                            return None

        if not audio_chunks:
            return None

        return np.concatenate(audio_chunks)

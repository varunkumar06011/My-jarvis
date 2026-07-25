from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout

from configs.config import MODEL_NAME, WHISPER_MODEL, WAKE_WORD, SAMPLE_RATE


class ModelsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🤖 Models")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        llm_group = QGroupBox("LLM (Ollama)")
        llm_form = QFormLayout(llm_group)
        llm_form.addRow("Model:", QLabel(MODEL_NAME))
        llm_form.addRow("Engine:", QLabel("Ollama (CPU-only)"))
        layout.addWidget(llm_group)

        stt_group = QGroupBox("Speech-to-Text (Whisper)")
        stt_form = QFormLayout(stt_group)
        stt_form.addRow("Model:", QLabel(WHISPER_MODEL))
        stt_form.addRow("Engine:", QLabel("OpenAI Whisper"))
        stt_form.addRow("Sample Rate:", QLabel(f"{SAMPLE_RATE} Hz"))
        layout.addWidget(stt_group)

        tts_group = QGroupBox("Text-to-Speech (Piper)")
        tts_form = QFormLayout(tts_group)
        tts_form.addRow("Engine:", QLabel("Piper (offline)"))
        tts_form.addRow("Output:", QLabel("Raw PCM → sounddevice"))
        layout.addWidget(tts_group)

        vad_group = QGroupBox("Voice Activity Detection")
        vad_form = QFormLayout(vad_group)
        vad_form.addRow("Engine:", QLabel("Silero VAD"))
        layout.addWidget(vad_group)

        wake_group = QGroupBox("Wake Word")
        wake_form = QFormLayout(wake_group)
        wake_form.addRow("Model:", QLabel(WAKE_WORD))
        wake_form.addRow("Engine:", QLabel("OpenWakeWord (ONNX)"))
        layout.addWidget(wake_group)

        layout.addStretch()

    def refresh(self):
        pass

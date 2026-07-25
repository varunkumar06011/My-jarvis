from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout

from configs.config import MODEL_NAME, WHISPER_MODEL, WAKE_WORD, SAMPLE_RATE
from core.service_registry import registry


class ModelsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🤖 Models")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        self.llm_group = QGroupBox("LLM (Ollama)")
        self.llm_form = QFormLayout(self.llm_group)
        self.llm_model_label = QLabel(MODEL_NAME)
        self.llm_engine_label = QLabel("Ollama (CPU-only)")
        self.llm_status_label = QLabel("—")
        self.llm_form.addRow("Model:", self.llm_model_label)
        self.llm_form.addRow("Engine:", self.llm_engine_label)
        self.llm_form.addRow("Status:", self.llm_status_label)
        layout.addWidget(self.llm_group)

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
        try:
            if registry.has("llm"):
                llm = registry.get("llm")
                if hasattr(llm, "client") and llm.client:
                    self.llm_status_label.setText("✅ Connected")
                    self.llm_status_label.setObjectName("statusOk")
                else:
                    self.llm_status_label.setText("⚠ No connection")
                    self.llm_status_label.setObjectName("statusBad")
            else:
                self.llm_status_label.setText("—")
        except Exception:
            self.llm_status_label.setText("⚠ Error")

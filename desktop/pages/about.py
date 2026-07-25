from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from configs.config import APP_NAME, VERSION


class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("ℹ About")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        info = QLabel(f"""
        <h2>{APP_NAME} v{VERSION}</h2>
        <p>Offline-first AI assistant with voice, tools, and intelligence.</p>
        <hr>
        <p><b>Architecture:</b></p>
        <ul>
            <li>LLM: Ollama (Qwen 2.5 Coder)</li>
            <li>STT: OpenAI Whisper</li>
            <li>TTS: Piper (offline)</li>
            <li>VAD: Silero</li>
            <li>Wake Word: OpenWakeWord</li>
            <li>GUI: PySide6 (Qt)</li>
        </ul>
        <hr>
        <p><b>Infrastructure:</b></p>
        <ul>
            <li>Event Bus</li>
            <li>Service Registry</li>
            <li>Health Manager</li>
            <li>Task Queue</li>
            <li>Lifecycle Manager</li>
        </ul>
        <p style='color: #666;'>Built with ❤ for offline AI.</p>
        """)
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()

    def refresh(self):
        pass

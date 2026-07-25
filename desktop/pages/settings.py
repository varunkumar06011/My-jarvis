from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout, QComboBox,
    QCheckBox, QSlider, QPushButton, QGroupBox, QHBoxLayout,
)
from PySide6.QtCore import Qt

from configs.config import (
    MODEL_NAME, WHISPER_MODEL, WAKE_WORD, WAKE_THRESHOLD,
    SILENCE_TIMEOUT, MAX_RECORD_SECONDS, SAMPLE_RATE,
)
from app import settings


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("⚙ Settings")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        voice_group = QGroupBox("Voice Settings")
        voice_form = QFormLayout(voice_group)

        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_combo.setCurrentText(WHISPER_MODEL)
        voice_form.addRow("Whisper Model:", self.whisper_combo)

        self.wake_check = QCheckBox("Enable Wake Word")
        self.wake_check.setChecked(True)
        voice_form.addRow("Wake Word:", self.wake_check)

        self.wake_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.wake_threshold_slider.setRange(10, 90)
        self.wake_threshold_slider.setValue(int(WAKE_THRESHOLD * 100))
        self.wake_threshold_label = QLabel(f"{WAKE_THRESHOLD:.2f}")
        self.wake_threshold_slider.valueChanged.connect(
            lambda v: self.wake_threshold_label.setText(f"{v / 100:.2f}")
        )
        voice_form.addRow("Wake Threshold:", self.wake_threshold_slider)
        voice_form.addRow("", self.wake_threshold_label)

        self.silence_slider = QSlider(Qt.Orientation.Horizontal)
        self.silence_slider.setRange(3, 30)
        self.silence_slider.setValue(int(SILENCE_TIMEOUT * 10))
        self.silence_label = QLabel(f"{SILENCE_TIMEOUT:.1f}s")
        self.silence_slider.valueChanged.connect(
            lambda v: self.silence_label.setText(f"{v / 10:.1f}s")
        )
        voice_form.addRow("Silence Timeout:", self.silence_slider)
        voice_form.addRow("", self.silence_label)

        layout.addWidget(voice_group)

        startup_group = QGroupBox("Windows Startup")
        startup_layout = QHBoxLayout(startup_group)

        self.autostart_check = QCheckBox("Start Jarvis with Windows")
        self.autostart_check.setChecked(settings.is_auto_start_enabled())
        self.autostart_check.stateChanged.connect(self._toggle_autostart)

        startup_layout.addWidget(self.autostart_check)
        layout.addWidget(startup_group)

        model_group = QGroupBox("AI Model")
        model_form = QFormLayout(model_group)
        model_form.addRow("Current Model:", QLabel(MODEL_NAME))
        layout.addWidget(model_group)

        layout.addStretch()

    def _toggle_autostart(self, state):
        if state == 2:
            settings.enable_auto_start()
        else:
            settings.disable_auto_start()

    def refresh(self):
        self.autostart_check.setChecked(settings.is_auto_start_enabled())

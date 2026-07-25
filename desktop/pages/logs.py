from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
    QComboBox,
)
from PySide6.QtCore import QTimer


class LogsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._filter = "all"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("📜 Logs")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["all", "USER", "JARVIS", "VOICE USER"])
        self.filter_combo.currentTextChanged.connect(self._on_filter)
        header.addWidget(QLabel("Filter:"))
        header.addWidget(self.filter_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)

        layout.addLayout(header)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setObjectName("chatDisplay")
        layout.addWidget(self.log_display)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)

        self.refresh()

    def _on_filter(self, text):
        self._filter = text
        self.refresh()

    def refresh(self):
        log_file = Path(__file__).parent.parent.parent / "logs" / "jarvis.log"

        if not log_file.exists():
            self.log_display.setPlainText("No logs found.")
            return

        try:
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as e:
            self.log_display.setPlainText(f"Error reading logs: {e}")
            return

        if self._filter != "all":
            lines = [l for l in lines if self._filter in l]

        recent = lines[-200:] if len(lines) > 200 else lines
        self.log_display.setPlainText("\n".join(recent))

        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )

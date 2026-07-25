import time
import psutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
)
from PySide6.QtCore import QTimer

from core.service_registry import registry
from core.event_bus import bus
from configs.config import MODEL_NAME, WHISPER_MODEL, WAKE_WORD


class StatCard(QFrame):
    def __init__(self, title, value="—"):
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statLabel")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(value)


class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🏠 Dashboard")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(12)

        self.state_card = StatCard("Lifecycle State")
        self.model_card = StatCard("Active Model")
        self.whisper_card = StatCard("Whisper Model")
        self.wake_card = StatCard("Wake Word")
        self.cpu_card = StatCard("CPU Usage")
        self.mem_card = StatCard("Memory Usage")
        self.plugins_card = StatCard("Loaded Plugins")
        self.services_card = StatCard("Registered Services")
        self.uptime_card = StatCard("Uptime")
        self.health_card = StatCard("Health Status")

        cards = [
            (self.state_card, 0, 0), (self.model_card, 0, 1),
            (self.whisper_card, 0, 2), (self.wake_card, 1, 0),
            (self.cpu_card, 1, 1), (self.mem_card, 1, 2),
            (self.plugins_card, 2, 0), (self.services_card, 2, 1),
            (self.uptime_card, 2, 2), (self.health_card, 3, 0),
        ]

        for card, row, col in cards:
            grid.addWidget(card, row, col)

        layout.addLayout(grid)
        layout.addStretch()

        self.start_time = time.time()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)

        self.refresh()

    def refresh(self):
        if registry.has("lifecycle"):
            lc = registry.get("lifecycle")
            self.state_card.set_value(lc.state.value)

        self.model_card.set_value(MODEL_NAME)
        self.whisper_card.set_value(WHISPER_MODEL)
        self.wake_card.set_value(WAKE_WORD)

        try:
            cpu = psutil.cpu_percent(interval=0.5)
            self.cpu_card.set_value(f"{cpu:.1f}%")
        except Exception:
            self.cpu_card.set_value("—")

        try:
            mem = psutil.virtual_memory()
            self.mem_card.set_value(f"{mem.percent:.1f}%")
        except Exception:
            self.mem_card.set_value("—")

        if registry.has("tools"):
            tools = registry.get("tools")
            self.plugins_card.set_value(f"{len(tools)} plugins")

        self.services_card.set_value(f"{len(registry.list_services())} services")

        uptime = int(time.time() - self.start_time)
        mins, secs = divmod(uptime, 60)
        hours, mins = divmod(mins, 60)
        self.uptime_card.set_value(f"{hours:02d}:{mins:02d}:{secs:02d}")

        self.health_card.set_value("✅ OK")

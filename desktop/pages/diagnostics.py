from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QFormLayout,
)
from PySide6.QtCore import Qt, QTimer

from core.service_registry import registry
from core.event_bus import bus
from core.health_manager import health


class DiagnosticsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._recent_events = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📊 Diagnostics")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        services_group = QGroupBox("Registered Services")
        services_layout = QVBoxLayout(services_group)

        self.services_table = QTableWidget(0, 2)
        self.services_table.setHorizontalHeaderLabels(["Service", "Available"])
        self.services_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.services_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.services_table.setColumnWidth(1, 100)
        services_layout.addWidget(self.services_table)

        layout.addWidget(services_group)

        health_group = QGroupBox("Health Checks")
        health_layout = QFormLayout(health_group)

        self.health_labels = {}
        for check_name in health._checks:
            lbl = QLabel("—")
            self.health_labels[check_name] = lbl
            health_layout.addRow(f"{check_name}:", lbl)

        layout.addWidget(health_group)

        events_group = QGroupBox("Recent Events")
        events_layout = QVBoxLayout(events_group)

        self.events_table = QTableWidget(0, 2)
        self.events_table.setHorizontalHeaderLabels(["Event", "Data"])
        self.events_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.events_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.events_table.setColumnWidth(0, 200)
        events_layout.addWidget(self.events_table)

        layout.addWidget(events_group)

        self._subscribe_events()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(3000)

        self.refresh()

    def _subscribe_events(self):
        event_types = [
            "ApplicationStarted", "ApplicationStopped", "WakeWordDetected",
            "SpeechStarted", "SpeechFinished", "ToolExecuted", "LLMResponse",
            "HealthCheckFailed", "HealthCheckPassed", "TaskStarted",
            "TaskCompleted", "TaskFailed",
        ]
        for et in event_types:
            bus.subscribe(et, lambda data, et=et: self._add_event(et, data))

    def _add_event(self, event_type, data):
        self._recent_events.insert(0, (event_type, str(data)[:80] if data else ""))
        self._recent_events = self._recent_events[:20]

    def refresh(self):
        services = registry.list_services()
        self.services_table.setRowCount(len(services))
        for i, name in enumerate(services):
            self.services_table.setItem(i, 0, QTableWidgetItem(name))
            self.services_table.setItem(i, 1, QTableWidgetItem("✅"))

        results = health.run_all_checks()
        for name, ok in results.items():
            if name in self.health_labels:
                self.health_labels[name].setText("✅ OK" if ok else "❌ Failed")

        self.events_table.setRowCount(len(self._recent_events))
        for i, (event, data) in enumerate(self._recent_events):
            self.events_table.setItem(i, 0, QTableWidgetItem(event))
            self.events_table.setItem(i, 1, QTableWidgetItem(data))

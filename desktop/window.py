from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QListWidget,
    QStackedWidget, QLabel, QStatusBar,
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont

from desktop.theme import DARK_QSS
from desktop.pages.home import HomePage
from desktop.pages.chat import ChatPage
from desktop.pages.settings import SettingsPage
from desktop.pages.plugins import PluginsPage
from desktop.pages.diagnostics import DiagnosticsPage
from desktop.pages.logs import LogsPage
from desktop.pages.models import ModelsPage
from desktop.pages.about import AboutPage
from desktop.pages.performance import PerformancePage
from desktop.pages.automation import AutomationPage
from desktop.pages.cto import CTOPage
from desktop.pages.learning import LearningPage
from desktop.pages.marketplace import MarketplacePage

from core.event_bus import bus
from core.service_registry import registry


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jarvis")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        self.setStyleSheet(DARK_QSS)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setCurrentRow(0)

        pages = [
            ("🏠  Home", HomePage()),
            ("💬  Chat", ChatPage()),
            ("🤖  Automation", AutomationPage()),
            ("📊  Performance", PerformancePage()),
            ("👔  AI CTO", CTOPage()),
            ("🧠  Learning", LearningPage()),
            ("⚙  Settings", SettingsPage()),
            ("🧩  Plugins", PluginsPage()),
            ("🏪  Marketplace", MarketplacePage()),
            ("📊  Diagnostics", DiagnosticsPage()),
            ("📜  Logs", LogsPage()),
            ("🤖  Models", ModelsPage()),
            ("ℹ  About", AboutPage()),
        ]

        self.pages = {}
        for label, page in pages:
            self.sidebar.addItem(label)
            self.pages[label] = page

        self.stack = QStackedWidget()
        for _, page in pages:
            self.stack.addWidget(page)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack)

        self.setCentralWidget(central)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self._setup_event_subscriptions()

        self._pages_by_name = {label: page for label, page in pages}

    def _setup_event_subscriptions(self):
        bus.subscribe("ApplicationStarted", self._on_app_started)
        bus.subscribe("WakeWordDetected", self._on_wake_word)
        bus.subscribe("SpeechFinished", self._on_speech_finished)
        bus.subscribe("LLMResponse", self._on_llm_response)
        bus.subscribe("ToolExecuted", self._on_tool_executed)
        bus.subscribe("HealthCheckFailed", self._on_health_failed)

    @Slot()
    def _on_app_started(self, data):
        self.status_bar.showMessage("Application Started")

    @Slot()
    def _on_wake_word(self, data):
        self.status_bar.showMessage("🔔 Wake word detected")

    @Slot()
    def _on_speech_finished(self, data):
        text = data.get("text", "") if data else ""
        self.status_bar.showMessage(f"Heard: {text[:50]}")
        chat_page = self._pages_by_name.get("💬  Chat")
        if chat_page:
            chat_page.add_message("user", text)

    @Slot()
    def _on_llm_response(self, data):
        response = data.get("response", "") if data else ""
        self.status_bar.showMessage("Response ready")
        chat_page = self._pages_by_name.get("💬  Chat")
        if chat_page:
            chat_page.add_message("assistant", response)

    @Slot()
    def _on_tool_executed(self, data):
        result = data.get("result", "") if data else ""
        input_text = data.get("input", "") if data else ""
        self.status_bar.showMessage(f"Tool: {result[:50]}")
        chat_page = self._pages_by_name.get("💬  Chat")
        if chat_page:
            chat_page.add_message("user", input_text)
            chat_page.add_message("assistant", result)

    @Slot()
    def _on_health_failed(self, data):
        service = data.get("service", "unknown") if data else "unknown"
        self.status_bar.showMessage(f"⚠ Health check failed: {service}")

    def refresh_all(self):
        for page in self._pages_by_name.values():
            if hasattr(page, "refresh"):
                page.refresh()

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel,
)
from PySide6.QtCore import Qt, QThread, Signal

from core.service_registry import registry
from core.router import route


class ChatWorker(QThread):
    response_ready = Signal(str)
    tool_response = Signal(str)

    def __init__(self, message):
        super().__init__()
        self.message = message

    def run(self):
        tool_reply = route(self.message)
        if tool_reply is not None:
            self.tool_response.emit(tool_reply)
            return

        if registry.has("llm"):
            llm = registry.get("llm")
            reply = llm.chat(self.message)
            self.response_ready.emit(reply)
        else:
            self.response_ready.emit("Error: LLM not available")


class ChatPage(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("💬 Chat")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_chat)
        header.addWidget(self.clear_btn)

        layout.addLayout(header)

        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message...")
        self.input_field.returnPressed.connect(self.send_message)
        input_row.addWidget(self.input_field)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row)

        self._init_html()

    def _init_html(self):
        self.chat_display.setHtml("""
        <style>
            body { font-family: 'Segoe UI'; font-size: 14px; color: #e0e0e0; }
            .user { color: #5dade2; margin: 8px 0; }
            .jarvis { color: #00d9a3; margin: 8px 0; }
            .label { font-weight: bold; }
        </style>
        <div style='text-align:center; color:#666; padding:40px;'>
            Start a conversation with Jarvis
        </div>
        """)

    def add_message(self, role, text):
        if role == "user":
            label = "You"
            css_class = "user"
        else:
            label = "Jarvis"
            css_class = "jarvis"

        import html as html_mod
        safe_text = html_mod.escape(text)

        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(
            f"<div class='{css_class}'><span class='label'>{label}:</span> {safe_text}</div>"
        )

        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.add_message("user", text)
        self.input_field.clear()
        self.send_btn.setEnabled(False)

        self._worker = ChatWorker(text)
        self._worker.response_ready.connect(self._on_response)
        self._worker.tool_response.connect(self._on_tool_response)
        self._worker.start()

    def _on_response(self, reply):
        self.add_message("assistant", reply)
        self.send_btn.setEnabled(True)

    def _on_tool_response(self, reply):
        self.add_message("assistant", reply)
        self.send_btn.setEnabled(True)

    def clear_chat(self):
        self._init_html()

    def refresh(self):
        pass

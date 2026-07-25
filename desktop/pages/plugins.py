from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QPushButton,
    QHBoxLayout, QGridLayout, QScrollArea,
)
from PySide6.QtCore import Qt

from core.service_registry import registry
from core.tool_registry import TOOLS, _discover_tools


class PluginCard(QFrame):
    def __init__(self, name, description, on_reload=None, on_toggle=None, enabled=True):
        super().__init__()
        self.setObjectName("card")
        self.name = name
        self._enabled = enabled
        self._on_toggle = on_toggle

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        name_label = QLabel(f"🧩 {name}")
        name_label.setObjectName("statValue")
        header.addWidget(name_label)
        header.addStretch()

        self.status_label = QLabel("✅ Enabled" if enabled else "⛔ Disabled")
        self.status_label.setObjectName("statusOk" if enabled else "statusBad")
        header.addWidget(self.status_label)

        layout.addLayout(header)

        desc_label = QLabel(description)
        desc_label.setObjectName("statLabel")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        btn_row = QHBoxLayout()
        reload_btn = QPushButton("Reload")
        reload_btn.clicked.connect(lambda: on_reload(name) if on_reload else None)
        btn_row.addWidget(reload_btn)

        self.toggle_btn = QPushButton("Disable" if enabled else "Enable")
        self.toggle_btn.setObjectName("dangerBtn" if enabled else "")
        self.toggle_btn.clicked.connect(self._handle_toggle)
        btn_row.addWidget(self.toggle_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _handle_toggle(self):
        self._enabled = not self._enabled
        self.status_label.setText("✅ Enabled" if self._enabled else "⛔ Disabled")
        self.status_label.setObjectName("statusOk" if self._enabled else "statusBad")
        self.toggle_btn.setText("Disable" if self._enabled else "Enable")
        self.toggle_btn.setObjectName("dangerBtn" if self._enabled else "")
        if self._on_toggle:
            self._on_toggle(self.name, self._enabled)


class PluginsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._disabled = set()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🧩 Plugins")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        self.count_label = QLabel(f"{len(TOOLS)} plugins loaded")
        self.count_label.setObjectName("statLabel")
        layout.addWidget(self.count_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(12)

        self._populate_cards()

        self.scroll.setWidget(self._container)
        layout.addWidget(self.scroll)

    def _populate_cards(self):
        for i in reversed(range(self._grid.count())):
            widget = self._grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        for i, (name, module) in enumerate(TOOLS.items()):
            desc = module.TOOL.get("description", "No description")
            enabled = name not in self._disabled
            card = PluginCard(
                name, desc,
                on_reload=self._reload_plugin,
                on_toggle=self._toggle_plugin,
                enabled=enabled,
            )
            self._grid.addWidget(card, i // 2, i % 2)

    def _reload_plugin(self, name: str):
        try:
            new_tools = _discover_tools()
            TOOLS.clear()
            TOOLS.update(new_tools)
            if registry.has("tools"):
                registry.remove("tools")
            registry.register("tools", TOOLS)
            self._populate_cards()
            self.count_label.setText(f"{len(TOOLS)} plugins loaded")
        except Exception as e:
            print(f"[Plugins] Reload failed: {e}")

    def _toggle_plugin(self, name: str, enabled: bool):
        if enabled:
            self._disabled.discard(name)
        else:
            self._disabled.add(name)

    def refresh(self):
        count = len(TOOLS)
        self.count_label.setText(f"{count} plugins loaded")

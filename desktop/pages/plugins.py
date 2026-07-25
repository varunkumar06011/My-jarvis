from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QPushButton,
    QHBoxLayout, QGridLayout, QScrollArea,
)
from PySide6.QtCore import Qt

from core.service_registry import registry
from core.tool_registry import TOOLS


class PluginCard(QFrame):
    def __init__(self, name, description):
        super().__init__()
        self.setObjectName("card")
        self.name = name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        name_label = QLabel(f"🧩 {name}")
        name_label.setObjectName("statValue")
        header.addWidget(name_label)
        header.addStretch()

        status = QLabel("✅ Enabled")
        status.setObjectName("statusOk")
        header.addWidget(status)

        layout.addLayout(header)

        desc_label = QLabel(description)
        desc_label.setObjectName("statLabel")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        btn_row = QHBoxLayout()
        reload_btn = QPushButton("Reload")
        disable_btn = QPushButton("Disable")
        disable_btn.setObjectName("dangerBtn")
        btn_row.addWidget(reload_btn)
        btn_row.addWidget(disable_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)


class PluginsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🧩 Plugins")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        count_label = QLabel(f"{len(TOOLS)} plugins loaded")
        count_label.setObjectName("statLabel")
        layout.addWidget(count_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(12)

        for i, (name, module) in enumerate(TOOLS.items()):
            desc = module.TOOL.get("description", "No description")
            card = PluginCard(name, desc)
            grid.addWidget(card, i // 2, i % 2)

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def refresh(self):
        pass

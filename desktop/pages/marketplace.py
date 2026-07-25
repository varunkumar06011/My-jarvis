from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QComboBox,
)
from PySide6.QtCore import QTimer

from marketplace.registry import marketplace


class MarketplacePage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🧩 Plugin Marketplace")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._discover_tab(), "Discover")
        tabs.addTab(self._installed_tab(), "Installed")
        tabs.addTab(self._stats_tab(), "Stats")

        layout.addWidget(tabs)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)

        self.refresh()

    def _discover_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search plugins...")
        self.search_input.textChanged.connect(self._refresh_discover)
        search_row.addWidget(self.search_input)

        self.category_combo = QComboBox()
        self.category_combo.addItem("All", "")
        for cat in marketplace.get_categories():
            self.category_combo.addItem(cat.replace("_", " ").title(), cat)
        self.category_combo.currentTextChanged.connect(self._refresh_discover)
        search_row.addWidget(QLabel("Category:"))
        search_row.addWidget(self.category_combo)

        layout.addLayout(search_row)

        self.discover_table = QTableWidget(0, 5)
        self.discover_table.setHorizontalHeaderLabels(["Name", "Version", "Category", "Downloads", "Verified"])
        self.discover_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.discover_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.discover_table.setColumnWidth(1, 80)
        self.discover_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.discover_table.setColumnWidth(2, 120)
        self.discover_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.discover_table.setColumnWidth(3, 80)
        self.discover_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.discover_table.setColumnWidth(4, 70)
        layout.addWidget(self.discover_table)

        return tab

    def _installed_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        update_btn = QPushButton("Check for Updates")
        update_btn.clicked.connect(self._check_updates)
        layout.addWidget(update_btn)

        self.installed_table = QTableWidget(0, 5)
        self.installed_table.setHorizontalHeaderLabels(["Name", "Version", "Enabled", "Update Available", "Installed"])
        self.installed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.installed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.installed_table.setColumnWidth(1, 80)
        self.installed_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.installed_table.setColumnWidth(2, 70)
        self.installed_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.installed_table.setColumnWidth(3, 100)
        self.installed_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.installed_table.setColumnWidth(4, 120)
        layout.addWidget(self.installed_table)

        return tab

    def _stats_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        stats_group = QGroupBox("Marketplace Statistics")
        stats_form = QFormLayout(stats_group)
        self.mp_total_label = QLabel("0")
        self.mp_installed_label = QLabel("0")
        self.mp_verified_label = QLabel("0")
        self.mp_downloads_label = QLabel("0")
        self.mp_updates_label = QLabel("0")
        stats_form.addRow("Total Plugins:", self.mp_total_label)
        stats_form.addRow("Installed:", self.mp_installed_label)
        stats_form.addRow("Verified:", self.mp_verified_label)
        stats_form.addRow("Total Downloads:", self.mp_downloads_label)
        stats_form.addRow("Updates Available:", self.mp_updates_label)
        layout.addWidget(stats_group)

        layout.addStretch()
        return tab

    def refresh(self):
        self._refresh_discover()
        self._refresh_installed()
        self._refresh_stats()

    def _refresh_discover(self):
        query = self.search_input.text().strip()
        category = self.category_combo.currentData() if hasattr(self, "category_combo") else ""
        plugins = marketplace.discover(category=category or "", query=query, limit=30)

        self.discover_table.setRowCount(len(plugins))
        for i, p in enumerate(plugins):
            self.discover_table.setItem(i, 0, QTableWidgetItem(p.get("name", "")))
            self.discover_table.setItem(i, 1, QTableWidgetItem(p.get("version", "")))
            self.discover_table.setItem(i, 2, QTableWidgetItem(p.get("category", "").replace("_", " ").title()))
            self.discover_table.setItem(i, 3, QTableWidgetItem(str(p.get("downloads", 0))))
            self.discover_table.setItem(i, 4, QTableWidgetItem("✓" if p.get("verified") else "—"))

    def _refresh_installed(self):
        installed = marketplace.list_installed()
        self.installed_table.setRowCount(len(installed))
        for i, ip in enumerate(installed):
            self.installed_table.setItem(i, 0, QTableWidgetItem(ip.get("name", "")))
            self.installed_table.setItem(i, 1, QTableWidgetItem(ip.get("version", "")))
            self.installed_table.setItem(i, 2, QTableWidgetItem("✓" if ip.get("enabled") else "✗"))
            self.installed_table.setItem(i, 3, QTableWidgetItem("⬆" if ip.get("update_available") else "—"))
            self.installed_table.setItem(i, 4, QTableWidgetItem(ip.get("installed_at", "")[:10]))

    def _refresh_stats(self):
        s = marketplace.stats()
        self.mp_total_label.setText(str(s["total_plugins"]))
        self.mp_installed_label.setText(str(s["total_installed"]))
        self.mp_verified_label.setText(str(s["verified_plugins"]))
        self.mp_downloads_label.setText(str(s["total_downloads"]))
        self.mp_updates_label.setText(str(s["updates_available"]))

    def _check_updates(self):
        updates = marketplace.check_updates()
        self._refresh_installed()

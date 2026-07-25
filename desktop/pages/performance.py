from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt, QTimer

from core.service_registry import registry


class PerformancePage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📊 Performance Dashboard")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # ── System Metrics ──
        sys_group = QGroupBox("System Resources")
        sys_grid = QGridLayout(sys_group)

        self.cpu_label = QLabel("—")
        self.ram_label = QLabel("—")
        self.ram_used_label = QLabel("—")
        self.disk_label = QLabel("—")
        self.thread_label = QLabel("—")

        sys_grid.addWidget(QLabel("CPU:"), 0, 0)
        sys_grid.addWidget(self.cpu_label, 0, 1)
        sys_grid.addWidget(QLabel("RAM:"), 0, 2)
        sys_grid.addWidget(self.ram_label, 0, 3)
        sys_grid.addWidget(QLabel("RAM Used:"), 1, 0)
        sys_grid.addWidget(self.ram_used_label, 1, 1)
        sys_grid.addWidget(QLabel("Disk:"), 1, 2)
        sys_grid.addWidget(self.disk_label, 1, 3)
        sys_grid.addWidget(QLabel("Threads:"), 2, 0)
        sys_grid.addWidget(self.thread_label, 2, 1)

        layout.addWidget(sys_group)

        # ── Latency Metrics ──
        latency_group = QGroupBox("Latency Metrics (ms)")
        latency_layout = QVBoxLayout(latency_group)

        self.latency_table = QTableWidget(0, 5)
        self.latency_table.setHorizontalHeaderLabels(["Operation", "Avg", "P95", "P99", "Count"])
        self.latency_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            self.latency_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self.latency_table.setColumnWidth(i, 80)
        latency_layout.addWidget(self.latency_table)

        layout.addWidget(latency_group)

        # ── Event Statistics ──
        events_group = QGroupBox("Event Statistics")
        events_layout = QVBoxLayout(events_group)

        self.events_table = QTableWidget(0, 3)
        self.events_table.setHorizontalHeaderLabels(["Event", "Count", "Category"])
        self.events_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.events_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.events_table.setColumnWidth(1, 80)
        self.events_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.events_table.setColumnWidth(2, 100)
        events_layout.addWidget(self.events_table)

        layout.addWidget(events_group)

        # ── Feature Flags ──
        flags_group = QGroupBox("Feature Flags")
        flags_layout = QVBoxLayout(flags_group)

        self.flags_table = QTableWidget(0, 2)
        self.flags_table.setHorizontalHeaderLabels(["Flag", "Enabled"])
        self.flags_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.flags_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.flags_table.setColumnWidth(1, 80)
        flags_layout.addWidget(self.flags_table)

        layout.addWidget(flags_group)

        # ── Auto-refresh ──
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)

        self.refresh()

    def refresh(self):
        # System metrics
        try:
            metrics = registry.get("metrics")
            perf = metrics.performance_summary()

            self.cpu_label.setText(f"{perf.get('cpu_percent', 0):.1f}%")
            self.ram_label.setText(f"{perf.get('ram_percent', 0):.1f}%")
            self.ram_used_label.setText(f"{perf.get('ram_used_mb', 0):.0f} MB")
            self.disk_label.setText(f"{perf.get('disk_percent', 0):.1f}%")
            self.thread_label.setText(str(perf.get('thread_count', 0)))

            # Latency table
            latency_keys = [k for k in perf if isinstance(perf.get(k), dict) and "avg_ms" in perf[k]]
            self.latency_table.setRowCount(len(latency_keys))
            for i, key in enumerate(sorted(latency_keys)):
                stats = perf[key]
                self.latency_table.setItem(i, 0, QTableWidgetItem(key))
                self.latency_table.setItem(i, 1, QTableWidgetItem(f"{stats['avg_ms']:.1f}"))
                self.latency_table.setItem(i, 2, QTableWidgetItem(f"{stats['p95_ms']:.1f}"))
                self.latency_table.setItem(i, 3, QTableWidgetItem(f"{stats['p99_ms']:.1f}"))
                self.latency_table.setItem(i, 4, QTableWidgetItem(str(stats['count'])))
        except KeyError:
            pass

        # Event statistics
        try:
            event_store = registry.get("event_store")
            stats = event_store.statistics()
            by_event = stats.get("by_event", {})

            self.events_table.setRowCount(len(by_event))
            for i, (event, count) in enumerate(sorted(by_event.items(), key=lambda x: -x[1])):
                self.events_table.setItem(i, 0, QTableWidgetItem(event))
                self.events_table.setItem(i, 1, QTableWidgetItem(str(count)))
                cat = stats.get("by_category", {})
                # Find category for this event
                from core.event_store import CATEGORY_MAP
                category = CATEGORY_MAP.get(event, "")
                self.events_table.setItem(i, 2, QTableWidgetItem(category.value if hasattr(category, 'value') else str(category)))
        except KeyError:
            pass

        # Feature flags
        try:
            flag_mgr = registry.get("flag_manager")
            flags = flag_mgr.list_flags()

            self.flags_table.setRowCount(len(flags))
            for i, (name, enabled) in enumerate(sorted(flags.items())):
                self.flags_table.setItem(i, 0, QTableWidgetItem(name))
                self.flags_table.setItem(i, 1, QTableWidgetItem("✅" if enabled else "❌"))
        except KeyError:
            pass

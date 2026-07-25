from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget,
)
from PySide6.QtCore import QTimer

from ai.learning.patterns import pattern_library
from ai.learning.decisions import decision_history
from ai.learning.preferences import user_preferences


class LearningPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🧠 Learning & Improvement")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        tabs = QTabWidget()

        tabs.addTab(self._patterns_tab(), "Patterns")
        tabs.addTab(self._decisions_tab(), "Decisions")
        tabs.addTab(self._preferences_tab(), "Preferences")

        layout.addWidget(tabs)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)

        self.refresh()

    def _patterns_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        stats_group = QGroupBox("Pattern Library Stats")
        stats_form = QFormLayout(stats_group)
        self.pat_total_label = QLabel("0")
        self.pat_uses_label = QLabel("0")
        self.pat_success_label = QLabel("0%")
        stats_form.addRow("Total Patterns:", self.pat_total_label)
        stats_form.addRow("Total Uses:", self.pat_uses_label)
        stats_form.addRow("Avg Success Rate:", self.pat_success_label)
        layout.addWidget(stats_group)

        self.pat_table = QTableWidget(0, 5)
        self.pat_table.setHorizontalHeaderLabels(["Name", "Category", "Language", "Uses", "Success Rate"])
        self.pat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.pat_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.pat_table.setColumnWidth(1, 120)
        self.pat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.pat_table.setColumnWidth(2, 80)
        self.pat_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.pat_table.setColumnWidth(3, 60)
        self.pat_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.pat_table.setColumnWidth(4, 80)
        layout.addWidget(self.pat_table)

        return tab

    def _decisions_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        stats_group = QGroupBox("Decision History Stats")
        stats_form = QFormLayout(stats_group)
        self.dec_total_label = QLabel("0")
        self.dec_active_label = QLabel("0")
        stats_form.addRow("Total Decisions:", self.dec_total_label)
        stats_form.addRow("Active:", self.dec_active_label)
        layout.addWidget(stats_group)

        self.dec_table = QTableWidget(0, 4)
        self.dec_table.setHorizontalHeaderLabels(["Title", "Status", "Tags", "Created"])
        self.dec_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.dec_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.dec_table.setColumnWidth(1, 80)
        self.dec_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.dec_table.setColumnWidth(2, 150)
        self.dec_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.dec_table.setColumnWidth(3, 120)
        layout.addWidget(self.dec_table)

        return tab

    def _preferences_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        stats_group = QGroupBox("User Preferences")
        stats_form = QFormLayout(stats_group)
        self.pref_count_label = QLabel("0")
        self.style_count_label = QLabel("0")
        self.workflow_count_label = QLabel("0")
        self.fixes_count_label = QLabel("0")
        stats_form.addRow("Preferences:", self.pref_count_label)
        stats_form.addRow("Coding Style Rules:", self.style_count_label)
        stats_form.addRow("Workflow Types:", self.workflow_count_label)
        stats_form.addRow("Recorded Fixes:", self.fixes_count_label)
        layout.addWidget(stats_group)

        workflows_group = QGroupBox("Frequent Workflows")
        workflows_layout = QVBoxLayout(workflows_group)
        self.workflow_table = QTableWidget(0, 2)
        self.workflow_table.setHorizontalHeaderLabels(["Workflow", "Count"])
        self.workflow_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.workflow_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.workflow_table.setColumnWidth(1, 80)
        workflows_layout.addWidget(self.workflow_table)
        layout.addWidget(workflows_group)

        return tab

    def refresh(self):
        pat_stats = pattern_library.stats()
        self.pat_total_label.setText(str(pat_stats["total_patterns"]))
        self.pat_uses_label.setText(str(pat_stats["total_uses"]))
        self.pat_success_label.setText(f"{pat_stats['avg_success_rate']:.0%}")

        patterns = pattern_library.search(limit=20)
        self.pat_table.setRowCount(len(patterns))
        for i, p in enumerate(patterns):
            self.pat_table.setItem(i, 0, QTableWidgetItem(p.get("name", "")))
            self.pat_table.setItem(i, 1, QTableWidgetItem(p.get("category", "")))
            self.pat_table.setItem(i, 2, QTableWidgetItem(p.get("language", "")))
            self.pat_table.setItem(i, 3, QTableWidgetItem(str(p.get("use_count", 0))))
            self.pat_table.setItem(i, 4, QTableWidgetItem(f"{p.get('success_rate', 0):.0%}"))

        dec_stats = decision_history.stats()
        self.dec_total_label.setText(str(dec_stats["total_decisions"]))
        self.dec_active_label.setText(str(dec_stats["active"]))

        decisions = decision_history.search(limit=20)
        self.dec_table.setRowCount(len(decisions))
        for i, d in enumerate(decisions):
            self.dec_table.setItem(i, 0, QTableWidgetItem(d.get("title", "")))
            self.dec_table.setItem(i, 1, QTableWidgetItem(d.get("status", "")))
            self.dec_table.setItem(i, 2, QTableWidgetItem(", ".join(d.get("tags", []))))
            self.dec_table.setItem(i, 3, QTableWidgetItem(d.get("created_at", "")[:10]))

        pref_stats = user_preferences.stats()
        self.pref_count_label.setText(str(pref_stats["total_prefs"]))
        self.style_count_label.setText(str(pref_stats["coding_style_rules"]))
        self.workflow_count_label.setText(str(pref_stats["workflow_types"]))
        self.fixes_count_label.setText(str(pref_stats["recorded_fixes"]))

        workflows = pref_stats.get("top_workflows", [])
        self.workflow_table.setRowCount(len(workflows))
        for i, w in enumerate(workflows):
            self.workflow_table.setItem(i, 0, QTableWidgetItem(w.get("name", "")))
            self.workflow_table.setItem(i, 1, QTableWidgetItem(str(w.get("count", 0))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QProgressBar, QComboBox,
)
from PySide6.QtCore import Qt, QTimer


class AutomationPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🤖 Automation Platform")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # ── Queue Status ──
        queue_group = QGroupBox("Queue Status")
        queue_layout = QHBoxLayout(queue_group)

        self.queue_pending = QLabel("0")
        self.queue_active = QLabel("0")
        self.queue_workers = QLabel("0")

        queue_layout.addWidget(QLabel("Pending:"))
        queue_layout.addWidget(self.queue_pending)
        queue_layout.addWidget(QLabel("Active:"))
        queue_layout.addWidget(self.queue_active)
        queue_layout.addWidget(QLabel("Workers:"))
        queue_layout.addWidget(self.queue_workers)
        queue_layout.addStretch()

        layout.addWidget(queue_group)

        # ── Active Automations ──
        active_group = QGroupBox("Active Automations")
        active_layout = QVBoxLayout(active_group)

        self.active_table = QTableWidget(0, 4)
        self.active_table.setHorizontalHeaderLabels(["Automation ID", "Workflow", "State", "Progress"])
        self.active_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.active_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.active_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.active_table.setColumnWidth(2, 120)
        self.active_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.active_table.setColumnWidth(3, 100)
        active_layout.addWidget(self.active_table)

        layout.addWidget(active_group)

        # ── Recent History ──
        history_group = QGroupBox("Recent History")
        history_layout = QVBoxLayout(history_group)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Name", "Status", "Duration", "Steps", "Rollback"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.history_table.setColumnWidth(1, 100)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.history_table.setColumnWidth(2, 100)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.history_table.setColumnWidth(3, 60)
        self.history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.history_table.setColumnWidth(4, 80)
        history_layout.addWidget(self.history_table)

        layout.addWidget(history_group)

        # ── Pending Approvals ──
        approval_group = QGroupBox("Pending Approvals")
        approval_layout = QVBoxLayout(approval_group)

        self.approval_table = QTableWidget(0, 4)
        self.approval_table.setHorizontalHeaderLabels(["Approval ID", "Action", "Risk", "Summary"])
        self.approval_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.approval_table.setColumnWidth(0, 120)
        self.approval_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.approval_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.approval_table.setColumnWidth(2, 80)
        self.approval_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        approval_layout.addWidget(self.approval_table)

        layout.addWidget(approval_group)

        # ── Auto-refresh ──
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)

        self.refresh()

    def refresh(self):
        try:
            from core.service_registry import registry
            engine = registry.get("automation_engine")

            # Queue status
            qs = engine.get_queue_status()
            self.queue_pending.setText(str(qs.get("pending", 0)))
            self.queue_active.setText(str(qs.get("active", 0)))
            self.queue_workers.setText(str(qs.get("workers", 0)))

            # Active automations
            active_ids = engine.list_active()
            self.active_table.setRowCount(len(active_ids))
            for i, aid in enumerate(active_ids):
                status = engine.get_status(aid)
                if status:
                    self.active_table.setItem(i, 0, QTableWidgetItem(aid))
                    self.active_table.setItem(i, 1, QTableWidgetItem(status.get("context", {}).get("workflow_id", "")))
                    self.active_table.setItem(i, 2, QTableWidgetItem(status.get("state", "")))
                    self.active_table.setItem(i, 3, QTableWidgetItem("..."))

            # History
            history = engine.get_history(limit=20)
            self.history_table.setRowCount(len(history))
            for i, record in enumerate(history):
                self.history_table.setItem(i, 0, QTableWidgetItem(record.get("name", "")))
                self.history_table.setItem(i, 1, QTableWidgetItem(record.get("status", "")))
                self.history_table.setItem(i, 2, QTableWidgetItem(f"{record.get('duration_ms', 0):.0f}ms"))
                self.history_table.setItem(i, 3, QTableWidgetItem(str(len(record.get("steps", [])))))
                self.history_table.setItem(i, 4, QTableWidgetItem("✅" if record.get("rollback_available") else "—"))

            # Pending approvals
            approvals = engine.get_pending_approvals()
            self.approval_table.setRowCount(len(approvals))
            for i, ap in enumerate(approvals):
                self.approval_table.setItem(i, 0, QTableWidgetItem(ap.get("id", "")))
                self.approval_table.setItem(i, 1, QTableWidgetItem(ap.get("action", "")))
                self.approval_table.setItem(i, 2, QTableWidgetItem(ap.get("risk_level", "")))
                self.approval_table.setItem(i, 3, QTableWidgetItem(ap.get("summary", "")))

        except KeyError:
            pass
        except Exception:
            pass

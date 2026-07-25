from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal

from ai.cto.dashboard import executive_dashboard
from ai.cto.reports import report_generator
from ai.cto.architecture import architecture_analyzer


class AnalyzeWorker(QThread):
    result_ready = Signal(dict)

    def run(self):
        result = architecture_analyzer.analyze()
        self.result_ready.emit(result)


class CTOPage(QWidget):
    def __init__(self):
        super().__init__()
        self._analyze_worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("👔 AI CTO Dashboard")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # ── Project Health ──
        health_group = QGroupBox("Project Health")
        health_grid = QGridLayout(health_group)

        self.issues_label = QLabel("0")
        self.security_label = QLabel("0")
        self.perf_label = QLabel("0")
        self.debt_label = QLabel("—")

        health_grid.addWidget(QLabel("Open Issues:"), 0, 0)
        health_grid.addWidget(self.issues_label, 0, 1)
        health_grid.addWidget(QLabel("Security Risks:"), 0, 2)
        health_grid.addWidget(self.security_label, 0, 3)
        health_grid.addWidget(QLabel("Perf Regressions:"), 1, 0)
        health_grid.addWidget(self.perf_label, 1, 1)
        health_grid.addWidget(QLabel("Tech Debt:"), 1, 2)
        health_grid.addWidget(self.debt_label, 1, 3)

        layout.addWidget(health_group)

        # ── System Status ──
        sys_group = QGroupBox("System Status")
        sys_grid = QGridLayout(sys_group)

        self.cpu_label = QLabel("—")
        self.ram_label = QLabel("—")
        self.threads_label = QLabel("—")
        self.services_label = QLabel("—")

        sys_grid.addWidget(QLabel("CPU:"), 0, 0)
        sys_grid.addWidget(self.cpu_label, 0, 1)
        sys_grid.addWidget(QLabel("RAM:"), 0, 2)
        sys_grid.addWidget(self.ram_label, 0, 3)
        sys_grid.addWidget(QLabel("Threads:"), 1, 0)
        sys_grid.addWidget(self.threads_label, 1, 1)
        sys_grid.addWidget(QLabel("Services:"), 1, 2)
        sys_grid.addWidget(self.services_label, 1, 3)

        layout.addWidget(sys_group)

        # ── Issues Table ──
        issues_group = QGroupBox("Issues & Risks")
        issues_layout = QVBoxLayout(issues_group)

        self.issues_table = QTableWidget(0, 4)
        self.issues_table.setHorizontalHeaderLabels(["Category", "Severity", "Service", "Message"])
        self.issues_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.issues_table.setColumnWidth(0, 100)
        self.issues_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.issues_table.setColumnWidth(1, 80)
        self.issues_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.issues_table.setColumnWidth(2, 120)
        self.issues_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        issues_layout.addWidget(self.issues_table)

        layout.addWidget(issues_group)

        # ── Reports ──
        reports_group = QGroupBox("Reports")
        reports_layout = QHBoxLayout(reports_group)

        self.daily_btn = QPushButton("Generate Daily")
        self.daily_btn.clicked.connect(lambda: self._generate_report("daily"))
        self.weekly_btn = QPushButton("Generate Weekly")
        self.weekly_btn.clicked.connect(lambda: self._generate_report("weekly"))
        self.monthly_btn = QPushButton("Generate Monthly")
        self.monthly_btn.clicked.connect(lambda: self._generate_report("monthly"))

        reports_layout.addWidget(self.daily_btn)
        reports_layout.addWidget(self.weekly_btn)
        reports_layout.addWidget(self.monthly_btn)
        reports_layout.addStretch()

        layout.addWidget(reports_group)

        # ── Architecture Analysis ──
        arch_group = QGroupBox("Architecture Analysis")
        arch_layout = QVBoxLayout(arch_group)

        arch_btn_row = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze Architecture")
        self.analyze_btn.clicked.connect(self._run_analysis)
        arch_btn_row.addWidget(self.analyze_btn)
        arch_btn_row.addStretch()
        arch_layout.addLayout(arch_btn_row)

        self.arch_display = QTextEdit()
        self.arch_display.setReadOnly(True)
        self.arch_display.setMaximumHeight(200)
        arch_layout.addWidget(self.arch_display)

        layout.addWidget(arch_group)

        # ── Auto-refresh ──
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)

        self.refresh()

    def refresh(self):
        snap = executive_dashboard.snapshot()

        health = snap.get("project_health", {})
        self.issues_label.setText(str(len(health.get("issues", []))))
        self.security_label.setText(str(len(health.get("security_risks", []))))
        self.perf_label.setText(str(len(health.get("performance_regressions", []))))

        sys_status = snap.get("system_status", {})
        self.cpu_label.setText(f"{sys_status.get('cpu_percent', 0):.1f}%")
        self.ram_label.setText(f"{sys_status.get('ram_percent', 0):.1f}%")
        self.threads_label.setText(str(sys_status.get("thread_count", 0)))

        svc_health = snap.get("service_health", {})
        self.services_label.setText(f"{svc_health.get('healthy', 0)}/{svc_health.get('total_services', 0)}")

        all_issues = []
        for issue in health.get("issues", []):
            all_issues.append(("Health", issue.get("severity", ""), issue.get("service", ""), issue.get("message", "")))
        for risk in health.get("security_risks", []):
            all_issues.append(("Security", risk.get("severity", ""), "config", risk.get("message", "")))
        for reg in health.get("performance_regressions", []):
            all_issues.append(("Performance", reg.get("severity", ""), reg.get("operation", ""), f"P95: {reg.get('p95_ms', 0)}ms"))

        self.issues_table.setRowCount(len(all_issues))
        for i, (cat, sev, svc, msg) in enumerate(all_issues):
            self.issues_table.setItem(i, 0, QTableWidgetItem(cat))
            self.issues_table.setItem(i, 1, QTableWidgetItem(sev))
            self.issues_table.setItem(i, 2, QTableWidgetItem(svc))
            self.issues_table.setItem(i, 3, QTableWidgetItem(msg))

    def _generate_report(self, report_type: str):
        if report_type == "daily":
            report = report_generator.generate_daily()
        elif report_type == "weekly":
            report = report_generator.generate_weekly()
        else:
            report = report_generator.generate_monthly()
        self.arch_display.setPlainText(f"Report generated: {report.get('id', '?')}")

    def _run_analysis(self):
        self.analyze_btn.setEnabled(False)
        self.arch_display.setPlainText("Analyzing...")
        self._analyze_worker = AnalyzeWorker()
        self._analyze_worker.result_ready.connect(self._on_analysis_done)
        self._analyze_worker.start()

    def _on_analysis_done(self, result: dict):
        self.analyze_btn.setEnabled(True)
        summary = result.get("summary", {})
        text = f"""Architecture Summary:
  Modules: {summary.get('total_modules', 0)}
  Total Lines: {summary.get('total_lines', 0)}
  Classes: {summary.get('total_classes', 0)}
  Functions: {summary.get('total_functions', 0)}
  Avg Complexity: {summary.get('avg_complexity', 0)}
  Bottlenecks: {summary.get('bottleneck_count', 0)}
  Legacy Modules: {summary.get('legacy_count', 0)}
  Risk Hotspots: {summary.get('hotspot_count', 0)}
"""
        hotspots = result.get("risk_hotspots", [])
        if hotspots:
            text += "\nTop Risk Hotspots:\n"
            for hs in hotspots[:5]:
                text += f"  • {hs['module']} (complexity: {hs['complexity']}, risk: {hs['risk']})\n"

        self.arch_display.setPlainText(text)

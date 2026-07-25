from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QTabWidget, QProgressBar, QComboBox,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal

from core.service_registry import registry


class PipelineWorker(QThread):
    result_ready = Signal(dict)

    def __init__(self, task: dict):
        super().__init__()
        self._task = task

    def run(self):
        try:
            coordinator = registry.get("agent_coordinator")
            result = coordinator.run_pipeline(self._task)
            self.result_ready.emit(result)
        except Exception as e:
            self.result_ready.emit({"status": "error", "error": str(e)})


class VerifyWorker(QThread):
    result_ready = Signal(dict)

    def __init__(self, project_path: str, project_name: str):
        super().__init__()
        self._path = project_path
        self._name = project_name

    def run(self):
        try:
            vw = registry.get("verification_workflow")
            result = vw.run(self._path, self._name, skip_deploy=True)
            self.result_ready.emit(result)
        except Exception as e:
            self.result_ready.emit({"status": "error", "error": str(e)})


class EngineeringPage(QWidget):
    def __init__(self):
        super().__init__()
        self._pipeline_worker = None
        self._verify_worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🔧 AI Engineering Console")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_agents_tab(), "Agents")
        tabs.addTab(self._build_pipeline_tab(), "Pipeline")
        tabs.addTab(self._build_verify_tab(), "Verification")
        tabs.addTab(self._build_projects_tab(), "Projects")
        layout.addWidget(tabs)

        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh)
        self._timer.start(5000)

    def _build_agents_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("Engineering Agents")
        gl = QVBoxLayout(group)

        self.agents_table = QTableWidget(0, 4)
        self.agents_table.setHorizontalHeaderLabels(["Agent", "Role", "Status", "Tasks"])
        self.agents_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.agents_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.agents_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.agents_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        gl.addWidget(self.agents_table)

        layout.addWidget(group)
        return tab

    def _build_pipeline_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        input_group = QGroupBox("Pipeline Input")
        igl = QGridLayout(input_group)

        igl.addWidget(QLabel("Task:"), 0, 0)
        self.task_input = QTextEdit()
        self.task_input.setMaximumHeight(80)
        self.task_input.setPlaceholderText("Describe the project to build...")
        igl.addWidget(self.task_input, 0, 1)

        igl.addWidget(QLabel("Type:"), 1, 0)
        self.task_type = QComboBox()
        self.task_type.addItems(["plan", "implement", "fix", "review", "deploy"])
        igl.addWidget(self.task_type, 1, 1)

        self.run_pipeline_btn = QPushButton("▶ Run Pipeline")
        self.run_pipeline_btn.clicked.connect(self._run_pipeline)
        igl.addWidget(self.run_pipeline_btn, 2, 1)

        layout.addWidget(input_group)

        result_group = QGroupBox("Pipeline Results")
        rgl = QVBoxLayout(result_group)

        self.pipeline_progress = QProgressBar()
        self.pipeline_progress.setVisible(False)
        rgl.addWidget(self.pipeline_progress)

        self.pipeline_output = QTextEdit()
        self.pipeline_output.setReadOnly(True)
        rgl.addWidget(self.pipeline_output)

        layout.addWidget(result_group)
        return tab

    def _build_verify_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("End-to-End Verification")
        gl = QGridLayout(group)

        gl.addWidget(QLabel("Project:"), 0, 0)
        self.verify_project_combo = QComboBox()
        self._refresh_projects_combo()
        gl.addWidget(self.verify_project_combo, 0, 1)

        self.verify_btn = QPushButton("▶ Run Verification")
        self.verify_btn.clicked.connect(self._run_verification)
        gl.addWidget(self.verify_btn, 1, 1)

        self.verify_progress = QProgressBar()
        self.verify_progress.setVisible(False)
        gl.addWidget(self.verify_progress, 2, 0, 1, 2)

        self.verify_output = QTextEdit()
        self.verify_output.setReadOnly(True)
        gl.addWidget(self.verify_output, 3, 0, 1, 2)

        layout.addWidget(group)
        return tab

    def _build_projects_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("Registered Projects")
        gl = QVBoxLayout(group)

        self.projects_table = QTableWidget(0, 5)
        self.projects_table.setHorizontalHeaderLabels(["Name", "Language", "Framework", "Active", "Path"])
        self.projects_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.projects_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.projects_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.projects_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.projects_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        gl.addWidget(self.projects_table)

        btn_row = QHBoxLayout()
        self.refresh_projects_btn = QPushButton("↻ Refresh")
        self.refresh_projects_btn.clicked.connect(self._refresh_projects)
        btn_row.addWidget(self.refresh_projects_btn)
        gl.addLayout(btn_row)

        layout.addWidget(group)
        return tab

    def _run_pipeline(self):
        task_text = self.task_input.toPlainText().strip()
        if not task_text:
            return

        task = {
            "type": self.task_type.currentText(),
            "description": task_text,
            "requirements": task_text,
        }

        self.run_pipeline_btn.setEnabled(False)
        self.pipeline_progress.setVisible(True)
        self.pipeline_progress.setRange(0, 0)
        self.pipeline_output.clear()
        self.pipeline_output.append("Starting agent pipeline...")

        self._pipeline_worker = PipelineWorker(task)
        self._pipeline_worker.result_ready.connect(self._on_pipeline_done)
        self._pipeline_worker.start()

    def _on_pipeline_done(self, result: dict):
        self.run_pipeline_btn.setEnabled(True)
        self.pipeline_progress.setVisible(False)

        status = result.get("status", "unknown")
        self.pipeline_output.append(f"\nPipeline Status: {status}")

        if status == "completed":
            duration = result.get("duration_ms", 0)
            self.pipeline_output.append(f"Duration: {duration}ms")
            for agent_name, agent_result in result.get("results", {}).items():
                msg = agent_result.get("message", "")
                self.pipeline_output.append(f"  [{agent_name}]: {msg}")
        elif status == "failed":
            failed_at = result.get("failed_at", "unknown")
            error = result.get("error", "unknown")
            self.pipeline_output.append(f"Failed at: {failed_at}")
            self.pipeline_output.append(f"Error: {error}")
        elif status == "error":
            self.pipeline_output.append(f"Error: {result.get('error', 'unknown')}")

    def _run_verification(self):
        project_name = self.verify_project_combo.currentText()
        if not project_name:
            return

        try:
            pm = registry.get("project_manager")
            project = pm.get_project(project_name)
            if not project:
                return
            path = project.root_path
        except Exception:
            return

        self.verify_btn.setEnabled(False)
        self.verify_progress.setVisible(True)
        self.verify_progress.setRange(0, 0)
        self.verify_output.clear()
        self.verify_output.append(f"Running verification for {project_name}...")

        self._verify_worker = VerifyWorker(path, project_name)
        self._verify_worker.result_ready.connect(self._on_verify_done)
        self._verify_worker.start()

    def _on_verify_done(self, result: dict):
        self.verify_btn.setEnabled(True)
        self.verify_progress.setVisible(False)

        status = result.get("status", "unknown")
        duration = result.get("duration_s", 0)
        self.verify_output.append(f"\nVerification: {status} in {duration}s")

        for stage_name, stage_result in result.get("stages", {}).items():
            stage_status = stage_result.get("status", "ok")
            self.verify_output.append(f"  [{stage_name}]: {stage_status}")

    def _refresh_projects_combo(self):
        self.verify_project_combo.clear()
        try:
            pm = registry.get("project_manager")
            for p in pm.list_projects():
                self.verify_project_combo.addItem(p["name"])
        except Exception:
            pass

    def _refresh_projects(self):
        try:
            pm = registry.get("project_manager")
            projects = pm.list_projects()
            active = pm.get_active()
            active_name = active.name if active else None

            self.projects_table.setRowCount(len(projects))
            for i, p in enumerate(projects):
                self.projects_table.setItem(i, 0, QTableWidgetItem(p.get("name", "")))
                self.projects_table.setItem(i, 1, QTableWidgetItem(p.get("language", "")))
                self.projects_table.setItem(i, 2, QTableWidgetItem(p.get("framework", "")))
                self.projects_table.setItem(i, 3, QTableWidgetItem("●" if p.get("name") == active_name else ""))
                self.projects_table.setItem(i, 4, QTableWidgetItem(p.get("root_path", "")))
        except Exception:
            pass

    def _refresh(self):
        try:
            if registry.has("agent_coordinator"):
                coordinator = registry.get("agent_coordinator")
                agents = coordinator.list_agents()
                self.agents_table.setRowCount(len(agents))
                for i, a in enumerate(agents):
                    self.agents_table.setItem(i, 0, QTableWidgetItem(a.get("name", "")))
                    self.agents_table.setItem(i, 1, QTableWidgetItem(a.get("role", "")))
                    self.agents_table.setItem(i, 2, QTableWidgetItem(a.get("status", "idle")))
                    self.agents_table.setItem(i, 3, QTableWidgetItem(str(a.get("memory_count", 0))))
        except Exception:
            pass

        self._refresh_projects()

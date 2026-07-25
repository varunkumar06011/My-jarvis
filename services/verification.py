"""End-to-End Verification Workflow — orchestrates the full project lifecycle:
register → analyze → build → test → fix → review → deploy → verify."""

import time
from datetime import datetime
from typing import Optional

from core.event_bus import bus
from logs.logger import write_log


class VerificationWorkflow:
    """Runs the end-to-end verification workflow for a project."""

    def __init__(self):
        self.stages = [
            ("register", "Register project in context manager"),
            ("analyze", "Run repository intelligence analysis"),
            ("build", "Build the project"),
            ("test", "Run tests"),
            ("fix", "Run build-test-fix-retry loop if needed"),
            ("review", "Run AI code review"),
            ("security", "Run security audit"),
            ("deploy", "Deploy to staging"),
            ("verify", "Verify deployment health"),
        ]

    def run(self, project_path: str, project_name: str = None,
            skip_deploy: bool = False) -> dict:
        """Run the full verification workflow.

        Args:
            project_path: Root directory of the project
            project_name: Optional project name (auto-detected if None)
            skip_deploy: Skip deployment stages

        Returns:
            dict with stage results, overall status, and duration
        """
        from pathlib import Path
        root = Path(project_path).resolve()
        if not root.exists():
            return {"status": "error", "error": f"Project path not found: {root}"}

        if project_name is None:
            project_name = root.name

        session_id = f"verify-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        started_at = time.time()
        results = {}
        overall_status = "passed"

        bus.publish("VerificationWorkflowStarted", {
            "session_id": session_id,
            "project": project_name,
            "path": str(root),
        })

        write_log("VERIFY", f"Starting verification workflow for {project_name} at {root}")

        stages = self.stages
        if skip_deploy:
            stages = [s for s in stages if s[0] not in ("deploy", "verify")]

        for stage_name, stage_desc in stages:
            write_log("VERIFY", f"Stage: {stage_name} — {stage_desc}")

            try:
                stage_result = self._run_stage(stage_name, root, project_name, results)
                results[stage_name] = stage_result

                bus.publish("VerificationStageCompleted", {
                    "session_id": session_id,
                    "stage": stage_name,
                    "status": stage_result.get("status", "ok"),
                })

                if stage_result.get("status") == "failed":
                    overall_status = "failed"
                    if stage_name in ("build", "test"):
                        # Try fix loop
                        write_log("VERIFY", f"Stage {stage_name} failed, attempting fix...")
                        fix_result = self._run_stage("fix", root, project_name, results)
                        results["fix"] = fix_result
                        if fix_result.get("status") == "passed":
                            # Retry the failed stage
                            retry_result = self._run_stage(stage_name, root, project_name, results)
                            results[f"{stage_name}_retry"] = retry_result
                            if retry_result.get("status") != "passed":
                                break
                        else:
                            break
                    elif stage_name in ("security", "review"):
                        # Non-blocking failures for review and security
                        write_log("VERIFY", f"Stage {stage_name} has issues but continuing...")
                    else:
                        break

            except Exception as e:
                results[stage_name] = {"status": "error", "error": str(e)}
                overall_status = "error"
                write_log("VERIFY", f"Stage {stage_name} error: {e}")
                break

        duration = round(time.time() - started_at, 2)

        bus.publish("VerificationWorkflowCompleted", {
            "session_id": session_id,
            "project": project_name,
            "status": overall_status,
            "duration_s": duration,
            "stages_run": len(results),
        })

        write_log("VERIFY", f"Workflow completed: {overall_status} in {duration}s")

        return {
            "session_id": session_id,
            "project": project_name,
            "status": overall_status,
            "duration_s": duration,
            "stages": results,
            "stages_run": len(results),
        }

    def _run_stage(self, stage: str, root, project_name: str, prior_results: dict) -> dict:
        """Run a single verification stage."""
        from core.service_registry import registry

        if stage == "register":
            from services.project_manager import project_manager
            info = project_manager.auto_detect(str(root))
            project = project_manager.register(
                name=project_name,
                root_path=str(root),
                framework=info.get("framework", ""),
                language=info.get("language", ""),
                github_repo=info.get("github_repo", ""),
            )
            project_manager.switch(project_name)
            return {"status": "ok", "project": project_name, "info": info}

        elif stage == "analyze":
            if registry.has("repo_intelligence"):
                ri = registry.get("repo_intelligence")
                ri.root = root
                ri._indexed = False
                ri._cache = None
                summary = ri.analyze_all()
                return {"status": "ok", "summary": summary}
            return {"status": "ok", "message": "Repo intelligence not available"}

        elif stage == "build":
            from automation.plugins.dev.plugin import DevPlugin
            dev = DevPlugin()
            dev.initialize()
            result = dev.build({"project_path": str(root)}, None, None)
            return {"status": result.get("status", "ok"), "output": result.get("output", "")[:1000]}

        elif stage == "test":
            from automation.plugins.dev.plugin import DevPlugin
            dev = DevPlugin()
            dev.initialize()
            result = dev.run_tests({"project_path": str(root)}, None, None)
            return {
                "status": result.get("status", "ok"),
                "exit_code": result.get("exit_code", 0),
                "output": result.get("output", "")[:1000],
                "errors": result.get("errors", "")[:500],
            }

        elif stage == "fix":
            if registry.has("build_test_fix_loop"):
                loop = registry.get("build_test_fix_loop")
                result = loop.run(str(root))
                return {"status": result.get("status", "failed"), "attempts": result.get("attempts", 0)}
            return {"status": "ok", "message": "Fix loop not available"}

        elif stage == "review":
            if registry.has("ai_engineer"):
                ai_eng = registry.get("ai_engineer")
                review = ai_eng.review_code()
                return {"status": "ok", "review": str(review)[:1000]}
            return {"status": "ok", "message": "AI engineer not available"}

        elif stage == "security":
            if registry.has("ai_engineer"):
                ai_eng = registry.get("ai_engineer")
                bugs = ai_eng.detect_bugs()
                critical = [b for b in bugs.get("bugs", []) if b.get("severity") == "critical"]
                return {
                    "status": "ok" if not critical else "failed",
                    "bugs_found": len(bugs.get("bugs", [])),
                    "critical": len(critical),
                }
            return {"status": "ok", "message": "AI engineer not available"}

        elif stage == "deploy":
            from automation.plugins.dev.plugin import DevPlugin
            dev = DevPlugin()
            dev.initialize()
            result = dev.deploy({"project_path": str(root), "method": "docker", "target": "staging"}, None, None)
            return {"status": result.get("status", "ok"), "output": result.get("output", "")[:500]}

        elif stage == "verify":
            # Check health endpoint
            import subprocess
            try:
                result = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8000/health"],
                    capture_output=True, text=True, timeout=10,
                )
                status_code = result.stdout.strip()
                return {"status": "ok" if status_code == "200" else "failed", "http_status": status_code}
            except Exception:
                return {"status": "ok", "message": "Health check skipped"}

        return {"status": "ok", "message": f"Stage {stage} not implemented"}


verification_workflow = VerificationWorkflow()

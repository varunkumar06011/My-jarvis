import re
import json
from pathlib import Path
from typing import Optional
from collections import defaultdict

from core.event_bus import bus
from core.event_store import event_store
from core.telemetry import telemetry, TelemetryLevel


class RootCauseAnalyzer:
    """Traces failures across logs, stack traces, dependencies, APIs,
    database, and configuration to identify root causes."""

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def analyze(self, error: str = None, stack_trace: str = None,
                file_path: str = None, repo: str = None) -> dict:
        """Analyze an error to find root cause."""
        findings = []
        evidence = []

        if stack_trace:
            trace_findings = self._analyze_stack_trace(stack_trace)
            findings.extend(trace_findings["findings"])
            evidence.extend(trace_findings["evidence"])

        if error:
            error_findings = self._analyze_error_message(error)
            findings.extend(error_findings["findings"])
            evidence.extend(error_findings["evidence"])

        if file_path:
            file_findings = self._analyze_file(file_path)
            findings.extend(file_findings["findings"])
            evidence.extend(file_findings["evidence"])

        log_findings = self._analyze_logs(error or "")
        findings.extend(log_findings["findings"])
        evidence.extend(log_findings["evidence"])

        event_findings = self._analyze_event_store(error or "")
        findings.extend(event_findings["findings"])
        evidence.extend(event_findings["evidence"])

        config_findings = self._analyze_config(error or "")
        findings.extend(config_findings["findings"])
        evidence.extend(config_findings["evidence"])

        dep_findings = self._analyze_dependencies(error or "", file_path)
        findings.extend(dep_findings["findings"])
        evidence.extend(dep_findings["evidence"])

        db_findings = self._analyze_database(error or "")
        findings.extend(db_findings["findings"])
        evidence.extend(db_findings["evidence"])

        api_findings = self._analyze_api(error or "")
        findings.extend(api_findings["findings"])
        evidence.extend(api_findings["evidence"])

        root_causes = self._deduce_root_cause(findings)

        result = {
            "error": error,
            "findings": findings,
            "evidence": evidence,
            "root_causes": root_causes,
            "confidence": self._calculate_confidence(findings),
        }

        bus.publish("RootCauseAnalyzed", {
            "error": error or "unknown",
            "findings_count": len(findings),
            "root_causes": len(root_causes),
        })

        return result

    def _analyze_stack_trace(self, trace: str) -> dict:
        findings = []
        evidence = []

        file_pattern = r'File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+(\w+)'
        for match in re.finditer(file_pattern, trace):
            file_path, line_num, func_name = match.groups()
            findings.append({
                "category": "stack_trace",
                "severity": "high",
                "message": f"Error originated in {func_name}() at {file_path}:{line_num}",
                "file": file_path,
                "line": int(line_num),
                "function": func_name,
            })
            evidence.append({"type": "stack_trace_entry", "value": match.group(0)})

        exception_pattern = r'^(\w+(?:Error|Exception|Warning)):\s*(.+)$'
        for match in re.finditer(exception_pattern, trace, re.MULTILINE):
            exc_type, message = match.groups()
            findings.append({
                "category": "exception",
                "severity": "critical",
                "message": f"{exc_type}: {message}",
                "exception_type": exc_type,
            })
            evidence.append({"type": "exception", "value": match.group(0)})

        if "ImportError" in trace or "ModuleNotFoundError" in trace:
            module_match = re.search(r"No module named '(\w+)'", trace)
            module_name = module_match.group(1) if module_match else "unknown"
            findings.append({
                "category": "dependency",
                "severity": "high",
                "message": f"Missing dependency: {module_name}",
                "module": module_name,
            })

        if "ConnectionError" in trace or "ConnectionRefusedError" in trace:
            findings.append({
                "category": "network",
                "severity": "high",
                "message": "Network connection error — service may be down or unreachable",
            })

        if "PermissionError" in trace:
            findings.append({
                "category": "permission",
                "severity": "high",
                "message": "Permission denied — check file/directory permissions",
            })

        if "KeyError" in trace:
            key_match = re.search(r"KeyError:\s*['\"]?(\w+)['\"]?", trace)
            key = key_match.group(1) if key_match else "unknown"
            findings.append({
                "category": "data",
                "severity": "medium",
                "message": f"KeyError: '{key}' — expected key missing from dictionary",
                "key": key,
            })

        if "TypeError" in trace and "NoneType" in trace:
            findings.append({
                "category": "null_handling",
                "severity": "high",
                "message": "TypeError with NoneType — null reference, value is None when expected to have a value",
            })

        return {"findings": findings, "evidence": evidence}

    def _analyze_error_message(self, error: str) -> dict:
        findings = []
        evidence = []

        error_lower = error.lower()

        if "timeout" in error_lower:
            findings.append({
                "category": "timeout",
                "severity": "high",
                "message": "Timeout occurred — operation took too long, possibly due to slow service or deadlock",
            })

        if "out of memory" in error_lower or "oom" in error_lower:
            findings.append({
                "category": "resource",
                "severity": "critical",
                "message": "Out of memory — process exceeded available memory",
            })

        if "deadlock" in error_lower:
            findings.append({
                "category": "concurrency",
                "severity": "critical",
                "message": "Deadlock detected — circular resource dependency",
            })

        if "rate limit" in error_lower or "429" in error:
            findings.append({
                "category": "api",
                "severity": "medium",
                "message": "Rate limit exceeded — too many API calls",
            })

        if "auth" in error_lower or "unauthorized" in error_lower or "401" in error:
            findings.append({
                "category": "authentication",
                "severity": "high",
                "message": "Authentication failure — invalid or expired credentials",
            })

        if "not found" in error_lower or "404" in error:
            findings.append({
                "category": "resource_not_found",
                "severity": "medium",
                "message": "Resource not found — endpoint, file, or entity may not exist",
            })

        if "duplicate" in error_lower or "already exists" in error_lower:
            findings.append({
                "category": "data_integrity",
                "severity": "medium",
                "message": "Duplicate entry — unique constraint violation",
            })

        evidence.append({"type": "error_message", "value": error[:500]})

        return {"findings": findings, "evidence": evidence}

    def _analyze_file(self, file_path: str) -> dict:
        findings = []
        evidence = []

        full_path = self.root / file_path
        if not full_path.exists():
            findings.append({
                "category": "missing_file",
                "severity": "high",
                "message": f"File not found: {file_path}",
                "file": file_path,
            })
            return {"findings": findings, "evidence": evidence}

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            findings.append({
                "category": "file_access",
                "severity": "high",
                "message": f"Cannot read file: {e}",
                "file": file_path,
            })
            return {"findings": findings, "evidence": evidence}

        if "TODO" in content or "FIXME" in content:
            evidence.append({"type": "incomplete_code", "file": file_path, "value": "Contains TODO/FIXME"})

        if "pass" in content:
            empty_catch = re.search(r'except.*:\s*pass', content)
            if empty_catch:
                findings.append({
                    "category": "error_handling",
                    "severity": "medium",
                    "message": f"Empty exception handler in {file_path} — errors silently swallowed",
                    "file": file_path,
                })

        return {"findings": findings, "evidence": evidence}

    def _analyze_logs(self, error: str) -> dict:
        findings = []
        evidence = []

        log_dir = self.root / "logs"
        if not log_dir.is_dir():
            return {"findings": findings, "evidence": evidence}

        error_keywords = error.lower().split() if error else []
        error_keywords = [kw for kw in error_keywords if len(kw) > 3]

        for log_file in log_dir.glob("*.log"):
            try:
                content = log_file.read_text(encoding="utf-8", errors="replace")
                lines = content.strip().split("\n")

                for line in lines[-100:]:
                    line_lower = line.lower()
                    if any(kw in line_lower for kw in error_keywords) or "error" in line_lower or "exception" in line_lower:
                        evidence.append({"type": "log_entry", "file": log_file.name, "value": line[:300]})
                        if len(evidence) > 20:
                            break
            except Exception:
                pass

        if evidence:
            findings.append({
                "category": "log_analysis",
                "severity": "medium",
                "message": f"Found {len(evidence)} related log entries",
            })

        return {"findings": findings, "evidence": evidence}

    def _analyze_event_store(self, error: str) -> dict:
        findings = []
        evidence = []

        try:
            failed_events = event_store.search(status="failed", limit=20)
            for evt in failed_events:
                metadata = evt.get("metadata", {})
                if error and error.lower() in str(metadata).lower():
                    evidence.append({"type": "event_store", "event": evt.get("event"), "metadata": metadata})

            if failed_events:
                findings.append({
                    "category": "event_history",
                    "severity": "low",
                    "message": f"Found {len(failed_events)} failed events in event store",
                })
        except Exception:
            pass

        return {"findings": findings, "evidence": evidence}

    def _analyze_config(self, error: str) -> dict:
        findings = []
        evidence = []

        env_file = self.root / ".env"
        if env_file.exists():
            try:
                content = env_file.read_text(encoding="utf-8", errors="replace")
                for line in content.splitlines():
                    if "=" in line and not line.startswith("#"):
                        key = line.split("=")[0].strip()
                        value = line.split("=", 1)[1].strip()
                        if not value or value == '""' or value == "''":
                            findings.append({
                                "category": "configuration",
                                "severity": "medium",
                                "message": f"Empty configuration value: {key}",
                            })
                            evidence.append({"type": "config", "key": key, "issue": "empty"})
                        if "password" in key.lower() and value and not value.startswith("$"):
                            findings.append({
                                "category": "configuration",
                                "severity": "high",
                                "message": f"Hardcoded password in .env: {key}",
                            })
            except Exception:
                pass

        return {"findings": findings, "evidence": evidence}

    def _analyze_dependencies(self, error: str, file_path: str = None) -> dict:
        findings = []
        evidence = []

        req_file = self.root / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text(encoding="utf-8", errors="replace")
                deps = [line.strip().split("==")[0].split(">=")[0].split("<=")[0].strip()
                        for line in content.splitlines() if line.strip() and not line.startswith("#")]
                evidence.append({"type": "dependencies", "value": deps})

                if "ImportError" in error or "ModuleNotFoundError" in error:
                    for dep in deps:
                        if dep.lower() in error.lower():
                            findings.append({
                                "category": "dependency",
                                "severity": "medium",
                                "message": f"Module '{dep}' is in requirements.txt but may not be installed",
                            })
            except Exception:
                pass

        pkg_file = self.root / "package.json"
        if pkg_file.exists():
            try:
                data = json.loads(pkg_file.read_text(encoding="utf-8"))
                deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
                evidence.append({"type": "npm_dependencies", "value": deps})
            except Exception:
                pass

        return {"findings": findings, "evidence": evidence}

    def _analyze_database(self, error: str) -> dict:
        findings = []
        evidence = []

        error_lower = error.lower() if error else ""

        if "sql" in error_lower or "database" in error_lower or "db" in error_lower:
            if "connection" in error_lower:
                findings.append({
                    "category": "database",
                    "severity": "high",
                    "message": "Database connection error — check connection string, credentials, and server status",
                })

            if "constraint" in error_lower or "duplicate" in error_lower:
                findings.append({
                    "category": "database",
                    "severity": "medium",
                    "message": "Database constraint violation — data integrity issue",
                })

            if "migration" in error_lower:
                findings.append({
                    "category": "database",
                    "severity": "medium",
                    "message": "Database migration issue — schema may be out of sync",
                })

        sql_files = list(self.root.rglob("*.sql"))
        if sql_files:
            evidence.append({"type": "sql_files", "count": len(sql_files)})

        return {"findings": findings, "evidence": evidence}

    def _analyze_api(self, error: str) -> dict:
        findings = []
        evidence = []

        error_lower = error.lower() if error else ""

        if "500" in error or "internal server error" in error_lower:
            findings.append({
                "category": "api",
                "severity": "high",
                "message": "API returned 500 — server-side error, check server logs",
            })

        if "502" in error or "bad gateway" in error_lower:
            findings.append({
                "category": "api",
                "severity": "high",
                "message": "API returned 502 — upstream service unavailable",
            })

        if "503" in error or "service unavailable" in error_lower:
            findings.append({
                "category": "api",
                "severity": "high",
                "message": "API returned 503 — service temporarily unavailable",
            })

        if "cors" in error_lower:
            findings.append({
                "category": "api",
                "severity": "medium",
                "message": "CORS error — check allowed origins configuration",
            })

        return {"findings": findings, "evidence": evidence}

    def _deduce_root_cause(self, findings: list) -> list:
        if not findings:
            return [{"cause": "Unknown", "confidence": "low", "message": "No clear root cause identified"}]

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_findings = sorted(findings, key=lambda x: severity_order.get(x.get("severity", "low"), 4))

        causes = []
        seen_categories = set()

        for finding in sorted_findings:
            cat = finding.get("category", "unknown")
            if cat not in seen_categories:
                causes.append({
                    "cause": cat,
                    "confidence": "high" if finding.get("severity") in ("critical", "high") else "medium",
                    "message": finding.get("message", ""),
                    "evidence": [f for f in sorted_findings if f.get("category") == cat],
                })
                seen_categories.add(cat)

        return causes[:5]

    def _calculate_confidence(self, findings: list) -> str:
        critical = sum(1 for f in findings if f.get("severity") == "critical")
        high = sum(1 for f in findings if f.get("severity") == "high")

        if critical > 0 or high > 2:
            return "high"
        elif high > 0:
            return "medium"
        else:
            return "low"


root_cause_analyzer = RootCauseAnalyzer()

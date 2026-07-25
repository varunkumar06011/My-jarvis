"""Repository Voice Bridge — connects voice commands to repository intelligence,
knowledge engine, and AI engineer for repository-aware voice responses."""

import re
from pathlib import Path
from typing import Optional

from core.event_bus import bus
from logs.logger import write_log


# ── Intent patterns ──────────────────────────────────────────────────────────

_REPO_INTENTS = [
    # (intent_name, [keyword patterns])
    ("switch_project", [r"\bswitch to\b", r"\bopen project\b", r"\bcontinue\b", r"\bopen (softshape|penguin|portfolio|restaurant)\b"]),
    ("list_projects",  [r"\blist project", r"\bshow project", r"\bwhat project", r"\bwhich project"]),
    ("register_project", [r"\bregister project\b", r"\badd project\b"]),
    ("create_repo",     [r"\bcreate (github )?repo", r"\bcreate repository\b", r"\bnew (github )?repo"]),
    ("push_project",    [r"\bpush project\b", r"\bpush to github\b", r"\bpush code\b"]),
    ("create_branch",   [r"\bcreate branch\b", r"\bnew branch\b"]),
    ("create_pr",       [r"\bcreate (pr|pull request)\b", r"\bopen (pr|pull request)\b"]),
    ("merge_pr",        [r"\bmerge (pr|pull request)\b"]),
    ("create_release",  [r"\bcreate release\b", r"\bnew release\b", r"\bpublish release\b"]),
    ("build_project",   [r"\bbuild (a |an |the )?(website|app|application|api|service|system|panel|dashboard)\b", r"\bcreate (a |an )?(website|app|application|api|service|system|panel|dashboard)\b", r"\bdevelop (a |an )?(website|app|application)\b"]),
    ("build_test",      [r"\bbuild test\b", r"\btest build\b", r"\brun build test\b", r"\bbuild and test\b"]),
    ("run_tests",       [r"\brun test", r"\bexecute test", r"\btest project\b"]),
    ("verify_project",  [r"\bverify project\b", r"\brun verification\b", r"\be2e test\b", r"\bend.to.end\b"]),
    ("where_is",      [r"\bwhere (is|are)\b", r"\bwhere.*(implemented|defined|located)\b"]),
    ("explain",       [r"\bexplain\b", r"\bhow does\b", r"\bhow do\b", r"\bwhat does\b", r"\btell me about\b"]),
    ("architecture",  [r"\barchitect", r"\bstructure\b", r"\blayout\b", r"\bhow.*organized\b", r"\bhow.*structured\b"]),
    ("database",      [r"\bdatabase\b", r"\bschema\b", r"\btable\b", r"\bsql\b", r"\bmigration\b"]),
    ("api",           [r"\bapi\b", r"\bendpoint\b", r"\broute\b", r"\bcontroller\b"]),
    ("service",       [r"\bservice\b", r"\bmanager\b", r"\bprovider\b", r"\bhandler\b"]),
    ("framework",     [r"\bframework\b", r"\btech stack\b", r"\btechnology\b", r"\bwhat.*built with\b"]),
    ("language",      [r"\blanguage\b", r"\bwhat.*written in\b", r"\bwhat.*coded in\b"]),
    ("find_bug",      [r"\bfind bug", r"\bdetect bug", r"\bbug", r"\bissue", r"\bproblem", r"\berror.*in.*code\b"]),
    ("security",      [r"\bsecurity\b", r"\bvulnerab", r"\bauth\b", r"\blogin\b", r"\bjwt\b", r"\bpassword\b"]),
    ("performance",   [r"\bperformance\b", r"\bslow\b", r"\bbottleneck\b", r"\boptimi[sz]", r"\blatency\b"]),
    ("test",          [r"\btest\b", r"\bunit test", r"\bcoverage\b"]),
    ("deps",          [r"\bdepend", r"\bimport", r"\buses.*library\b", r"\bpackage\b"]),
]

_NON_REPO_PATTERNS = [
    r"^\d",                       # starts with a number (calculator)
    r"\b(what time|what day|today|weather)\b",
    r"\b(battery|power|volume|screenshot|clipboard)\b",
    r"\b(open|close|launch|start|stop).+(notepad|calculator|browser|chrome|firefox)\b",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify_intent(text: str) -> Optional[str]:
    """Classify whether a voice command is a repository query.
    Returns the intent name or None if not a repo query."""
    lower = text.lower().strip()

    if not lower or len(lower) < 3:
        return None

    if _matches_any(lower, _NON_REPO_PATTERNS):
        return None

    for intent_name, patterns in _REPO_INTENTS:
        if _matches_any(lower, patterns):
            return intent_name

    return None


# ── Response Formatter ───────────────────────────────────────────────────────

def _format_locations(locations: list, max_items: int = 5) -> str:
    lines = []
    for loc in locations[:max_items]:
        symbol = loc.get("symbol", loc.get("module", loc.get("file", "unknown")))
        file = loc.get("file", "")
        line = loc.get("line", "")
        loc_str = f"{file}" + (f":{line}" if line else "")
        lines.append(f"{symbol} in {loc_str}")
    if len(locations) > max_items:
        lines.append(f"... and {len(locations) - max_items} more")
    return ". ".join(lines) if lines else "No locations found"


def _format_endpoints(endpoints: list, max_items: int = 5) -> str:
    lines = []
    for ep in endpoints[:max_items]:
        method = ep.get("method", ep.get("decorator", "")).upper()
        path = ep.get("path", ep.get("route", ""))
        func = ep.get("function", "")
        if method and path:
            lines.append(f"{method} {path} ({func})")
        elif func:
            lines.append(f"{func}")
    if len(endpoints) > max_items:
        lines.append(f"... and {len(endpoints) - max_items} more")
    return ". ".join(lines) if lines else "No endpoints found"


def _format_services(services: list, max_items: int = 5) -> str:
    lines = []
    for svc in services[:max_items]:
        name = svc.get("symbol", svc.get("module", "unknown"))
        file = svc.get("file", "")
        lines.append(f"{name} in {file}")
    if len(services) > max_items:
        lines.append(f"... and {len(services) - max_items} more")
    return ". ".join(lines) if lines else "No services found"


def _format_structure(data: dict) -> str:
    parts = []
    discovery = data.get("discovery", {})
    if discovery.get("vcs"):
        parts.append(f"Version control: {discovery['vcs']}")
    if discovery.get("is_monorepo"):
        parts.append("This is a monorepo")

    lang = data.get("primary_language", "unknown")
    parts.append(f"Primary language: {lang}")

    fw = data.get("primary_framework")
    if fw:
        parts.append(f"Primary framework: {fw}")

    summary = data.get("summary", {})
    if summary:
        parts.append(f"{summary.get('total_modules', 0)} modules, {summary.get('total_symbols', 0)} symbols, {summary.get('api_endpoints', 0)} API endpoints")

    ks = data.get("knowledge_summary", {})
    if ks:
        controllers = ks.get("controllers", 0)
        services = ks.get("services", 0)
        if controllers:
            parts.append(f"{controllers} controllers")
        if services:
            parts.append(f"{services} services")

    return ". ".join(parts) if parts else "No structure information available"


def _format_bugs(bug_data: dict) -> str:
    summary = bug_data.get("summary", {})
    total = summary.get("total_issues", 0)
    by_type = summary.get("by_type", {})

    if total == 0:
        return "No bugs detected. The codebase looks clean."

    parts = [f"Found {total} potential issues"]
    for bug_type, count in by_type.items():
        if count > 0:
            label = bug_type.replace("_", " ")
            parts.append(f"{count} {label}")

    return ". ".join(parts)


def _format_review(review_data: dict) -> str:
    if "summary" in review_data:
        summary = review_data["summary"]
        total = summary.get("total_issues", 0)
        files = summary.get("files_reviewed", 0)
        avg_score = summary.get("avg_quality_score", 0)
        return f"Reviewed {files} files. Found {total} issues. Average quality score: {avg_score}/100"

    if "issues" in review_data:
        issues = review_data["issues"]
        if not issues:
            return "No issues found in this file"
        parts = [f"Found {len(issues)} issues"]
        for issue in issues[:5]:
            severity = issue.get("severity", "info")
            category = issue.get("category", "general")
            message = issue.get("message", "")
            line = issue.get("line", "?")
            parts.append(f"{severity} at line {line}: {category} - {message}")
        return ". ".join(parts)

    return "Review completed"


def _format_security(findings: list) -> str:
    if not findings:
        return "No security issues found"
    parts = [f"Found {len(findings)} security findings"]
    for f in findings[:5]:
        severity = f.get("severity", "info")
        category = f.get("category", "general")
        message = f.get("message", "")
        parts.append(f"{severity}: {category} - {message}")
    return ". ".join(parts)


def _format_search_results(results: list, query: str) -> str:
    if not results:
        return f"No results found for '{query}'"
    parts = [f"Found {len(results)} matches for '{query}'"]
    for r in results[:5]:
        symbol = r.get("symbol", r.get("module", r.get("file", "unknown")))
        file = r.get("file", "")
        line = r.get("line", "")
        loc_str = f"{file}" + (f":{line}" if line else "")
        parts.append(f"{symbol} in {loc_str}")
    if len(results) > 5:
        parts.append(f"... and {len(results) - 5} more")
    return ". ".join(parts)


def format_response(intent: str, data: dict, original_query: str) -> str:
    """Format structured query results into a natural language voice response."""
    if "error" in data:
        return f"Sorry, I encountered an error: {data['error']}"

    if intent == "where_is":
        locations = data.get("locations", data.get("matches", []))
        answer = data.get("answer", "")
        detail = _format_locations(locations)
        return f"{answer}. {detail}" if detail and detail != "No locations found" else answer

    elif intent == "explain":
        if "locations" in data:
            locations = data["locations"]
            answer = data.get("answer", "")
            detail = _format_locations(locations)
            return f"{answer}. {detail}"
        elif "matches" in data:
            return _format_search_results(data["matches"], original_query)
        elif "summary" in data:
            return _format_structure(data)
        return data.get("answer", "I couldn't find specific information about that")

    elif intent == "architecture":
        return _format_structure(data)

    elif intent == "database":
        if "matches" in data:
            return _format_search_results(data["matches"], original_query)
        elif "locations" in data:
            return f"{data.get('answer', '')}. {_format_locations(data['locations'])}"
        return data.get("answer", "No database information found")

    elif intent == "api":
        endpoints = data.get("endpoints", [])
        answer = data.get("answer", "")
        detail = _format_endpoints(endpoints)
        return f"{answer}. {detail}" if detail and detail != "No endpoints found" else answer

    elif intent == "service":
        services = data.get("services", data.get("matches", []))
        answer = data.get("answer", "")
        detail = _format_services(services)
        return f"{answer}. {detail}" if detail and detail != "No services found" else answer

    elif intent == "framework":
        fw = data.get("frameworks", {})
        primary = fw.get("primary_framework", "unknown")
        all_fw = fw.get("frameworks", [])
        fw_list = ", ".join(all_fw[:5]) if all_fw else primary
        return f"Primary framework: {primary}. Detected frameworks: {fw_list}"

    elif intent == "language":
        lang = data.get("languages", {})
        primary = lang.get("primary_language", "unknown")
        all_langs = lang.get("languages", {})
        if isinstance(all_langs, dict):
            lang_list = ", ".join(f"{k} ({v.get('file_count', v) if isinstance(v, dict) else v} files)" for k, v in list(all_langs.items())[:5])
        else:
            lang_list = primary
        return f"Primary language: {primary}. Languages: {lang_list}"

    elif intent == "find_bug":
        return _format_bugs(data)

    elif intent == "security":
        if "findings" in data:
            return _format_security(data["findings"])
        elif "summary" in data:
            return _format_review(data)
        return data.get("answer", "Security scan completed")

    elif intent == "performance":
        if "summary" in data:
            return _format_review(data)
        elif "matches" in data:
            return _format_search_results(data["matches"], original_query)
        return data.get("answer", "Performance analysis completed")

    elif intent == "test":
        if "matches" in data:
            return _format_search_results(data["matches"], original_query)
        return data.get("answer", "Test information retrieved")

    elif intent == "deps":
        if "matches" in data:
            return _format_search_results(data["matches"], original_query)
        return data.get("answer", "Dependency information retrieved")

    return data.get("answer", str(data)[:200])


# ── Bridge function ──────────────────────────────────────────────────────────

def handle_repo_query(text: str) -> Optional[str]:
    """Check if a voice command is a repository query and handle it.
    Returns a natural language response string, or None if not a repo query."""
    intent = classify_intent(text)
    if intent is None:
        return None

    from core.service_registry import registry

    response_parts = []

    # ── Project Management ──

    if intent == "switch_project":
        from services.project_manager import project_manager
        project_name = _extract_project_name(text)
        if project_name:
            project = project_manager.switch(project_name)
            if project:
                response = f"Switched to {project.name}. "
                if project.framework:
                    response += f"Framework: {project.framework}. "
                if project.language:
                    response += f"Language: {project.language}. "
                if project.github_repo:
                    response += f"GitHub: {project.github_repo}. "
                response += f"Path: {project.root_path}"
                return response
            else:
                available = project_manager.list_projects()
                if available:
                    names = ", ".join(p["name"] for p in available)
                    return f"Project '{project_name}' not found. Available projects: {names}"
                else:
                    return f"Project '{project_name}' not found. No projects registered yet."
        else:
            return "Which project would you like to switch to?"

    elif intent == "list_projects":
        from services.project_manager import project_manager
        projects = project_manager.list_projects()
        if not projects:
            return "No projects registered yet. You can register a project by saying 'register project' followed by the path."
        active = project_manager.get_active()
        parts = [f"You have {len(projects)} projects registered"]
        for p in projects[:5]:
            marker = " (active)" if active and p["name"].lower() == active.name.lower() else ""
            parts.append(f"{p['name']}{marker}")
        if len(projects) > 5:
            parts.append(f"and {len(projects) - 5} more")
        return ". ".join(parts)

    elif intent == "register_project":
        from services.project_manager import project_manager
        path = _extract_path(text)
        if path:
            info = project_manager.auto_detect(path)
            project = project_manager.register(
                name=info.get("name", Path(path).name),
                root_path=path,
                framework=info.get("framework", ""),
                language=info.get("language", ""),
                github_repo=info.get("github_repo", ""),
                database=info.get("database", ""),
                architecture=info.get("architecture", ""),
            )
            return f"Registered project {project.name} at {project.root_path}. Language: {project.language or 'unknown'}. Framework: {project.framework or 'unknown'}."
        else:
            return "Please specify the project path. For example: register project at C:/Users/projects/myapp"

    # ── Route to appropriate engine based on intent ──

    if intent == "build_test":
        from services.project_manager import project_manager
        active = project_manager.get_active()
        if not active:
            return "No active project. Switch to a project first."
        try:
            from core.service_registry import registry
            loop = registry.get("build_test_fix_loop")
            result = loop.run(active.root_path)
            if result.get("status") == "passed":
                return f"Build and test passed after {result.get('attempts', 0)} attempt(s)."
            else:
                return f"Build and test failed after {result.get('attempts', 0)} attempt(s). Check logs for details."
        except Exception as e:
            return f"Build-test loop error: {e}"

    elif intent == "run_tests":
        from services.project_manager import project_manager
        active = project_manager.get_active()
        if not active:
            return "No active project. Switch to a project first."
        try:
            from automation.plugins.dev.plugin import DevPlugin
            dev = DevPlugin()
            dev.initialize()
            result = dev.run_tests({"project_path": active.root_path}, None, None)
            if result.get("status") == "ok":
                return "All tests passed."
            else:
                errors = result.get("errors", "")[:500]
                return f"Tests failed. {errors}"
        except Exception as e:
            return f"Test execution error: {e}"

    elif intent == "verify_project":
        from services.project_manager import project_manager
        active = project_manager.get_active()
        if not active:
            return "No active project. Switch to a project first."
        try:
            from core.service_registry import registry
            vw = registry.get("verification_workflow")
            result = vw.run(active.root_path, active.name, skip_deploy=True)
            status = result.get("status", "unknown")
            stages = result.get("stages_run", 0)
            duration = result.get("duration_s", 0)
            return f"Verification {status}. {stages} stages completed in {duration} seconds."
        except Exception as e:
            return f"Verification error: {e}"

    if intent == "build_project":
        from core.service_registry import registry
        if not registry.has("agent_coordinator"):
            return "Agent pipeline is not available. Enable engineering agents flag first."
        coordinator = registry.get("agent_coordinator")
        description = text
        task = {
            "type": "plan",
            "description": description,
            "requirements": description,
        }
        try:
            result = coordinator.run_pipeline(task)
            if result.get("status") == "completed":
                agents_run = len(result.get("results", {}))
                duration = result.get("duration_ms", 0)
                reporter_result = result.get("results", {}).get("Reporter", {})
                summary = reporter_result.get("summary", "Pipeline completed")
                return f"Build pipeline completed. {agents_run} agents ran in {duration}ms. {summary}"
            elif result.get("status") == "failed":
                failed_at = result.get("failed_at", "unknown")
                error = result.get("error", "unknown")
                return f"Pipeline failed at {failed_at} agent. Error: {error}"
        except Exception as e:
            return f"Pipeline error: {e}"
        return None

    if intent == "create_repo":
        from services.project_manager import project_manager
        active = project_manager.get_active()
        project_name = _extract_repo_name(text) or (active.name if active else "")
        if not project_name:
            return "Which project should I create a GitHub repository for?"
        try:
            from core.service_registry import registry
            if registry.has("ai_engineer") and registry.has("repo_intelligence"):
                pass
            from automation.plugins.github.plugin import GitHubPlugin
            gh = GitHubPlugin()
            gh.initialize()
            result = gh.create_repo({"name": project_name, "private": False}, None, None)
            if result.get("status") == "ok":
                return f"Created GitHub repository {result.get('full_name', project_name)}. URL: {result.get('url', 'unknown')}"
            else:
                return f"Failed to create repository: {result.get('error', 'unknown error')}"
        except Exception as e:
            return f"Error creating repository: {e}"

    elif intent == "push_project":
        from services.project_manager import project_manager
        active = project_manager.get_active()
        if not active:
            return "No active project. Switch to a project first by saying 'switch to' followed by the project name."
        try:
            from automation.plugins.git.plugin import GitPlugin
            git_plugin = GitPlugin()
            git_plugin.initialize()
            add_result = git_plugin.add({"repo_path": active.root_path, "files": ["."]}, None, None)
            commit_result = git_plugin.commit({"repo_path": active.root_path, "message": "Update by Jarvis"}, None, None)
            push_result = git_plugin.push({"repo_path": active.root_path, "remote": "origin", "branch": "main"}, None, None)
            parts = []
            if add_result.get("status") == "ok":
                parts.append("Files staged")
            if commit_result.get("status") == "ok":
                parts.append("Committed")
            if push_result.get("status") == "ok":
                parts.append("Pushed to GitHub")
            else:
                parts.append(f"Push failed: {push_result.get('output', 'unknown')}")
            return ". ".join(parts)
        except Exception as e:
            return f"Error pushing: {e}"

    elif intent == "create_branch":
        from services.project_manager import project_manager
        active = project_manager.get_active()
        if not active:
            return "No active project. Switch to a project first."
        branch_name = _extract_branch_name(text)
        if not branch_name:
            return "What should the branch be named?"
        try:
            from automation.plugins.git.plugin import GitPlugin
            git_plugin = GitPlugin()
            git_plugin.initialize()
            result = git_plugin.create_branch({"repo_path": active.root_path, "branch": branch_name}, None, None)
            if result.get("status") == "ok":
                return f"Created branch {branch_name}"
            return f"Failed to create branch: {result.get('output', 'error')}"
        except Exception as e:
            return f"Error creating branch: {e}"

    elif intent == "create_pr":
        from services.project_manager import project_manager
        active = project_manager.get_active()
        if not active:
            return "No active project. Switch to a project first."
        if not active.github_repo:
            return "Active project has no GitHub repository configured."
        try:
            from automation.plugins.github.plugin import GitHubPlugin
            gh = GitHubPlugin()
            gh.initialize()
            title = _extract_pr_title(text) or "Automated PR by Jarvis"
            result = gh.create_pr({"repo": active.github_repo, "title": title, "head": "feature/new", "base": "main"}, None, None)
            if result.get("status") == "ok":
                return f"Created PR #{result.get('number', '?')}: {result.get('url', 'unknown')}"
            return f"Failed to create PR: {result.get('error', 'unknown')}"
        except Exception as e:
            return f"Error creating PR: {e}"

    elif intent == "merge_pr":
        from services.project_manager import project_manager
        active = project_manager.get_active()
        if not active or not active.github_repo:
            return "No active project with a GitHub repository."
        try:
            from automation.plugins.github.plugin import GitHubPlugin
            gh = GitHubPlugin()
            gh.initialize()
            pr_num = _extract_pr_number(text)
            if not pr_num:
                pulls = gh.list_pulls({"repo": active.github_repo, "state": "open"}, None, None)
                if pulls.get("pulls"):
                    pr_num = pulls["pulls"][0].get("number")
                else:
                    return "No open PRs to merge."
            result = gh.merge_pr({"repo": active.github_repo, "pr_number": pr_num}, None, None)
            if result.get("status") == "ok":
                return f"Merged PR #{pr_num}"
            return f"Failed to merge PR: {result.get('error', 'unknown')}"
        except Exception as e:
            return f"Error merging PR: {e}"

    elif intent == "create_release":
        from services.project_manager import project_manager
        active = project_manager.get_active()
        if not active or not active.github_repo:
            return "No active project with a GitHub repository."
        tag = _extract_release_tag(text) or "v1.0.0"
        try:
            from automation.plugins.github.plugin import GitHubPlugin
            gh = GitHubPlugin()
            gh.initialize()
            result = gh.create_release({"repo": active.github_repo, "tag": tag, "name": tag, "body": "Release created by Jarvis"}, None, None)
            if result.get("status") == "ok":
                return f"Created release {tag}. URL: {result.get('url', 'unknown')}"
            return f"Failed to create release: {result.get('error', 'unknown')}"
        except Exception as e:
            return f"Error creating release: {e}"

    if intent == "find_bug":
        if registry.has("ai_engineer"):
            ai_engineer = registry.get("ai_engineer")
            data = ai_engineer.detect_bugs()
            response = format_response(intent, data, text)
            response_parts.append(response)
        else:
            return None

    elif intent == "security":
        if registry.has("ai_engineer"):
            ai_engineer = registry.get("ai_engineer")
            review = ai_engineer.review_code()
            if "summary" in review:
                response_parts.append(format_response(intent, review, text))
            else:
                response_parts.append("Security review completed")
        else:
            return None

    elif intent == "performance":
        if registry.has("ai_engineer"):
            ai_engineer = registry.get("ai_engineer")
            review = ai_engineer.review_code()
            response_parts.append(format_response(intent, review, text))
        else:
            return None

    elif intent in ("framework", "language"):
        if registry.has("repo_intelligence"):
            ri = registry.get("repo_intelligence")
            if intent == "framework":
                data = {"frameworks": ri.get_frameworks()}
            else:
                data = {"languages": ri.get_languages()}
            response_parts.append(format_response(intent, data, text))
        else:
            return None

    elif intent == "architecture":
        if registry.has("repo_intelligence"):
            ri = registry.get("repo_intelligence")
            summary = ri.get_summary()
            response_parts.append(format_response(intent, summary, text))
        else:
            return None

    elif intent in ("where_is", "explain", "api", "service", "database", "test", "deps"):
        # Try repo intelligence query engine first
        if registry.has("repo_intelligence"):
            ri = registry.get("repo_intelligence")
            data = ri.query(text)
            response_parts.append(format_response(intent, data, text))

            # Augment with knowledge engine search for explain intents
            if intent == "explain" and registry.has("knowledge_engine"):
                ke = registry.get("knowledge_engine")
                knowledge_results = ke.search(text, limit=3)
                if knowledge_results:
                    for kr in knowledge_results[:2]:
                        snippet = kr.get("content", kr.get("text", ""))[:150]
                        source = kr.get("file", kr.get("repo", "unknown"))
                        response_parts.append(f"From {source}: {snippet}")
        else:
            return None

    if not response_parts:
        return None

    response = " ".join(response_parts)

    # Keep response concise for voice (max ~500 chars)
    if len(response) > 500:
        response = response[:497] + "..."

    bus.publish("RepoQueryAnswered", {
        "query": text,
        "intent": intent,
        "response": response,
    })

    write_log("REPO_BRIDGE", f"Intent: {intent} | Query: {text} | Response: {response[:100]}...")

    return response


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_project_name(text: str) -> Optional[str]:
    """Extract a project name from a voice command like 'switch to Softshape'."""
    lower = text.lower().strip()
    for prefix in ["switch to ", "open project ", "continue ", "open "]:
        if lower.startswith(prefix):
            name = text[len(prefix):].strip()
            if name:
                return name
    return None


def _extract_path(text: str) -> Optional[str]:
    """Extract a file path from a voice command like 'register project at C:/Users/projects/myapp'."""
    import re
    match = re.search(r'[A-Za-z]:[\\\/][^\s]+', text)
    if match:
        return match.group(0)
    match = re.search(r'at\s+(.+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_repo_name(text: str) -> Optional[str]:
    """Extract repo name from 'create repo myproject' or 'create github repo myproject'."""
    lower = text.lower()
    for prefix in ["create github repo ", "create repository ", "create repo ", "new github repo ", "new repo "]:
        if lower.startswith(prefix):
            return text[len(prefix):].strip()
    match = re.search(r'(?:create|new)\s+(?:github\s+)?repo\s+(?:for\s+|called\s+|named\s+)?(.+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_branch_name(text: str) -> Optional[str]:
    """Extract branch name from 'create branch feature/login'."""
    match = re.search(r'(?:create|new)\s+branch\s+(?:called\s+|named\s+)?(.+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_pr_title(text: str) -> Optional[str]:
    """Extract PR title from 'create PR titled fix login bug'."""
    match = re.search(r'(?:create|open)\s+(?:pr|pull request)\s+(?:titled\s+|called\s+|named\s+)?(.+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_pr_number(text: str) -> Optional[int]:
    """Extract PR number from 'merge PR 42'."""
    match = re.search(r'(?:merge|close)\s+(?:pr|pull request)\s*#?(\d+)', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extract_release_tag(text: str) -> Optional[str]:
    """Extract release tag from 'create release v1.2.3'."""
    match = re.search(r'(?:create|new|publish)\s+release\s+(.+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

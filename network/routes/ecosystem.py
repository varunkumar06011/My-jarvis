from fastapi import APIRouter, Query, Body
from typing import Optional

from flags import flag_manager

router = APIRouter(prefix="/api/v1/ecosystem", tags=["ecosystem"])


def _check_flag(flag_name: str):
    if not flag_manager.is_enabled(flag_name):
        return {"error": f"Feature '{flag_name}' is disabled"}
    return None


# ── Repository Intelligence (Step 30) ──

@router.get("/repo/analyze")
async def analyze_repository(root: str = Query(".")):
    err = _check_flag("repo_intelligence")
    if err:
        return err
    from ai.repo.intelligence import RepositoryIntelligence
    ri = RepositoryIntelligence(root)
    return ri.analyze_all()


@router.get("/repo/summary")
async def repo_summary(root: str = Query(".")):
    err = _check_flag("repo_intelligence")
    if err:
        return err
    from ai.repo.intelligence import RepositoryIntelligence
    ri = RepositoryIntelligence(root)
    return ri.get_summary()


@router.get("/repo/discovery")
async def repo_discovery(root: str = Query(".")):
    err = _check_flag("repo_intelligence")
    if err:
        return err
    from ai.repo.discovery import RepositoryDiscovery
    return RepositoryDiscovery(root).discover()


@router.get("/repo/languages")
async def repo_languages(root: str = Query(".")):
    err = _check_flag("repo_intelligence")
    if err:
        return err
    from ai.repo.languages import LanguageDetector
    return LanguageDetector(root).detect()


@router.get("/repo/frameworks")
async def repo_frameworks(root: str = Query(".")):
    err = _check_flag("repo_intelligence")
    if err:
        return err
    from ai.repo.frameworks import FrameworkDetector
    return FrameworkDetector(root).detect()


@router.get("/repo/analysis")
async def repo_analysis(root: str = Query(".")):
    err = _check_flag("repo_intelligence")
    if err:
        return err
    from ai.repo.static_analysis import StaticAnalyzer
    return StaticAnalyzer(root).analyze()


@router.get("/repo/knowledge")
async def repo_knowledge(root: str = Query(".")):
    err = _check_flag("repo_intelligence")
    if err:
        return err
    from ai.repo.knowledge import RepositoryKnowledge
    return RepositoryKnowledge(root).identify()


@router.post("/repo/query")
async def query_repository(question: str = Body(..., embed=True), root: str = Query(".")):
    err = _check_flag("repo_intelligence")
    if err:
        return err
    from ai.repo.query_engine import RepositoryQueryEngine
    qe = RepositoryQueryEngine(root)
    return qe.query(question)


# ── Knowledge Engine / RAG (Step 31) ──

@router.post("/knowledge/index")
async def index_repository(root: str = Body(..., embed=True), repo_name: str = Body(None, embed=True)):
    err = _check_flag("knowledge_engine")
    if err:
        return err
    from ai.knowledge.engine import knowledge_engine
    return knowledge_engine.index_repository(root, repo_name)


@router.post("/knowledge/search")
async def knowledge_search(query: str = Body(..., embed=True), limit: int = Body(20, embed=True),
                           repo: str = Body(None, embed=True)):
    err = _check_flag("knowledge_engine")
    if err:
        return err
    from ai.knowledge.engine import knowledge_engine
    return knowledge_engine.search(query, limit=limit, repo=repo)


@router.post("/knowledge/semantic-search")
async def semantic_search(query: str = Body(..., embed=True), limit: int = Body(20, embed=True),
                          repo: str = Body(None, embed=True)):
    err = _check_flag("knowledge_engine")
    if err:
        return err
    from ai.knowledge.engine import knowledge_engine
    return knowledge_engine.semantic_search(query, limit=limit, repo=repo)


@router.post("/knowledge/context")
async def build_context(query: str = Body(..., embed=True), repo: str = Body(None, embed=True),
                        max_chunks: int = Body(10, embed=True)):
    err = _check_flag("knowledge_engine")
    if err:
        return err
    from ai.knowledge.engine import knowledge_engine
    return knowledge_engine.build_context(query, repo=repo, max_chunks=max_chunks)


@router.post("/knowledge/incremental-update")
async def incremental_update(repo: str = Body(None, embed=True)):
    err = _check_flag("knowledge_engine")
    if err:
        return err
    from ai.knowledge.engine import knowledge_engine
    return knowledge_engine.update_incremental(repo)


@router.get("/knowledge/detect-changes")
async def detect_changes(repo: str = Query(None)):
    err = _check_flag("knowledge_engine")
    if err:
        return err
    from ai.knowledge.engine import knowledge_engine
    return knowledge_engine.detect_changes(repo)


@router.post("/knowledge/multi-search")
async def multi_repo_search(query: str = Body(..., embed=True), repos: list = Body(None, embed=True),
                            limit: int = Body(20, embed=True)):
    err = _check_flag("knowledge_engine")
    if err:
        return err
    from ai.knowledge.engine import knowledge_engine
    return knowledge_engine.multi_repo_search(query, repos=repos, limit=limit)


@router.post("/knowledge/remember")
async def remember(entry_type: str = Body(..., embed=True), title: str = Body(..., embed=True),
                   content: str = Body(..., embed=True), tags: list = Body(None, embed=True),
                   repo: str = Body(None, embed=True)):
    err = _check_flag("knowledge_engine")
    if err:
        return err
    from ai.knowledge.engine import knowledge_engine
    return knowledge_engine.remember(entry_type, title, content, tags=tags, repo=repo)


@router.get("/knowledge/recall")
async def recall(query: str = Query(""), entry_type: str = Query(None), limit: int = Query(20)):
    err = _check_flag("knowledge_engine")
    if err:
        return err
    from ai.knowledge.engine import knowledge_engine
    return knowledge_engine.recall(query=query or None, entry_type=entry_type, limit=limit)


@router.get("/knowledge/stats")
async def knowledge_stats():
    err = _check_flag("knowledge_engine")
    if err:
        return err
    from ai.knowledge.engine import knowledge_engine
    return knowledge_engine.stats()


# ── AI Software Engineer (Step 32) ──

@router.post("/engineer/review")
async def review_code(filepath: str = Body(None, embed=True), root: str = Query(".")):
    err = _check_flag("ai_engineer")
    if err:
        return err
    from ai.engineer.engineer import AISoftwareEngineer
    eng = AISoftwareEngineer(root)
    return eng.review_code(filepath)


@router.post("/engineer/analyze-failure")
async def analyze_failure(error: str = Body(None, embed=True), stack_trace: str = Body(None, embed=True),
                          file_path: str = Body(None, embed=True), root: str = Query(".")):
    err = _check_flag("ai_engineer")
    if err:
        return err
    from ai.engineer.engineer import AISoftwareEngineer
    eng = AISoftwareEngineer(root)
    return eng.analyze_failure(error=error, stack_trace=stack_trace, file_path=file_path)


@router.post("/engineer/detect-bugs")
async def detect_bugs(root: str = Query(".")):
    err = _check_flag("ai_engineer")
    if err:
        return err
    from ai.engineer.engineer import AISoftwareEngineer
    eng = AISoftwareEngineer(root)
    return eng.detect_bugs()


@router.post("/engineer/generate-tests")
async def generate_tests(filepath: str = Body(..., embed=True), test_type: str = Body("unit", embed=True),
                         root: str = Query(".")):
    err = _check_flag("ai_engineer")
    if err:
        return err
    from ai.engineer.engineer import AISoftwareEngineer
    eng = AISoftwareEngineer(root)
    return eng.generate_tests(filepath, test_type)


@router.post("/engineer/generate-docs")
async def generate_docs(filepath: str = Body(..., embed=True), root: str = Query(".")):
    err = _check_flag("ai_engineer")
    if err:
        return err
    from ai.engineer.engineer import AISoftwareEngineer
    eng = AISoftwareEngineer(root)
    return eng.generate_docs(filepath)


@router.post("/engineer/refactoring-plan")
async def refactoring_plan(filepath: str = Body(..., embed=True), root: str = Query(".")):
    err = _check_flag("ai_engineer")
    if err:
        return err
    from ai.engineer.engineer import AISoftwareEngineer
    eng = AISoftwareEngineer(root)
    return eng.generate_refactoring_plan(filepath)


@router.post("/engineer/migration-plan")
async def migration_plan(from_framework: str = Body(..., embed=True),
                         to_framework: str = Body(..., embed=True)):
    err = _check_flag("ai_engineer")
    if err:
        return err
    from ai.engineer.engineer import AISoftwareEngineer
    eng = AISoftwareEngineer()
    return eng.generate_migration_plan(from_framework, to_framework)


@router.post("/engineer/full-analysis")
async def full_analysis(filepath: str = Body(None, embed=True), root: str = Query(".")):
    err = _check_flag("ai_engineer")
    if err:
        return err
    from ai.engineer.engineer import AISoftwareEngineer
    eng = AISoftwareEngineer(root)
    return eng.full_analysis(filepath)


# ── Engineering Agents (Step 33) ──

@router.get("/agents/list")
async def list_agents():
    err = _check_flag("engineering_agents")
    if err:
        return err
    from ai.agents.coordinator import agent_coordinator
    return agent_coordinator.list_agents()


@router.get("/agents/status")
async def agents_status(agent_name: str = Query(None)):
    err = _check_flag("engineering_agents")
    if err:
        return err
    from ai.agents.coordinator import agent_coordinator
    if agent_name:
        return agent_coordinator.get_agent_status(agent_name)
    return agent_coordinator.get_agent_status()


@router.get("/agents/pipeline-status")
async def pipeline_status():
    err = _check_flag("engineering_agents")
    if err:
        return err
    from ai.agents.coordinator import agent_coordinator
    return agent_coordinator.pipeline_status()


@router.post("/agents/run-pipeline")
async def run_pipeline(task: dict = Body(...)):
    err = _check_flag("engineering_agents")
    if err:
        return err
    from ai.agents.coordinator import agent_coordinator
    return agent_coordinator.run_pipeline(task)


@router.post("/agents/run-single")
async def run_single_agent(agent_name: str = Body(..., embed=True), task: dict = Body(...)):
    err = _check_flag("engineering_agents")
    if err:
        return err
    from ai.agents.coordinator import agent_coordinator
    return agent_coordinator.run_single_agent(agent_name, task)


@router.get("/agents/sessions")
async def list_sessions(limit: int = Query(20)):
    err = _check_flag("engineering_agents")
    if err:
        return err
    from ai.agents.coordinator import agent_coordinator
    return agent_coordinator.list_sessions(limit)


@router.get("/agents/session/{session_id}")
async def get_session(session_id: str):
    err = _check_flag("engineering_agents")
    if err:
        return err
    from ai.agents.coordinator import agent_coordinator
    result = agent_coordinator.get_session(session_id)
    if result is None:
        return {"error": "Session not found"}
    return result


# ── Development Ecosystem (Step 34) ──

@router.get("/dev/status")
async def dev_status(root: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.ecosystem import DevelopmentEcosystem
    return DevelopmentEcosystem(root).ecosystem_status()


@router.get("/dev/git/status")
async def git_status(repo_path: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.ecosystem import dev_ecosystem
    return dev_ecosystem.git_status(repo_path)


@router.get("/dev/git/log")
async def git_log(repo_path: str = Query("."), count: int = Query(20)):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.ecosystem import dev_ecosystem
    return dev_ecosystem.git_log(repo_path, count)


@router.get("/dev/git/branch-health")
async def git_branch_health(repo_path: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.ecosystem import dev_ecosystem
    return dev_ecosystem.branch_health(repo_path)


@router.post("/dev/pr-review")
async def pr_review(platform: str = Body(..., embed=True), repo: str = Body(..., embed=True),
                    pr_number: int = Body(..., embed=True)):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.ecosystem import dev_ecosystem
    return dev_ecosystem.pr_review(platform, repo, pr_number)


@router.post("/dev/commit-analysis")
async def commit_analysis(platform: str = Body(..., embed=True), repo: str = Body(..., embed=True),
                          sha: str = Body(..., embed=True)):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.ecosystem import dev_ecosystem
    return dev_ecosystem.commit_analysis(platform, repo, sha)


@router.get("/dev/release-summary")
async def release_summary(platform: str = Query("github"), repo: str = Query(...), limit: int = Query(5)):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.ecosystem import dev_ecosystem
    return dev_ecosystem.release_summary(platform, repo, limit)


@router.get("/dev/ides")
async def detect_ides(root: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.ide import IDEIntegration
    return IDEIntegration(root).detect_ides()


@router.post("/dev/open-ide")
async def open_ide(ide: str = Body(..., embed=True), file_path: str = Body(None, embed=True),
                   line: int = Body(None, embed=True), root: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.ide import IDEIntegration
    return IDEIntegration(root).open(ide, file_path=file_path, line=line)


@router.get("/dev/docker/status")
async def docker_status():
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.containers import container_integration
    return container_integration.docker_status()


@router.get("/dev/docker/ps")
async def docker_ps(all_containers: bool = Query(False)):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.containers import container_integration
    return container_integration.docker_ps(all_containers)


@router.get("/dev/docker/images")
async def docker_images():
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.containers import container_integration
    return container_integration.docker_images()


@router.post("/dev/docker/build")
async def docker_build(dockerfile: str = Body("Dockerfile", embed=True), tag: str = Body("", embed=True),
                       context: str = Body(".", embed=True)):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.containers import container_integration
    return container_integration.docker_build(dockerfile, tag, context)


@router.get("/dev/docker/analyze-dockerfile")
async def analyze_dockerfile(dockerfile_path: str = Query("Dockerfile")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.containers import container_integration
    return container_integration.analyze_dockerfile(dockerfile_path)


@router.post("/dev/compose/up")
async def compose_up(cwd: str = Body(".", embed=True), detached: bool = Body(True, embed=True),
                     service: str = Body("", embed=True)):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.containers import container_integration
    return container_integration.compose_up(cwd=cwd, detached=detached, service=service)


@router.post("/dev/compose/down")
async def compose_down(cwd: str = Body(".", embed=True), volumes: bool = Body(False, embed=True)):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.containers import container_integration
    return container_integration.compose_down(cwd=cwd, volumes=volumes)


@router.get("/dev/build/systems")
async def detect_build_systems(root: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.build import BuildSystemIntegration
    return BuildSystemIntegration(root).detect_build_systems()


@router.post("/dev/build/run")
async def run_build(system: str = Body(None, embed=True), cwd: str = Body(".", embed=True),
                    root: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.build import BuildSystemIntegration
    return BuildSystemIntegration(root).build(system=system, cwd=cwd)


@router.post("/dev/test/run")
async def run_tests(system: str = Body(None, embed=True), cwd: str = Body(".", embed=True),
                    root: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.build import BuildSystemIntegration
    return BuildSystemIntegration(root).test(system=system, cwd=cwd)


@router.get("/dev/cicd/detect")
async def detect_cicd(root: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.cicd import CICDIntegration
    return CICDIntegration(root).detect_cicd()


@router.get("/dev/cicd/github/workflows")
async def github_workflows(root: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.cicd import CICDIntegration
    return CICDIntegration(root).github_actions_list_workflows()


@router.get("/dev/cicd/gitlab/parse")
async def gitlab_parse(root: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.cicd import CICDIntegration
    return CICDIntegration(root).gitlab_ci_parse()


@router.get("/dev/cicd/jenkins/parse")
async def jenkins_parse(root: str = Query(".")):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.cicd import CICDIntegration
    return CICDIntegration(root).jenkins_parse_jenkinsfile()


@router.post("/dev/cicd/build-failures")
async def build_failures(platform: str = Body(..., embed=True), repo: str = Body(..., embed=True),
                         run_id: int = Body(None, embed=True)):
    err = _check_flag("dev_ecosystem")
    if err:
        return err
    from ai.ecosystem.cicd import CICDIntegration
    return CICDIntegration().build_failures(platform, repo, run_id)

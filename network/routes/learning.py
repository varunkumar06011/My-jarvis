from fastapi import APIRouter, Query
from pydantic import BaseModel

from ai.learning.patterns import pattern_library
from ai.learning.decisions import decision_history
from ai.learning.preferences import user_preferences

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


class PatternCreate(BaseModel):
    name: str
    category: str
    pattern: str
    solution: str
    language: str = ""
    tags: list[str] = []


class DecisionCreate(BaseModel):
    title: str
    context: str
    decision: str
    rationale: str
    alternatives: list[str] = []
    consequences: str = ""
    tags: list[str] = []


class PreferenceSet(BaseModel):
    key: str
    value: any


@router.get("/patterns")
async def search_patterns(query: str = "", category: str = "", language: str = "", limit: int = 20):
    return {"patterns": pattern_library.search(query, category, language, limit)}


@router.post("/patterns")
async def create_pattern(req: PatternCreate):
    p = pattern_library.add(req.name, req.category, req.pattern, req.solution, req.language, req.tags)
    return p.to_dict()


@router.post("/patterns/{pattern_id}/use")
async def record_pattern_use(pattern_id: str, success: bool = True):
    pattern_library.record_use(pattern_id, success)
    return {"status": "ok"}


@router.get("/patterns/stats")
async def pattern_stats():
    return pattern_library.stats()


@router.get("/decisions")
async def search_decisions(query: str = "", tag: str = "", status: str = "", limit: int = 20):
    return {"decisions": decision_history.search(query, tag, status, limit)}


@router.post("/decisions")
async def create_decision(req: DecisionCreate):
    d = decision_history.record(req.title, req.context, req.decision, req.rationale,
                                req.alternatives, req.consequences, req.tags)
    return d.to_dict()


@router.get("/decisions/stats")
async def decision_stats():
    return decision_history.stats()


@router.get("/preferences")
async def get_preferences():
    return {
        "prefs": user_preferences._prefs,
        "coding_style": user_preferences.get_coding_style(),
        "naming_conventions": user_preferences.get_naming_conventions(),
        "frequent_workflows": user_preferences.get_frequent_workflows(),
        "stats": user_preferences.stats(),
    }


@router.post("/preferences")
async def set_preference(req: PreferenceSet):
    user_preferences.set(req.key, req.value)
    return {"status": "ok"}


@router.get("/preferences/fixes")
async def search_fixes(query: str = "", limit: int = 10):
    return {"fixes": user_preferences.search_fixes(query, limit)}

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ai.cto.dashboard import executive_dashboard
from ai.cto.reports import report_generator, milestone_tracker
from ai.cto.architecture import architecture_analyzer

router = APIRouter(prefix="/api/v1/cto", tags=["cto"])


class MilestoneCreate(BaseModel):
    title: str
    description: str = ""
    category: str = "general"
    target_date: str = ""
    status: str = "planned"


@router.get("/dashboard")
async def get_dashboard():
    return executive_dashboard.snapshot()


@router.get("/reports")
async def list_reports():
    return {"reports": report_generator.list_reports()}


@router.post("/reports/generate")
async def generate_report(report_type: str = Query("daily")):
    if report_type == "daily":
        return report_generator.generate_daily()
    elif report_type == "weekly":
        return report_generator.generate_weekly()
    elif report_type == "monthly":
        return report_generator.generate_monthly()
    return {"error": "Invalid report type. Use: daily, weekly, monthly"}


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    report = report_generator.get_report(report_id)
    if report is None:
        return {"error": "Report not found"}
    return report


@router.get("/architecture")
async def get_architecture():
    return architecture_analyzer.analyze()


@router.get("/milestones")
async def list_milestones(status: str = "", category: str = "", limit: int = 50):
    return {"milestones": milestone_tracker.list(status, category, limit)}


@router.post("/milestones")
async def create_milestone(req: MilestoneCreate):
    return milestone_tracker.add(req.title, req.description, req.category, req.target_date, req.status)


@router.post("/milestones/{milestone_id}/complete")
async def complete_milestone(milestone_id: str):
    return milestone_tracker.complete(milestone_id)

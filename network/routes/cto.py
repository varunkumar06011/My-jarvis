from fastapi import APIRouter, Query

from ai.cto.dashboard import executive_dashboard
from ai.cto.reports import report_generator
from ai.cto.architecture import architecture_analyzer

router = APIRouter(prefix="/api/v1/cto", tags=["cto"])


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

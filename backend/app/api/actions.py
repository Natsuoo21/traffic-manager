from fastapi import APIRouter, Query

from app.main import get_db
from app.services.actions_service import ActionsService

router = APIRouter()


@router.get("/overview")
def overview() -> dict:
    """High-level overview of all campaigns across platforms."""
    return ActionsService(get_db()).get_overview()


@router.post("/pause/{campaign_id}")
def pause_campaign(campaign_id: int) -> dict:
    """Pause a campaign by local DB ID."""
    return ActionsService(get_db()).pause_campaign(campaign_id)


@router.post("/resume/{campaign_id}")
def resume_campaign(campaign_id: int) -> dict:
    """Resume (activate) a campaign by local DB ID."""
    return ActionsService(get_db()).resume_campaign(campaign_id)


@router.post("/budget/{campaign_id}")
def update_budget(campaign_id: int, amount: float = Query(...)) -> dict:
    """Update campaign budget."""
    return ActionsService(get_db()).update_budget(campaign_id, amount)


@router.get("/metrics/{campaign_id}")
def campaign_metrics(campaign_id: int, days: int = Query(7, ge=1, le=90)) -> dict:
    """Get metrics for a specific campaign."""
    return ActionsService(get_db()).get_campaign_metrics(campaign_id, days=days)


@router.get("/summary/{platform}")
def platform_summary(platform: str, days: int = Query(7, ge=1, le=90)) -> dict:
    """Get aggregated metrics for all campaigns of a platform."""
    return ActionsService(get_db()).get_platform_summary(platform, days=days)

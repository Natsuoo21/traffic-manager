from fastapi import APIRouter, HTTPException, Query

from app.connectors import get_active_platforms
from app.main import get_db
from app.services.sync_service import SyncService

router = APIRouter()


@router.post("/")
def trigger_sync_all() -> dict:
    """Trigger a full sync of all configured platforms."""
    db = get_db()
    service = SyncService(db)
    results = service.sync_all()
    return {
        "status": "completed",
        "platforms_synced": [r["platform"] for r in results],
        "results": results,
    }


@router.post("/{platform}")
def trigger_sync_platform(platform: str) -> dict:
    """Trigger sync for a specific platform."""
    active = get_active_platforms()
    if platform not in active:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform}' is not configured. Active: {active}",
        )
    db = get_db()
    service = SyncService(db)
    return service.sync_platform(platform)


@router.get("/log")
def get_sync_log(
    platform: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Get recent sync log entries."""
    db = get_db()
    sql = "SELECT * FROM sync_log"
    params: list = []
    if platform:
        sql += " WHERE platform = ?"
        params.append(platform)
    sql += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(sql, tuple(params))
    return {"sync_logs": [dict(r) for r in rows], "total": len(rows)}

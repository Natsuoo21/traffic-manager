from fastapi import APIRouter, HTTPException, Query

from app.main import get_db

router = APIRouter()


@router.get("/")
def list_campaigns(
    platform: str | None = Query(None),
    status: str | None = Query(None),
) -> dict:
    db = get_db()
    sql = "SELECT * FROM campaigns WHERE 1=1"
    params: list = []

    if platform:
        sql += " AND platform = ?"
        params.append(platform)
    if status:
        sql += " AND status = ?"
        params.append(status.upper())

    sql += " ORDER BY updated_at DESC"
    rows = db.execute(sql, tuple(params))
    campaigns = [dict(r) for r in rows]
    return {"campaigns": campaigns, "total": len(campaigns)}


@router.get("/{campaign_id}")
def get_campaign(campaign_id: int) -> dict:
    db = get_db()
    rows = db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign = dict(rows[0])

    # Include ad sets
    ad_set_rows = db.execute(
        "SELECT * FROM ad_sets WHERE campaign_id = ?", (campaign_id,)
    )
    campaign["ad_sets"] = [dict(r) for r in ad_set_rows]
    return campaign

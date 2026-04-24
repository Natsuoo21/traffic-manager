from fastapi import APIRouter, Query

from app.main import get_db

router = APIRouter()


@router.get("/")
def list_metrics(
    platform: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> dict:
    db = get_db()
    sql = "SELECT * FROM metrics_snapshots WHERE 1=1"
    params: list = []

    if platform:
        sql += " AND platform = ?"
        params.append(platform)
    if entity_type:
        sql += " AND entity_type = ?"
        params.append(entity_type)
    if entity_id is not None:
        sql += " AND entity_id = ?"
        params.append(entity_id)
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date <= ?"
        params.append(date_to)

    sql += " ORDER BY date DESC"
    rows = db.execute(sql, tuple(params))
    metrics = [dict(r) for r in rows]
    return {"metrics": metrics, "total": len(metrics)}

from fastapi import APIRouter

from app.main import get_db

router = APIRouter()


@router.get("/")
def list_accounts() -> dict:
    db = get_db()
    rows = db.execute("SELECT * FROM platform_accounts ORDER BY platform")
    accounts = [dict(r) for r in rows]
    return {"accounts": accounts, "total": len(accounts)}

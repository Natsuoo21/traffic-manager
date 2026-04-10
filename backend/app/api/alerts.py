from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_alerts() -> dict:
    return {"alerts": [], "total": 0}

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_metrics() -> dict:
    return {"metrics": [], "total": 0}

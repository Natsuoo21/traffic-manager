from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_campaigns() -> dict:
    return {"campaigns": [], "total": 0}

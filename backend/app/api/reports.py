from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_reports() -> dict:
    return {"reports": [], "total": 0}

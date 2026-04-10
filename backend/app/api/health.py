from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    platforms = {
        "meta": settings.has_meta(),
        "google_ads": settings.has_google_ads(),
        "linkedin": settings.has_linkedin(),
    }
    return {
        "status": "ok",
        "version": "0.1.0",
        "platforms": platforms,
    }

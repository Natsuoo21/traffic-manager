from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.database import Database

db: Database | None = None


def get_db() -> Database:
    assert db is not None, "Database not initialized"
    return db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global db
    logger.info(f"Starting Traffic Manager ({settings.app_env})")
    db = Database(settings.db_path)

    platforms = []
    if settings.has_meta():
        platforms.append("Meta")
    if settings.has_google_ads():
        platforms.append("Google Ads")
    if settings.has_linkedin():
        platforms.append("LinkedIn")
    logger.info(f"Configured platforms: {platforms or ['none — add credentials to .env']}")

    yield

    logger.info("Shutting down Traffic Manager")


app = FastAPI(
    title="Traffic Manager",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from app.api.accounts import router as accounts_router  # noqa: E402
from app.api.alerts import router as alerts_router  # noqa: E402
from app.api.campaigns import router as campaigns_router  # noqa: E402
from app.api.health import router as health_router  # noqa: E402
from app.api.metrics import router as metrics_router  # noqa: E402
from app.api.reports import router as reports_router  # noqa: E402
from app.api.sync import router as sync_router  # noqa: E402

app.include_router(health_router)
app.include_router(campaigns_router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(metrics_router, prefix="/api/metrics", tags=["metrics"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["alerts"])
app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
app.include_router(accounts_router, prefix="/api/accounts", tags=["accounts"])
app.include_router(sync_router, prefix="/api/sync", tags=["sync"])

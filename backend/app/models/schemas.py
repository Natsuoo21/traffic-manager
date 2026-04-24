from __future__ import annotations

from pydantic import BaseModel

# --- Platform Account ---


class AccountResponse(BaseModel):
    id: int
    platform: str
    account_id: str
    account_name: str | None = None
    is_active: bool = True
    last_synced_at: str | None = None


# --- Campaign ---


class CampaignResponse(BaseModel):
    id: int
    platform: str
    platform_id: str
    account_id: int
    name: str
    objective: str | None = None
    status: str
    budget_type: str | None = None
    budget_amount: float | None = None
    currency: str = "BRL"
    start_date: str | None = None
    end_date: str | None = None
    last_synced_at: str | None = None


class CampaignDetail(CampaignResponse):
    ad_sets: list[AdSetResponse] = []


# --- Ad Set ---


class AdSetResponse(BaseModel):
    id: int
    platform: str
    platform_id: str
    campaign_id: int
    name: str
    status: str
    targeting: str | None = None
    bid_strategy: str | None = None
    budget_amount: float | None = None
    budget_type: str | None = None
    last_synced_at: str | None = None


# --- Ad ---


class AdResponse(BaseModel):
    id: int
    platform: str
    platform_id: str
    ad_set_id: int
    name: str
    status: str
    preview_url: str | None = None
    last_synced_at: str | None = None


# --- Metrics ---


class MetricRow(BaseModel):
    id: int
    platform: str
    entity_type: str
    entity_id: int
    date: str
    impressions: int = 0
    clicks: int = 0
    spend: float = 0.0
    conversions: int = 0
    conversion_value: float = 0.0
    reach: int = 0
    ctr: float = 0.0
    cpc: float = 0.0
    cpm: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0
    currency: str = "BRL"


# --- Sync ---


class SyncLogEntry(BaseModel):
    id: int
    platform: str
    sync_type: str
    status: str
    entities_synced: int = 0
    error_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None


class SyncTriggerResponse(BaseModel):
    status: str
    platforms_synced: list[str]
    results: list[dict] = []

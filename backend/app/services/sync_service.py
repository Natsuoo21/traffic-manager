import json
import sqlite3
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any

from loguru import logger

from app.config import settings
from app.connectors import get_active_platforms, get_connector
from app.connectors.base import AdPlatformConnector
from app.database import Database


class SyncService:
    """Orchestrates data sync from ad platforms into SQLite."""

    def __init__(self, db: Database):
        self.db = db

    # ── Public API ──────���───────────────────────────────────────

    def sync_all(self) -> list[dict[str, Any]]:
        """Sync all configured platforms. Returns list of sync log summaries."""
        results = []
        for platform in get_active_platforms():
            result = self.sync_platform(platform)
            results.append(result)
        return results

    def sync_platform(self, platform: str) -> dict[str, Any]:
        """Full sync for one platform: account -> campaigns -> ad_sets -> ads -> metrics."""
        log_id = self._log_start(platform, "full_sync")
        start_time = time.monotonic()
        total_entities = 0

        try:
            connector = get_connector(platform)
            conn = self.db.connection()
            try:
                account_row_id = self._get_or_create_account(conn, platform)

                # 1. Sync campaigns
                n_campaigns = self._sync_campaigns(conn, connector, platform, account_row_id)
                total_entities += n_campaigns

                # 2. Sync ad sets (for each campaign)
                n_ad_sets = self._sync_ad_sets(conn, connector, platform)
                total_entities += n_ad_sets

                # 3. Sync ads (for each ad set)
                n_ads = self._sync_ads(conn, connector, platform)
                total_entities += n_ads

                # 4. Sync metrics (last 7 days)
                n_metrics = self._sync_metrics(
                    conn,
                    connector,
                    platform,
                    date_from=(date.today() - timedelta(days=7)).isoformat(),
                    date_to=date.today().isoformat(),
                )
                total_entities += n_metrics

                # Update account last_synced_at
                conn.execute(
                    "UPDATE platform_accounts SET last_synced_at = ? WHERE id = ?",
                    (datetime.now(tz=UTC).isoformat(), account_row_id),
                )

                conn.commit()
            finally:
                conn.close()

            duration_ms = int((time.monotonic() - start_time) * 1000)
            self._log_finish(log_id, "SUCCESS", total_entities, duration_ms)
            logger.info(f"[{platform}] Sync completed: {total_entities} entities in {duration_ms}ms")
            return {
                "platform": platform,
                "status": "SUCCESS",
                "entities_synced": total_entities,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(f"Sync failed for {platform}: {e}")
            self._log_finish(log_id, "FAILED", total_entities, duration_ms, str(e))
            return {
                "platform": platform,
                "status": "FAILED",
                "error": str(e),
                "duration_ms": duration_ms,
            }

    # ── Account ──────────���──────────────────────────────────────

    def _get_or_create_account(self, conn: sqlite3.Connection, platform: str) -> int:
        """Ensure platform_accounts row exists, return its local id."""
        account_id_map = {
            "meta": settings.meta_ad_account_id,
            "google": settings.google_ads_customer_id,
            "linkedin": settings.linkedin_ad_account_id,
        }
        ext_account_id = account_id_map[platform]

        row = conn.execute(
            "SELECT id FROM platform_accounts WHERE platform = ? AND account_id = ?",
            (platform, ext_account_id),
        ).fetchone()

        if row:
            return row["id"]

        cursor = conn.execute(
            """INSERT INTO platform_accounts (platform, account_id, account_name, is_active)
               VALUES (?, ?, ?, 1)""",
            (platform, ext_account_id, f"{platform} account"),
        )
        return cursor.lastrowid  # type: ignore[return-value]

    # ── Campaigns ─────────��─────────────────────────────────────

    def _sync_campaigns(
        self,
        conn: sqlite3.Connection,
        connector: AdPlatformConnector,
        platform: str,
        account_row_id: int,
    ) -> int:
        raw_campaigns = connector.get_campaigns()
        now = datetime.now(tz=UTC).isoformat()
        count = 0

        for raw in raw_campaigns:
            norm = self._normalize_campaign(raw, platform)
            conn.execute(
                """INSERT INTO campaigns
                       (platform, platform_id, account_id, name, objective, status,
                        budget_type, budget_amount, currency, start_date, end_date,
                        platform_data, last_synced_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(platform, platform_id) DO UPDATE SET
                       name=excluded.name, objective=excluded.objective,
                       status=excluded.status, budget_type=excluded.budget_type,
                       budget_amount=excluded.budget_amount, currency=excluded.currency,
                       start_date=excluded.start_date, end_date=excluded.end_date,
                       platform_data=excluded.platform_data,
                       last_synced_at=excluded.last_synced_at,
                       updated_at=excluded.updated_at""",
                (
                    platform,
                    norm["platform_id"],
                    account_row_id,
                    norm["name"],
                    norm["objective"],
                    norm["status"],
                    norm["budget_type"],
                    norm["budget_amount"],
                    norm["currency"],
                    norm["start_date"],
                    norm["end_date"],
                    json.dumps(raw),
                    now,
                    now,
                ),
            )
            count += 1

        logger.info(f"[{platform}] Synced {count} campaigns")
        return count

    # ── Ad Sets ─────────────────────────────────────────────────

    def _sync_ad_sets(
        self,
        conn: sqlite3.Connection,
        connector: AdPlatformConnector,
        platform: str,
    ) -> int:
        campaigns = conn.execute(
            "SELECT id, platform_id FROM campaigns WHERE platform = ?",
            (platform,),
        ).fetchall()

        now = datetime.now(tz=UTC).isoformat()
        count = 0

        for campaign_row in campaigns:
            local_campaign_id = campaign_row["id"]
            platform_campaign_id = campaign_row["platform_id"]

            try:
                raw_ad_sets = connector.get_ad_sets(platform_campaign_id)
            except Exception as e:
                logger.warning(f"[{platform}] Failed to get ad sets for campaign {platform_campaign_id}: {e}")
                continue

            for raw in raw_ad_sets:
                norm = self._normalize_ad_set(raw, platform)
                conn.execute(
                    """INSERT INTO ad_sets
                           (platform, platform_id, campaign_id, name, status,
                            targeting, bid_strategy, budget_amount, budget_type,
                            platform_data, last_synced_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(platform, platform_id) DO UPDATE SET
                           campaign_id=excluded.campaign_id, name=excluded.name,
                           status=excluded.status, targeting=excluded.targeting,
                           bid_strategy=excluded.bid_strategy,
                           budget_amount=excluded.budget_amount,
                           budget_type=excluded.budget_type,
                           platform_data=excluded.platform_data,
                           last_synced_at=excluded.last_synced_at,
                           updated_at=excluded.updated_at""",
                    (
                        platform,
                        norm["platform_id"],
                        local_campaign_id,
                        norm["name"],
                        norm["status"],
                        norm["targeting"],
                        norm["bid_strategy"],
                        norm["budget_amount"],
                        norm["budget_type"],
                        json.dumps(raw),
                        now,
                        now,
                    ),
                )
                count += 1

        logger.info(f"[{platform}] Synced {count} ad sets")
        return count

    # ── Ads ─────────────────────────────────────────────────────

    def _sync_ads(
        self,
        conn: sqlite3.Connection,
        connector: AdPlatformConnector,
        platform: str,
    ) -> int:
        ad_sets = conn.execute(
            "SELECT id, platform_id FROM ad_sets WHERE platform = ?",
            (platform,),
        ).fetchall()

        now = datetime.now(tz=UTC).isoformat()
        count = 0

        for ad_set_row in ad_sets:
            local_ad_set_id = ad_set_row["id"]
            platform_ad_set_id = ad_set_row["platform_id"]

            try:
                raw_ads = connector.get_ads(platform_ad_set_id)
            except Exception as e:
                logger.warning(f"[{platform}] Failed to get ads for ad set {platform_ad_set_id}: {e}")
                continue

            for raw in raw_ads:
                norm = self._normalize_ad(raw, platform)
                conn.execute(
                    """INSERT INTO ads
                           (platform, platform_id, ad_set_id, name, status,
                            creative_data, preview_url, platform_data,
                            last_synced_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(platform, platform_id) DO UPDATE SET
                           ad_set_id=excluded.ad_set_id, name=excluded.name,
                           status=excluded.status, creative_data=excluded.creative_data,
                           preview_url=excluded.preview_url,
                           platform_data=excluded.platform_data,
                           last_synced_at=excluded.last_synced_at,
                           updated_at=excluded.updated_at""",
                    (
                        platform,
                        norm["platform_id"],
                        local_ad_set_id,
                        norm["name"],
                        norm["status"],
                        norm["creative_data"],
                        norm["preview_url"],
                        json.dumps(raw),
                        now,
                        now,
                    ),
                )
                count += 1

        logger.info(f"[{platform}] Synced {count} ads")
        return count

    # ── Metrics ─────────────────────────────────────────────────

    def _sync_metrics(
        self,
        conn: sqlite3.Connection,
        connector: AdPlatformConnector,
        platform: str,
        date_from: str,
        date_to: str,
    ) -> int:
        campaigns = conn.execute(
            "SELECT id, platform_id FROM campaigns WHERE platform = ?",
            (platform,),
        ).fetchall()

        count = 0
        for campaign_row in campaigns:
            local_id = campaign_row["id"]
            platform_id = campaign_row["platform_id"]

            try:
                raw_metrics = connector.get_metrics("campaign", platform_id, date_from, date_to)
            except Exception as e:
                logger.warning(f"[{platform}] Failed to get metrics for campaign {platform_id}: {e}")
                continue

            for raw in raw_metrics:
                norm = self._normalize_metric(raw)
                conn.execute(
                    """INSERT INTO metrics_snapshots
                           (platform, entity_type, entity_id, date,
                            impressions, clicks, spend, conversions,
                            conversion_value, reach, ctr, cpc, cpm, cpa, roas,
                            platform_metrics, currency)
                       VALUES (?, 'campaign', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(platform, entity_type, entity_id, date) DO UPDATE SET
                           impressions=excluded.impressions, clicks=excluded.clicks,
                           spend=excluded.spend, conversions=excluded.conversions,
                           conversion_value=excluded.conversion_value,
                           reach=excluded.reach, ctr=excluded.ctr,
                           cpc=excluded.cpc, cpm=excluded.cpm,
                           cpa=excluded.cpa, roas=excluded.roas,
                           platform_metrics=excluded.platform_metrics,
                           synced_at=datetime('now')""",
                    (
                        platform,
                        local_id,
                        norm["date"],
                        norm["impressions"],
                        norm["clicks"],
                        norm["spend"],
                        norm["conversions"],
                        norm["conversion_value"],
                        norm["reach"],
                        norm["ctr"],
                        norm["cpc"],
                        norm["cpm"],
                        norm["cpa"],
                        norm["roas"],
                        json.dumps(raw),
                        norm["currency"],
                    ),
                )
                count += 1

        logger.info(f"[{platform}] Synced {count} metric rows")
        return count

    # ── Sync Log ────────────────────────────────────────────────

    def _log_start(self, platform: str, sync_type: str) -> int:
        return self.db.insert(
            "INSERT INTO sync_log (platform, sync_type, status) VALUES (?, ?, 'STARTED')",
            (platform, sync_type),
        )

    def _log_finish(
        self,
        log_id: int,
        status: str,
        entities_synced: int,
        duration_ms: int,
        error_message: str | None = None,
    ) -> None:
        self.db.execute(
            """UPDATE sync_log SET
                   status=?, entities_synced=?, error_message=?,
                   finished_at=datetime('now'), duration_ms=?
               WHERE id=?""",
            (status, entities_synced, error_message, duration_ms, log_id),
        )

    # ── Normalization helpers ───────────────────────────────────

    def _normalize_campaign(self, raw: dict[str, Any], platform: str) -> dict[str, Any]:
        if platform == "meta":
            budget_daily = raw.get("daily_budget")
            budget_lifetime = raw.get("lifetime_budget")
            budget_type = "daily" if budget_daily else ("lifetime" if budget_lifetime else None)
            budget_val = budget_daily or budget_lifetime
            budget_amount = int(budget_val) / 100 if budget_val else None

            return {
                "platform_id": str(raw["id"]),
                "name": raw.get("name", ""),
                "objective": raw.get("objective", ""),
                "status": self._normalize_status(raw.get("status", "")),
                "budget_type": budget_type,
                "budget_amount": budget_amount,
                "currency": "BRL",
                "start_date": raw.get("start_time", ""),
                "end_date": raw.get("stop_time", ""),
            }
        elif platform == "google":
            return {
                "platform_id": str(raw["id"]),
                "name": raw.get("name", ""),
                "objective": raw.get("channel_type", ""),
                "status": self._normalize_status(raw.get("status", "")),
                "budget_type": "daily",
                "budget_amount": raw.get("budget"),
                "currency": "BRL",
                "start_date": raw.get("start_date", ""),
                "end_date": raw.get("end_date", ""),
            }
        elif platform == "linkedin":
            return {
                "platform_id": str(raw["id"]),
                "name": raw.get("name", ""),
                "objective": None,
                "status": self._normalize_status(raw.get("status", "")),
                "budget_type": "lifetime",
                "budget_amount": float(raw["budget"]) if raw.get("budget") else None,
                "currency": raw.get("currency", "BRL"),
                "start_date": raw.get("start_date", ""),
                "end_date": raw.get("end_date", ""),
            }
        else:
            raise ValueError(f"Unknown platform: {platform}")

    def _normalize_ad_set(self, raw: dict[str, Any], platform: str) -> dict[str, Any]:
        if platform == "meta":
            budget_daily = raw.get("daily_budget")
            budget_lifetime = raw.get("lifetime_budget")
            budget_type = "daily" if budget_daily else ("lifetime" if budget_lifetime else None)
            budget_val = budget_daily or budget_lifetime
            budget_amount = int(budget_val) / 100 if budget_val else None

            return {
                "platform_id": str(raw["id"]),
                "name": raw.get("name", ""),
                "status": self._normalize_status(raw.get("status", "")),
                "targeting": json.dumps(raw.get("targeting")) if raw.get("targeting") else None,
                "bid_strategy": raw.get("bid_strategy", ""),
                "budget_amount": budget_amount,
                "budget_type": budget_type,
            }
        elif platform == "google":
            return {
                "platform_id": str(raw["id"]),
                "name": raw.get("name", ""),
                "status": self._normalize_status(raw.get("status", "")),
                "targeting": None,
                "bid_strategy": raw.get("type", ""),
                "budget_amount": raw.get("cpc_bid"),
                "budget_type": "cpc_bid",
            }
        elif platform == "linkedin":
            daily_budget = raw.get("daily_budget")
            return {
                "platform_id": str(raw["id"]),
                "name": raw.get("name", ""),
                "status": self._normalize_status(raw.get("status", "")),
                "targeting": None,
                "bid_strategy": raw.get("bid_strategy", ""),
                "budget_amount": float(daily_budget) if daily_budget else None,
                "budget_type": "daily" if daily_budget else None,
            }
        else:
            raise ValueError(f"Unknown platform: {platform}")

    def _normalize_ad(self, raw: dict[str, Any], platform: str) -> dict[str, Any]:
        if platform == "meta":
            return {
                "platform_id": str(raw["id"]),
                "name": raw.get("name", ""),
                "status": self._normalize_status(raw.get("status", "")),
                "creative_data": json.dumps(raw.get("creative")) if raw.get("creative") else None,
                "preview_url": raw.get("preview_shareable_link", ""),
            }
        elif platform == "google":
            return {
                "platform_id": str(raw["id"]),
                "name": raw.get("name", ""),
                "status": self._normalize_status(raw.get("status", "")),
                "creative_data": json.dumps({"type": raw.get("type"), "final_urls": raw.get("final_urls")}),
                "preview_url": (raw.get("final_urls") or [""])[0],
            }
        elif platform == "linkedin":
            return {
                "platform_id": str(raw["id"]),
                "name": raw.get("name", ""),
                "status": self._normalize_status(raw.get("status", "")),
                "creative_data": None,
                "preview_url": None,
            }
        else:
            raise ValueError(f"Unknown platform: {platform}")

    def _normalize_metric(self, raw: dict[str, Any]) -> dict[str, Any]:
        impressions = int(raw.get("impressions", 0))
        clicks = int(raw.get("clicks", 0))
        spend = float(raw.get("spend", 0))
        conversions = int(raw.get("conversions", 0))
        conversion_value = float(raw.get("conversion_value", 0))

        ctr = float(raw.get("ctr", 0))
        cpc = float(raw.get("cpc", 0))
        cpm = float(raw.get("cpm", 0))
        cpa = (spend / conversions) if conversions > 0 else 0.0
        roas = (conversion_value / spend) if spend > 0 else 0.0

        return {
            "date": raw.get("date", ""),
            "impressions": impressions,
            "clicks": clicks,
            "spend": spend,
            "conversions": conversions,
            "conversion_value": conversion_value,
            "reach": int(raw.get("reach", 0)),
            "ctr": ctr,
            "cpc": cpc,
            "cpm": cpm,
            "cpa": cpa,
            "roas": roas,
            "currency": raw.get("currency", "BRL"),
        }

    @staticmethod
    def _normalize_status(status: str) -> str:
        """Normalize platform-specific status to: ACTIVE, PAUSED, ARCHIVED, DELETED."""
        s = status.upper()
        if s == "ENABLED":
            return "ACTIVE"
        if s == "CANCELED":
            return "ARCHIVED"
        if s == "DRAFT":
            return "PAUSED"
        return s

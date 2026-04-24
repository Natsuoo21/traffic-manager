"""Campaign action service — the functions a traffic manager calls.

Designed to be called from:
- Python scripts (now)
- Neo skill system (future, via natural language)

All methods accept human-friendly inputs (campaign name, platform name)
and return structured dicts with the result.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from loguru import logger

from app.connectors import get_active_platforms, get_connector
from app.database import Database
from app.services.sync_service import SyncService


class ActionsService:
    """High-level actions for managing ad campaigns across platforms."""

    def __init__(self, db: Database):
        self.db = db
        self.sync = SyncService(db)

    # ── Sync ────────────────────────────────────────────────────

    def sync_all(self) -> dict[str, Any]:
        """Sync all configured platforms."""
        results = self.sync.sync_all()
        return {
            "action": "sync_all",
            "platforms": [r["platform"] for r in results],
            "results": results,
        }

    def sync_platform(self, platform: str) -> dict[str, Any]:
        """Sync a specific platform."""
        return self.sync.sync_platform(platform)

    # ── Status Overview ─────────────────────────────────────────

    def get_overview(self) -> dict[str, Any]:
        """Get a high-level overview of all campaigns across platforms."""
        campaigns = self.db.execute(
            "SELECT * FROM campaigns ORDER BY platform, status"
        )
        accounts = self.db.execute("SELECT * FROM platform_accounts")

        by_platform: dict[str, dict] = {}
        for c in campaigns:
            p = c["platform"]
            if p not in by_platform:
                by_platform[p] = {"active": 0, "paused": 0, "other": 0, "campaigns": []}
            status = c["status"]
            if status == "ACTIVE":
                by_platform[p]["active"] += 1
            elif status == "PAUSED":
                by_platform[p]["paused"] += 1
            else:
                by_platform[p]["other"] += 1
            by_platform[p]["campaigns"].append({
                "id": c["id"],
                "name": c["name"],
                "status": c["status"],
                "budget": c["budget_amount"],
                "currency": c["currency"],
            })

        return {
            "action": "overview",
            "active_platforms": get_active_platforms(),
            "accounts": [dict(a) for a in accounts],
            "by_platform": by_platform,
            "total_campaigns": len(campaigns),
        }

    # ── Campaign Actions ────────────────────────────────────────

    def pause_campaign(self, campaign: str | int, platform: str | None = None) -> dict[str, Any]:
        """Pause a campaign by name or ID.

        Args:
            campaign: Campaign name (partial match) or local DB ID.
            platform: Optional platform filter (meta, google, linkedin).
        """
        row = self._resolve_campaign(campaign, platform)
        if not row:
            return {"action": "pause", "error": f"Campaign not found: {campaign}"}

        if row["status"] == "PAUSED":
            return {"action": "pause", "campaign": row["name"], "status": "already_paused"}

        connector = get_connector(row["platform"])
        result = connector.update_campaign_status(row["platform_id"], "PAUSED")

        # Update local DB
        self.db.execute(
            "UPDATE campaigns SET status = 'PAUSED', updated_at = ? WHERE id = ?",
            (datetime.now(tz=UTC).isoformat(), row["id"]),
        )

        logger.info(f"Paused campaign '{row['name']}' on {row['platform']}")
        return {
            "action": "pause",
            "campaign": row["name"],
            "platform": row["platform"],
            "status": "paused",
            "api_result": result,
        }

    def resume_campaign(self, campaign: str | int, platform: str | None = None) -> dict[str, Any]:
        """Resume (activate) a campaign by name or ID."""
        row = self._resolve_campaign(campaign, platform)
        if not row:
            return {"action": "resume", "error": f"Campaign not found: {campaign}"}

        if row["status"] == "ACTIVE":
            return {"action": "resume", "campaign": row["name"], "status": "already_active"}

        connector = get_connector(row["platform"])
        result = connector.update_campaign_status(row["platform_id"], "ACTIVE")

        self.db.execute(
            "UPDATE campaigns SET status = 'ACTIVE', updated_at = ? WHERE id = ?",
            (datetime.now(tz=UTC).isoformat(), row["id"]),
        )

        logger.info(f"Resumed campaign '{row['name']}' on {row['platform']}")
        return {
            "action": "resume",
            "campaign": row["name"],
            "platform": row["platform"],
            "status": "active",
            "api_result": result,
        }

    def update_budget(
        self, campaign: str | int, amount: float, platform: str | None = None
    ) -> dict[str, Any]:
        """Update campaign daily budget."""
        row = self._resolve_campaign(campaign, platform)
        if not row:
            return {"action": "update_budget", "error": f"Campaign not found: {campaign}"}

        connector = get_connector(row["platform"])
        result = connector.update_campaign_budget(row["platform_id"], amount)

        self.db.execute(
            "UPDATE campaigns SET budget_amount = ?, updated_at = ? WHERE id = ?",
            (amount, datetime.now(tz=UTC).isoformat(), row["id"]),
        )

        logger.info(f"Updated budget for '{row['name']}' on {row['platform']} to {amount}")
        return {
            "action": "update_budget",
            "campaign": row["name"],
            "platform": row["platform"],
            "new_budget": amount,
            "currency": row["currency"],
            "api_result": result,
        }

    # ── Metrics / Reporting ─────────────────────────────────────

    def get_campaign_metrics(
        self,
        campaign: str | int,
        days: int = 7,
        platform: str | None = None,
    ) -> dict[str, Any]:
        """Get recent metrics for a campaign."""
        row = self._resolve_campaign(campaign, platform)
        if not row:
            return {"action": "metrics", "error": f"Campaign not found: {campaign}"}

        date_from = (date.today() - timedelta(days=days)).isoformat()
        metrics = self.db.execute(
            """SELECT * FROM metrics_snapshots
               WHERE entity_type = 'campaign' AND entity_id = ? AND date >= ?
               ORDER BY date DESC""",
            (row["id"], date_from),
        )

        totals = {"impressions": 0, "clicks": 0, "spend": 0.0, "conversions": 0}
        for m in metrics:
            totals["impressions"] += m["impressions"]
            totals["clicks"] += m["clicks"]
            totals["spend"] += m["spend"]
            totals["conversions"] += m["conversions"]

        if totals["impressions"] > 0:
            totals["ctr"] = round(totals["clicks"] / totals["impressions"] * 100, 2)
            totals["cpm"] = round(totals["spend"] / totals["impressions"] * 1000, 2)
        else:
            totals["ctr"] = 0.0
            totals["cpm"] = 0.0
        if totals["clicks"] > 0:
            totals["cpc"] = round(totals["spend"] / totals["clicks"], 2)
        else:
            totals["cpc"] = 0.0

        return {
            "action": "metrics",
            "campaign": row["name"],
            "platform": row["platform"],
            "period": f"last {days} days",
            "totals": totals,
            "daily": [dict(m) for m in metrics],
        }

    def get_platform_summary(self, platform: str, days: int = 7) -> dict[str, Any]:
        """Get aggregated metrics for all campaigns of a platform."""
        date_from = (date.today() - timedelta(days=days)).isoformat()
        metrics = self.db.execute(
            """SELECT SUM(impressions) as impressions, SUM(clicks) as clicks,
                      SUM(spend) as spend, SUM(conversions) as conversions
               FROM metrics_snapshots
               WHERE platform = ? AND entity_type = 'campaign' AND date >= ?""",
            (platform, date_from),
        )

        row = metrics[0] if metrics else {}
        impressions = row["impressions"] or 0
        clicks = row["clicks"] or 0
        spend = row["spend"] or 0.0
        conversions = row["conversions"] or 0

        campaigns = self.db.execute(
            "SELECT id, name, status, budget_amount, currency FROM campaigns WHERE platform = ?",
            (platform,),
        )

        return {
            "action": "platform_summary",
            "platform": platform,
            "period": f"last {days} days",
            "totals": {
                "impressions": impressions,
                "clicks": clicks,
                "spend": spend,
                "conversions": conversions,
                "ctr": round(clicks / impressions * 100, 2) if impressions > 0 else 0,
                "cpc": round(spend / clicks, 2) if clicks > 0 else 0,
            },
            "campaigns": [dict(c) for c in campaigns],
        }

    # ── Helpers ──────────────────────────────────────────────────

    def _resolve_campaign(self, campaign: str | int, platform: str | None = None) -> dict | None:
        """Find a campaign by ID or name (partial match)."""
        # Try by ID first
        if isinstance(campaign, int) or (isinstance(campaign, str) and campaign.isdigit()):
            rows = self.db.execute(
                "SELECT * FROM campaigns WHERE id = ?", (int(campaign),)
            )
            if rows:
                return dict(rows[0])

        # Search by name (case-insensitive partial match)
        sql = "SELECT * FROM campaigns WHERE name LIKE ?"
        params: list[Any] = [f"%{campaign}%"]
        if platform:
            sql += " AND platform = ?"
            params.append(platform)

        rows = self.db.execute(sql, tuple(params))
        if len(rows) == 1:
            return dict(rows[0])
        if len(rows) > 1:
            # Multiple matches — log and return first
            names = [r["name"] for r in rows]
            logger.warning(f"Multiple campaigns match '{campaign}': {names}. Using first.")
            return dict(rows[0])
        return None

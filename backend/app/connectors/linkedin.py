from typing import Any

import httpx
from loguru import logger

from app.config import settings
from app.connectors.base import AdPlatformConnector

BASE_URL = "https://api.linkedin.com/rest"


class LinkedInConnector(AdPlatformConnector):
    """LinkedIn Ads connector using REST API + httpx."""

    platform = "linkedin"

    def __init__(self) -> None:
        self.account_id = settings.linkedin_ad_account_id
        self.headers = {
            "Authorization": f"Bearer {settings.linkedin_access_token}",
            "LinkedIn-Version": "202404",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
        self.client = httpx.Client(base_url=BASE_URL, headers=self.headers, timeout=30)
        logger.info(f"LinkedIn connector initialized for account {self.account_id}")

    def test_connection(self) -> bool:
        try:
            resp = self.client.get(f"/adAccounts/{self.account_id}")
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"LinkedIn connection test failed: {e}")
            return False

    def get_campaigns(self, status_filter: str | None = None) -> list[dict[str, Any]]:
        # LinkedIn calls these "Campaign Groups"
        params: dict[str, Any] = {
            "q": "search",
            "search": f"(account:(values:List(urn:li:sponsoredAccount:{self.account_id})))",
        }
        if status_filter:
            status_map = {"ACTIVE": "ACTIVE", "PAUSED": "PAUSED"}
            li_status = status_map.get(status_filter, status_filter)
            params["search"] += f",(status:(values:List({li_status})))"

        resp = self.client.get("/adCampaignGroups", params=params)
        resp.raise_for_status()
        data = resp.json()

        campaigns = []
        for cg in data.get("elements", []):
            campaigns.append({
                "id": str(cg.get("id", "")),
                "name": cg.get("name", ""),
                "status": cg.get("status", ""),
                "budget": cg.get("totalBudget", {}).get("amount", ""),
                "currency": cg.get("totalBudget", {}).get("currencyCode", "BRL"),
                "start_date": cg.get("runSchedule", {}).get("start", ""),
                "end_date": cg.get("runSchedule", {}).get("end", ""),
                "platform_data": cg,
            })
        return campaigns

    def get_ad_sets(self, campaign_id: str) -> list[dict[str, Any]]:
        # LinkedIn calls these "Campaigns" (under Campaign Groups)
        params = {
            "q": "search",
            "search": f"(campaignGroup:(values:List(urn:li:sponsoredCampaignGroup:{campaign_id})))",
        }
        resp = self.client.get("/adCampaigns", params=params)
        resp.raise_for_status()
        data = resp.json()

        ad_sets = []
        for c in data.get("elements", []):
            ad_sets.append({
                "id": str(c.get("id", "")),
                "name": c.get("name", ""),
                "status": c.get("status", ""),
                "daily_budget": c.get("dailyBudget", {}).get("amount", ""),
                "bid_strategy": c.get("optimizationTargetType", ""),
                "platform_data": c,
            })
        return ad_sets

    def get_ads(self, ad_set_id: str) -> list[dict[str, Any]]:
        # LinkedIn calls these "Creatives"
        params = {
            "q": "search",
            "search": f"(campaign:(values:List(urn:li:sponsoredCampaign:{ad_set_id})))",
        }
        resp = self.client.get("/adCreatives", params=params)
        resp.raise_for_status()
        data = resp.json()

        ads = []
        for cr in data.get("elements", []):
            ads.append({
                "id": str(cr.get("id", "")),
                "name": cr.get("name", ""),
                "status": cr.get("status", ""),
                "platform_data": cr,
            })
        return ads

    def get_metrics(
        self,
        entity_type: str,
        entity_id: str,
        date_from: str,
        date_to: str,
    ) -> list[dict[str, Any]]:
        pivot = {
            "campaign": "CAMPAIGN_GROUP",
            "ad_set": "CAMPAIGN",
            "ad": "CREATIVE",
        }
        li_pivot = pivot.get(entity_type, "CAMPAIGN_GROUP")

        entity_urn_map = {
            "campaign": f"urn:li:sponsoredCampaignGroup:{entity_id}",
            "ad_set": f"urn:li:sponsoredCampaign:{entity_id}",
            "ad": f"urn:li:sponsoredCreative:{entity_id}",
        }
        entity_urn = entity_urn_map.get(entity_type, entity_id)

        # Parse dates (YYYY-MM-DD)
        from_parts = date_from.split("-")
        to_parts = date_to.split("-")

        params = {
            "q": "analytics",
            "pivot": li_pivot,
            "dateRange": (
                f"(start:(year:{from_parts[0]},month:{from_parts[1]},day:{from_parts[2]}),"
                f"end:(year:{to_parts[0]},month:{to_parts[1]},day:{to_parts[2]}))"
            ),
            "timeGranularity": "DAILY",
            "campaigns": f"List({entity_urn})" if entity_type == "ad_set" else "",
            "campaignGroups": f"List({entity_urn})" if entity_type == "campaign" else "",
            "creatives": f"List({entity_urn})" if entity_type == "ad" else "",
            "fields": "impressions,clicks,costInLocalCurrency,externalWebsiteConversions",
        }
        # Remove empty params
        params = {k: v for k, v in params.items() if v}

        resp = self.client.get("/adAnalytics", params=params)
        resp.raise_for_status()
        data = resp.json()

        metrics = []
        for row in data.get("elements", []):
            date_range = row.get("dateRange", {}).get("start", {})
            date_str = f"{date_range.get('year', '')}-{date_range.get('month', ''):02d}-{date_range.get('day', ''):02d}"
            impressions = row.get("impressions", 0)
            clicks = row.get("clicks", 0)
            spend = float(row.get("costInLocalCurrency", "0"))

            metrics.append({
                "date": date_str,
                "impressions": impressions,
                "clicks": clicks,
                "spend": spend,
                "conversions": row.get("externalWebsiteConversions", 0),
                "ctr": (clicks / impressions * 100) if impressions > 0 else 0,
                "cpc": (spend / clicks) if clicks > 0 else 0,
                "cpm": (spend / impressions * 1000) if impressions > 0 else 0,
            })
        return metrics

    def update_campaign_status(self, campaign_id: str, status: str) -> dict[str, Any]:
        resp = self.client.post(
            f"/adCampaignGroups/{campaign_id}",
            json={"patch": {"$set": {"status": status}}},
        )
        resp.raise_for_status()
        return {"id": campaign_id, "status": status}

    def update_campaign_budget(self, campaign_id: str, amount: float) -> dict[str, Any]:
        resp = self.client.post(
            f"/adCampaignGroups/{campaign_id}",
            json={"patch": {"$set": {"totalBudget": {"amount": str(amount), "currencyCode": "BRL"}}}},
        )
        resp.raise_for_status()
        return {"id": campaign_id, "budget": amount}

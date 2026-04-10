from typing import Any

from loguru import logger

from app.config import settings
from app.connectors.base import AdPlatformConnector


class MetaConnector(AdPlatformConnector):
    """Meta (Facebook/Instagram) Ads connector using facebook-business SDK."""

    platform = "meta"

    def __init__(self) -> None:
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.api import FacebookAdsApi

        FacebookAdsApi.init(
            app_id=settings.meta_app_id,
            app_secret=settings.meta_app_secret,
            access_token=settings.meta_access_token,
            api_version=settings.meta_api_version,
        )
        self.account = AdAccount(settings.meta_ad_account_id)
        logger.info(f"Meta connector initialized for account {settings.meta_ad_account_id}")

    def test_connection(self) -> bool:
        try:
            self.account.api_get(fields=["name", "account_status"])
            return True
        except Exception as e:
            logger.error(f"Meta connection test failed: {e}")
            return False

    def get_campaigns(self, status_filter: str | None = None) -> list[dict[str, Any]]:
        fields = [
            "name", "objective", "status", "daily_budget", "lifetime_budget",
            "start_time", "stop_time", "created_time", "updated_time",
        ]
        params: dict[str, Any] = {}
        if status_filter:
            params["filtering"] = [{"field": "status", "operator": "EQUAL", "value": status_filter}]

        campaigns = self.account.get_campaigns(fields=fields, params=params)
        return [dict(c) for c in campaigns]

    def get_ad_sets(self, campaign_id: str) -> list[dict[str, Any]]:
        from facebook_business.adobjects.campaign import Campaign

        fields = [
            "name", "status", "targeting", "bid_strategy",
            "daily_budget", "lifetime_budget",
        ]
        campaign = Campaign(campaign_id)
        ad_sets = campaign.get_ad_sets(fields=fields)
        return [dict(a) for a in ad_sets]

    def get_ads(self, ad_set_id: str) -> list[dict[str, Any]]:
        from facebook_business.adobjects.adset import AdSet

        fields = ["name", "status", "creative", "preview_shareable_link"]
        ad_set = AdSet(ad_set_id)
        ads = ad_set.get_ads(fields=fields)
        return [dict(a) for a in ads]

    def get_metrics(
        self,
        entity_type: str,
        entity_id: str,
        date_from: str,
        date_to: str,
    ) -> list[dict[str, Any]]:
        from facebook_business.adobjects.ad import Ad
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.adset import AdSet
        from facebook_business.adobjects.campaign import Campaign

        entity_map = {
            "campaign": Campaign,
            "ad_set": AdSet,
            "ad": Ad,
            "account": AdAccount,
        }
        cls = entity_map.get(entity_type)
        if not cls:
            raise ValueError(f"Unknown entity type: {entity_type}")

        obj = cls(entity_id)
        fields = [
            "impressions", "clicks", "spend", "actions", "action_values",
            "reach", "ctr", "cpc", "cpm", "cost_per_action_type",
        ]
        params = {
            "time_range": {"since": date_from, "until": date_to},
            "time_increment": 1,
        }
        insights = obj.get_insights(fields=fields, params=params)
        return [dict(i) for i in insights]

    def update_campaign_status(self, campaign_id: str, status: str) -> dict[str, Any]:
        from facebook_business.adobjects.campaign import Campaign

        campaign = Campaign(campaign_id)
        campaign.api_update(params={"status": status})
        return {"id": campaign_id, "status": status}

    def update_campaign_budget(self, campaign_id: str, amount: float) -> dict[str, Any]:
        from facebook_business.adobjects.campaign import Campaign

        campaign = Campaign(campaign_id)
        # Meta uses cents for budget
        campaign.api_update(params={"daily_budget": int(amount * 100)})
        return {"id": campaign_id, "daily_budget": amount}

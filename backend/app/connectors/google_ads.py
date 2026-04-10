from typing import Any

from loguru import logger

from app.config import settings
from app.connectors.base import AdPlatformConnector


class GoogleAdsConnector(AdPlatformConnector):
    """Google Ads connector using google-ads SDK."""

    platform = "google"

    def __init__(self) -> None:
        from google.ads.googleads.client import GoogleAdsClient

        credentials = {
            "developer_token": settings.google_ads_developer_token,
            "client_id": settings.google_ads_client_id,
            "client_secret": settings.google_ads_client_secret,
            "refresh_token": settings.google_ads_refresh_token,
            "use_proto_plus": True,
        }
        if settings.google_ads_login_customer_id:
            credentials["login_customer_id"] = settings.google_ads_login_customer_id

        self.client = GoogleAdsClient.load_from_dict(credentials)
        self.customer_id = settings.google_ads_customer_id
        logger.info(f"Google Ads connector initialized for customer {self.customer_id}")

    def test_connection(self) -> bool:
        try:
            ga_service = self.client.get_service("GoogleAdsService")
            query = "SELECT customer.id, customer.descriptive_name FROM customer LIMIT 1"
            ga_service.search(customer_id=self.customer_id, query=query)
            return True
        except Exception as e:
            logger.error(f"Google Ads connection test failed: {e}")
            return False

    def get_campaigns(self, status_filter: str | None = None) -> list[dict[str, Any]]:
        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                campaign.id, campaign.name, campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                campaign.start_date, campaign.end_date
            FROM campaign
            ORDER BY campaign.id
        """
        if status_filter:
            status_map = {"ACTIVE": "ENABLED", "PAUSED": "PAUSED"}
            gads_status = status_map.get(status_filter, status_filter)
            query = query.replace("ORDER BY", f"WHERE campaign.status = '{gads_status}' ORDER BY")

        response = ga_service.search(customer_id=self.customer_id, query=query)
        campaigns = []
        for row in response:
            campaigns.append({
                "id": str(row.campaign.id),
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "channel_type": row.campaign.advertising_channel_type.name,
                "budget_micros": row.campaign_budget.amount_micros,
                "budget": row.campaign_budget.amount_micros / 1_000_000,
                "start_date": row.campaign.start_date,
                "end_date": row.campaign.end_date,
            })
        return campaigns

    def get_ad_sets(self, campaign_id: str) -> list[dict[str, Any]]:
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                ad_group.id, ad_group.name, ad_group.status,
                ad_group.type, ad_group.cpc_bid_micros
            FROM ad_group
            WHERE campaign.id = {campaign_id}
        """
        response = ga_service.search(customer_id=self.customer_id, query=query)
        ad_groups = []
        for row in response:
            ad_groups.append({
                "id": str(row.ad_group.id),
                "name": row.ad_group.name,
                "status": row.ad_group.status.name,
                "type": row.ad_group.type_.name,
                "cpc_bid": row.ad_group.cpc_bid_micros / 1_000_000,
            })
        return ad_groups

    def get_ads(self, ad_set_id: str) -> list[dict[str, Any]]:
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                ad_group_ad.ad.id, ad_group_ad.ad.name,
                ad_group_ad.status, ad_group_ad.ad.type,
                ad_group_ad.ad.final_urls
            FROM ad_group_ad
            WHERE ad_group.id = {ad_set_id}
        """
        response = ga_service.search(customer_id=self.customer_id, query=query)
        ads = []
        for row in response:
            ads.append({
                "id": str(row.ad_group_ad.ad.id),
                "name": row.ad_group_ad.ad.name,
                "status": row.ad_group_ad.status.name,
                "type": row.ad_group_ad.ad.type_.name,
                "final_urls": list(row.ad_group_ad.ad.final_urls),
            })
        return ads

    def get_metrics(
        self,
        entity_type: str,
        entity_id: str,
        date_from: str,
        date_to: str,
    ) -> list[dict[str, Any]]:
        ga_service = self.client.get_service("GoogleAdsService")

        entity_filter = {
            "campaign": f"campaign.id = {entity_id}",
            "ad_set": f"ad_group.id = {entity_id}",
            "ad": f"ad_group_ad.ad.id = {entity_id}",
        }
        where = entity_filter.get(entity_type, f"campaign.id = {entity_id}")

        # date format: YYYY-MM-DD → YYYYMMDD for Google Ads
        gads_from = date_from.replace("-", "")
        gads_to = date_to.replace("-", "")

        query = f"""
            SELECT
                segments.date,
                metrics.impressions, metrics.clicks, metrics.cost_micros,
                metrics.conversions, metrics.conversions_value,
                metrics.ctr, metrics.average_cpc, metrics.average_cpm
            FROM campaign
            WHERE {where}
                AND segments.date BETWEEN '{gads_from}' AND '{gads_to}'
        """
        response = ga_service.search(customer_id=self.customer_id, query=query)
        metrics = []
        for row in response:
            metrics.append({
                "date": row.segments.date,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "spend": row.metrics.cost_micros / 1_000_000,
                "conversions": int(row.metrics.conversions),
                "conversion_value": row.metrics.conversions_value,
                "ctr": row.metrics.ctr,
                "cpc": row.metrics.average_cpc / 1_000_000,
                "cpm": row.metrics.average_cpm / 1_000_000,
            })
        return metrics

    def update_campaign_status(self, campaign_id: str, status: str) -> dict[str, Any]:
        campaign_service = self.client.get_service("CampaignService")
        operation = self.client.get_type("CampaignOperation")
        campaign = operation.update
        campaign.resource_name = campaign_service.campaign_path(self.customer_id, campaign_id)

        status_map = {"ACTIVE": 2, "PAUSED": 3}  # CampaignStatusEnum values
        campaign.status = status_map.get(status, 3)

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("status")
        operation.update_mask.CopyFrom(field_mask)

        campaign_service.mutate_campaigns(
            customer_id=self.customer_id,
            operations=[operation],
        )
        return {"id": campaign_id, "status": status}

    def update_campaign_budget(self, campaign_id: str, amount: float) -> dict[str, Any]:
        # Google Ads budget is a separate resource — simplified here
        logger.warning("Google Ads budget update requires CampaignBudget resource — not yet implemented")
        return {"id": campaign_id, "budget": amount, "note": "not_implemented"}

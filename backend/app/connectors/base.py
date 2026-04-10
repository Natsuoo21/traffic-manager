from abc import ABC, abstractmethod
from typing import Any


class AdPlatformConnector(ABC):
    """Abstract interface for ad platform connectors."""

    platform: str  # 'meta', 'google', 'linkedin'

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the connector can reach the platform API."""
        ...

    @abstractmethod
    def get_campaigns(self, status_filter: str | None = None) -> list[dict[str, Any]]:
        """Fetch all campaigns from the platform."""
        ...

    @abstractmethod
    def get_ad_sets(self, campaign_id: str) -> list[dict[str, Any]]:
        """Fetch ad sets/groups for a campaign."""
        ...

    @abstractmethod
    def get_ads(self, ad_set_id: str) -> list[dict[str, Any]]:
        """Fetch ads for an ad set/group."""
        ...

    @abstractmethod
    def get_metrics(
        self,
        entity_type: str,
        entity_id: str,
        date_from: str,
        date_to: str,
    ) -> list[dict[str, Any]]:
        """Fetch performance metrics for an entity in a date range."""
        ...

    @abstractmethod
    def update_campaign_status(self, campaign_id: str, status: str) -> dict[str, Any]:
        """Update campaign status (ACTIVE, PAUSED)."""
        ...

    @abstractmethod
    def update_campaign_budget(self, campaign_id: str, amount: float) -> dict[str, Any]:
        """Update campaign budget."""
        ...

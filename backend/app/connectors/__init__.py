from app.config import settings
from app.connectors.base import AdPlatformConnector


def get_connector(platform: str) -> AdPlatformConnector:
    """Instantiate and return the connector for a given platform."""
    if platform == "meta":
        if not settings.has_meta():
            raise ValueError("Meta credentials not configured")
        from app.connectors.meta import MetaConnector

        return MetaConnector()

    elif platform == "google":
        if not settings.has_google_ads():
            raise ValueError("Google Ads credentials not configured")
        from app.connectors.google_ads import GoogleAdsConnector

        return GoogleAdsConnector()

    elif platform == "linkedin":
        if not settings.has_linkedin():
            raise ValueError("LinkedIn credentials not configured")
        from app.connectors.linkedin import LinkedInConnector

        return LinkedInConnector()

    else:
        raise ValueError(f"Unknown platform: {platform}")


def get_active_platforms() -> list[str]:
    """Return list of platform names that have valid credentials configured."""
    platforms = []
    if settings.has_meta():
        platforms.append("meta")
    if settings.has_google_ads():
        platforms.append("google")
    if settings.has_linkedin():
        platforms.append("linkedin")
    return platforms

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str | None:
    """Find .env.development if it exists."""
    env_file = Path(__file__).parent.parent / ".env.development"
    if env_file.exists():
        return str(env_file)
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_port: int = 3002
    app_host: str = "0.0.0.0"
    db_path: str = "./data/traffic.db"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Meta
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_access_token: str = ""
    meta_ad_account_id: str = ""
    meta_pixel_id: str = ""
    meta_api_version: str = "v21.0"

    # Google Ads
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_refresh_token: str = ""
    google_ads_customer_id: str = ""
    google_ads_login_customer_id: str = ""

    # LinkedIn
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_access_token: str = ""
    linkedin_refresh_token: str = ""
    linkedin_ad_account_id: str = ""

    # Alerts
    alert_email_enabled: bool = False
    alert_email_to: str = ""
    resend_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Scheduling
    metrics_sync_cron: str = "0 */6 * * *"
    alert_check_cron: str = "0 */1 * * *"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def has_meta(self) -> bool:
        return bool(self.meta_access_token and self.meta_ad_account_id)

    def has_google_ads(self) -> bool:
        return bool(self.google_ads_developer_token and self.google_ads_refresh_token)

    def has_linkedin(self) -> bool:
        return bool(self.linkedin_access_token and self.linkedin_ad_account_id)


settings = Settings()

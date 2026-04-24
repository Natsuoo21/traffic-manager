from unittest.mock import MagicMock

from app.database import Database
from app.services.sync_service import SyncService


def _make_db() -> Database:
    return Database(":memory:")


def _make_mock_connector() -> MagicMock:
    connector = MagicMock()
    connector.platform = "meta"
    connector.get_campaigns.return_value = [
        {
            "id": "123456",
            "name": "Test Campaign",
            "objective": "CONVERSIONS",
            "status": "ACTIVE",
            "daily_budget": "5000",
            "lifetime_budget": None,
            "start_time": "2026-04-01",
            "stop_time": "2026-04-30",
        }
    ]
    connector.get_ad_sets.return_value = [
        {
            "id": "789",
            "name": "Test Ad Set",
            "status": "ACTIVE",
            "daily_budget": "2000",
            "lifetime_budget": None,
            "targeting": {"geo": "BR"},
            "bid_strategy": "LOWEST_COST",
        }
    ]
    connector.get_ads.return_value = [
        {
            "id": "999",
            "name": "Test Ad",
            "status": "ACTIVE",
            "creative": {"body": "Buy now"},
            "preview_shareable_link": "https://example.com/preview",
        }
    ]
    connector.get_metrics.return_value = [
        {
            "date": "2026-04-20",
            "impressions": 1000,
            "clicks": 50,
            "spend": 25.0,
            "conversions": 5,
            "conversion_value": 100.0,
            "reach": 800,
            "ctr": 5.0,
            "cpc": 0.5,
            "cpm": 25.0,
        }
    ]
    return connector


class TestSyncService:
    def test_sync_platform_creates_account(self, monkeypatch: object) -> None:
        db = _make_db()
        mock = _make_mock_connector()
        monkeypatch.setattr("app.services.sync_service.get_connector", lambda p: mock)  # type: ignore[attr-defined]
        monkeypatch.setattr("app.services.sync_service.settings.meta_ad_account_id", "act_123")  # type: ignore[attr-defined]

        service = SyncService(db)
        result = service.sync_platform("meta")

        assert result["status"] == "SUCCESS"
        accounts = db.execute("SELECT * FROM platform_accounts WHERE platform = 'meta'")
        assert len(accounts) == 1
        assert accounts[0]["account_id"] == "act_123"

    def test_sync_campaigns_upserts(self, monkeypatch: object) -> None:
        db = _make_db()
        mock = _make_mock_connector()
        monkeypatch.setattr("app.services.sync_service.get_connector", lambda p: mock)  # type: ignore[attr-defined]
        monkeypatch.setattr("app.services.sync_service.settings.meta_ad_account_id", "act_123")  # type: ignore[attr-defined]

        service = SyncService(db)
        service.sync_platform("meta")
        service.sync_platform("meta")  # second sync

        campaigns = db.execute("SELECT * FROM campaigns WHERE platform = 'meta'")
        assert len(campaigns) == 1  # not 2

    def test_sync_creates_hierarchy(self, monkeypatch: object) -> None:
        db = _make_db()
        mock = _make_mock_connector()
        monkeypatch.setattr("app.services.sync_service.get_connector", lambda p: mock)  # type: ignore[attr-defined]
        monkeypatch.setattr("app.services.sync_service.settings.meta_ad_account_id", "act_123")  # type: ignore[attr-defined]

        service = SyncService(db)
        service.sync_platform("meta")

        campaigns = db.execute("SELECT * FROM campaigns")
        ad_sets = db.execute("SELECT * FROM ad_sets")
        ads = db.execute("SELECT * FROM ads")
        metrics = db.execute("SELECT * FROM metrics_snapshots")

        assert len(campaigns) == 1
        assert len(ad_sets) == 1
        assert len(ads) == 1
        assert len(metrics) == 1

        # Verify FK chain
        assert ad_sets[0]["campaign_id"] == campaigns[0]["id"]
        assert ads[0]["ad_set_id"] == ad_sets[0]["id"]
        assert metrics[0]["entity_id"] == campaigns[0]["id"]

    def test_sync_log_recorded(self, monkeypatch: object) -> None:
        db = _make_db()
        mock = _make_mock_connector()
        monkeypatch.setattr("app.services.sync_service.get_connector", lambda p: mock)  # type: ignore[attr-defined]
        monkeypatch.setattr("app.services.sync_service.settings.meta_ad_account_id", "act_123")  # type: ignore[attr-defined]

        service = SyncService(db)
        service.sync_platform("meta")

        logs = db.execute("SELECT * FROM sync_log WHERE platform = 'meta'")
        assert len(logs) >= 1
        assert logs[0]["status"] == "SUCCESS"
        assert logs[0]["entities_synced"] > 0

    def test_sync_handles_connector_failure(self, monkeypatch: object) -> None:
        db = _make_db()
        failing = MagicMock()
        failing.get_campaigns.side_effect = Exception("API error")
        monkeypatch.setattr("app.services.sync_service.get_connector", lambda p: failing)  # type: ignore[attr-defined]
        monkeypatch.setattr("app.services.sync_service.settings.meta_ad_account_id", "act_123")  # type: ignore[attr-defined]

        service = SyncService(db)
        result = service.sync_platform("meta")

        assert result["status"] == "FAILED"
        assert "API error" in result["error"]

    def test_normalize_status(self) -> None:
        db = _make_db()
        service = SyncService(db)
        assert service._normalize_status("ENABLED") == "ACTIVE"
        assert service._normalize_status("PAUSED") == "PAUSED"
        assert service._normalize_status("CANCELED") == "ARCHIVED"
        assert service._normalize_status("DRAFT") == "PAUSED"
        assert service._normalize_status("ACTIVE") == "ACTIVE"

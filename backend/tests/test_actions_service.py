from unittest.mock import MagicMock

from app.database import Database
from app.services.actions_service import ActionsService


def _seed_campaign(db: Database) -> int:
    """Insert a test account + campaign, return campaign ID."""
    account_id = db.insert(
        "INSERT INTO platform_accounts (platform, account_id, account_name) VALUES (?, ?, ?)",
        ("meta", "act_123", "test account"),
    )
    campaign_id = db.insert(
        """INSERT INTO campaigns (platform, platform_id, account_id, name, status, budget_amount, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("meta", "ext_456", account_id, "Test Campaign", "ACTIVE", 50.0, "BRL"),
    )
    return campaign_id


class TestActionsService:
    def test_get_overview_empty(self) -> None:
        db = Database(":memory:")
        svc = ActionsService(db)
        result = svc.get_overview()
        assert result["total_campaigns"] == 0

    def test_get_overview_with_campaign(self) -> None:
        db = Database(":memory:")
        _seed_campaign(db)
        svc = ActionsService(db)
        result = svc.get_overview()
        assert result["total_campaigns"] == 1
        assert "meta" in result["by_platform"]
        assert result["by_platform"]["meta"]["active"] == 1

    def test_pause_campaign_by_id(self, monkeypatch: object) -> None:
        db = Database(":memory:")
        cid = _seed_campaign(db)
        mock_connector = MagicMock()
        mock_connector.update_campaign_status.return_value = {"id": "ext_456", "status": "PAUSED"}
        monkeypatch.setattr("app.services.actions_service.get_connector", lambda p: mock_connector)  # type: ignore[attr-defined]

        svc = ActionsService(db)
        result = svc.pause_campaign(cid)
        assert result["status"] == "paused"
        assert result["campaign"] == "Test Campaign"

        # Verify DB updated
        rows = db.execute("SELECT status FROM campaigns WHERE id = ?", (cid,))
        assert rows[0]["status"] == "PAUSED"

    def test_pause_already_paused(self) -> None:
        db = Database(":memory:")
        cid = _seed_campaign(db)
        db.execute("UPDATE campaigns SET status = 'PAUSED' WHERE id = ?", (cid,))

        svc = ActionsService(db)
        result = svc.pause_campaign(cid)
        assert result["status"] == "already_paused"

    def test_resume_campaign(self, monkeypatch: object) -> None:
        db = Database(":memory:")
        cid = _seed_campaign(db)
        db.execute("UPDATE campaigns SET status = 'PAUSED' WHERE id = ?", (cid,))
        mock_connector = MagicMock()
        mock_connector.update_campaign_status.return_value = {"id": "ext_456", "status": "ACTIVE"}
        monkeypatch.setattr("app.services.actions_service.get_connector", lambda p: mock_connector)  # type: ignore[attr-defined]

        svc = ActionsService(db)
        result = svc.resume_campaign(cid)
        assert result["status"] == "active"

    def test_update_budget(self, monkeypatch: object) -> None:
        db = Database(":memory:")
        cid = _seed_campaign(db)
        mock_connector = MagicMock()
        mock_connector.update_campaign_budget.return_value = {"id": "ext_456", "daily_budget": 100.0}
        monkeypatch.setattr("app.services.actions_service.get_connector", lambda p: mock_connector)  # type: ignore[attr-defined]

        svc = ActionsService(db)
        result = svc.update_budget(cid, 100.0)
        assert result["new_budget"] == 100.0

        rows = db.execute("SELECT budget_amount FROM campaigns WHERE id = ?", (cid,))
        assert rows[0]["budget_amount"] == 100.0

    def test_resolve_campaign_by_name(self) -> None:
        db = Database(":memory:")
        _seed_campaign(db)
        svc = ActionsService(db)
        result = svc.get_campaign_metrics("Test Campaign")
        assert result["campaign"] == "Test Campaign"

    def test_resolve_campaign_partial_name(self) -> None:
        db = Database(":memory:")
        _seed_campaign(db)
        svc = ActionsService(db)
        result = svc.get_campaign_metrics("Test")
        assert result["campaign"] == "Test Campaign"

    def test_campaign_not_found(self) -> None:
        db = Database(":memory:")
        svc = ActionsService(db)
        result = svc.pause_campaign("nonexistent")
        assert "error" in result

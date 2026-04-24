from fastapi.testclient import TestClient


class TestCampaignsAPI:
    def test_list_campaigns_empty(self, client: TestClient) -> None:
        resp = client.get("/api/campaigns/")
        assert resp.status_code == 200
        assert resp.json()["campaigns"] == []
        assert resp.json()["total"] == 0

    def test_list_campaigns_with_filter(self, client: TestClient) -> None:
        resp = client.get("/api/campaigns/?platform=meta&status=ACTIVE")
        assert resp.status_code == 200

    def test_get_campaign_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/campaigns/9999")
        assert resp.status_code == 404


class TestMetricsAPI:
    def test_list_metrics_empty(self, client: TestClient) -> None:
        resp = client.get("/api/metrics/")
        assert resp.status_code == 200
        assert resp.json()["metrics"] == []

    def test_list_metrics_with_filters(self, client: TestClient) -> None:
        resp = client.get("/api/metrics/?platform=meta&date_from=2026-04-01&date_to=2026-04-30")
        assert resp.status_code == 200


class TestAccountsAPI:
    def test_list_accounts_empty(self, client: TestClient) -> None:
        resp = client.get("/api/accounts/")
        assert resp.status_code == 200
        assert resp.json()["accounts"] == []


class TestSyncAPI:
    def test_sync_log_empty(self, client: TestClient) -> None:
        resp = client.get("/api/sync/log")
        assert resp.status_code == 200
        assert resp.json()["sync_logs"] == []

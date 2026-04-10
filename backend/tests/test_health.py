from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "platforms" in data


def test_campaigns_returns_empty(client: TestClient) -> None:
    resp = client.get("/api/campaigns/")
    assert resp.status_code == 200
    assert resp.json()["campaigns"] == []

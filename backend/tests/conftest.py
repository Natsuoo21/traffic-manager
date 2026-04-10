import os

import pytest
from fastapi.testclient import TestClient

# Use in-memory DB for tests
os.environ["DB_PATH"] = ":memory:"
os.environ["APP_ENV"] = "test"


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    with TestClient(app) as c:
        yield c

import os

import pytest
from fastapi.testclient import TestClient

# Unit/API tests are deterministic and never connect to a developer database.
os.environ["DATABASE_URL"] = ""

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client

def test_service_health_without_database_is_honest(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["database"]["status"] == "not_configured"
    assert response.headers["X-Request-ID"]


def test_versioned_api_health(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["service"] == "GeoAI Flood Prediction API"


def test_docs_are_available(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()

def test_health_uses_response_envelope(client):
    response = client.get("/health", headers={"X-Correlation-ID": "FRONT-health"})
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["message"] == "Health check successful"
    assert body["data"]["status"] == "ok"
    assert body["correlation_id"] == "FRONT-health"
    assert response.headers["X-Correlation-ID"] == "FRONT-health"


def test_ready_uses_response_envelope(client):
    response = client.get("/ready", headers={"X-Correlation-ID": "FRONT-ready"})
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["message"] == "Readiness check successful"
    assert body["data"]["status"] == "ready"
    assert body["data"]["database"] in {"ok", "error"}
    assert "llm_provider" in body["data"]
    assert "scheduler" in body["data"]
    assert body["correlation_id"] == "FRONT-ready"
    assert response.headers["X-Correlation-ID"] == "FRONT-ready"


def test_health_ready_do_not_expose_secrets(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-test-key")
    monkeypatch.setenv("API_KEY", "secret-api-key")

    for path in ("/health", "/ready"):
        response = client.get(path)
        serialized = response.text
        assert "secret-test-key" not in serialized
        assert "secret-api-key" not in serialized
        assert "OPENAI_API_KEY" not in serialized
        assert "API_KEY" not in serialized


def test_health_ready_include_correlation_header_when_auth_enabled(client, monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "test-api-key")

    for path in ("/health", "/ready"):
        response = client.get(path, headers={"X-Correlation-ID": "FRONT-auth-health"})
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "FRONT-auth-health"
        assert response.json()["correlation_id"] == "FRONT-auth-health"

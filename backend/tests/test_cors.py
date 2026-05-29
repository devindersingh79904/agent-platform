import os
import importlib
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def reload_main_with_env(monkeypatch):
    def _reload(cors_val):
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", cors_val)
        import app.main
        importlib.reload(app.main)
        return TestClient(app.main.app)
    return _reload

def test_cors_wildcard(reload_main_with_env):
    client = reload_main_with_env("*")
    response = client.options("/api/agents?page=1", headers={
        "Origin": "https://random-frontend.com",
        "Access-Control-Request-Method": "GET"
    })
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "*"
    assert response.headers.get("access-control-allow-credentials") != "true"
    assert "GET" in response.headers.get("access-control-allow-methods", "")

def test_cors_exact_origin(reload_main_with_env):
    client = reload_main_with_env("https://frontend.com")
    response = client.options("/api/agents?page=1", headers={
        "Origin": "https://frontend.com",
        "Access-Control-Request-Method": "GET"
    })
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "https://frontend.com"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "GET" in response.headers.get("access-control-allow-methods", "")

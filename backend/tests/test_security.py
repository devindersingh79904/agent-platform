import pytest
import os
from fastapi.testclient import TestClient
from app.main import app

def test_health_ready(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    
    res2 = client.get("/ready")
    assert res2.status_code == 200

def test_api_key_auth_rejects_missing_key(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "secret123")
    
    # We must recreate the client because middleware is bound at startup
    # For testing middleware dynamically, it can be tricky.
    # In FastAPI, changing env vars during runtime might not affect app config if it's already loaded.
    # However, our APIAuthMiddleware checks os.getenv dynamically per request!
    client = TestClient(app)
    
    res = client.get("/api/config")
    assert res.status_code == 401

def test_api_key_auth_accepts_valid_key(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "secret123")
    
    client = TestClient(app)
    
    res = client.get("/api/config", headers={"X-API-Key": "secret123"})
    assert res.status_code == 200

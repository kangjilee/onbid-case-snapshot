# tests/test_ops.py
import os
import time
from fastapi.testclient import TestClient

# Test both dev and prod configurations
def test_dev_environment():
    """Test development environment configuration"""
    os.environ["ENV"] = "dev"
    
    # Import after setting ENV
    from main import app
    client = TestClient(app)
    
    # /docs should be accessible in dev
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()

def test_unauthorized_access():
    """Test API key validation"""
    from main import app
    client = TestClient(app)
    
    # Test without API key
    response = client.post("/api/v1/profile", json={
        "job": "직장인",
        "annual_income": 50000000,
        "credit_score": 700
    })
    assert response.status_code == 401
    assert response.json()["detail"]["success"] is False
    assert response.json()["detail"]["error"]["code"] == "UNAUTHORIZED"

def test_cors_preflight():
    """Test CORS preflight request"""
    from main import app
    client = TestClient(app)
    
    # OPTIONS request should return 200 for CORS preflight
    response = client.options("/api/v1/healthz", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET"
    })
    assert response.status_code == 200

def test_enhanced_healthz():
    """Test enhanced health check with version and uptime"""
    from main import app
    client = TestClient(app)
    
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_s" in data
    assert isinstance(data["uptime_s"], (int, float))
    assert data["uptime_s"] >= 0

def test_meta_endpoint():
    """Test meta information endpoint"""
    from main import app
    client = TestClient(app)
    
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    
    data = response.json()
    assert "version" in data
    assert "git_commit" in data
    assert "started_at" in data
    assert "T" in data["started_at"]  # ISO datetime format

def test_request_tracing():
    """Test request ID tracing in headers"""
    from main import app
    client = TestClient(app)
    
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    
    # Request ID should be UUID format
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36  # UUID length
    assert request_id.count("-") == 4  # UUID format
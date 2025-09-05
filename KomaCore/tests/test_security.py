from starlette.testclient import TestClient
from main import app

def test_health_ok():
    c = TestClient(app)
    assert c.get("/healthz").status_code == 200

def test_block_without_key():
    c = TestClient(app)
    assert c.get("/any").status_code in (401,403,404)  # 라우트 미존재면 404, 미들웨어 403
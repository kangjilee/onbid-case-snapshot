# core/security.py
import hmac
from fastapi import Request
from starlette.responses import JSONResponse
from .config import X_API_KEYS

def _valid_key(k: str) -> bool:
    return any(hmac.compare_digest(k, s) for s in X_API_KEYS)

async def api_key_enforcer(request: Request, call_next):
    # 허용 예외 엔드포인트
    if request.url.path in ("/healthz", "/"):
        return await call_next(request)
    key = request.headers.get("X-API-KEY")
    if not key or not _valid_key(key):
        return JSONResponse({"detail": "invalid or missing api key"}, status_code=403)
    return await call_next(request)
import os
import time
import logging
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

from models import (
    ProfileRequest, ProfileResponse, ProfileAssumptions,
    AnalyzeRequest, AnalyzeResponse,
    BidPriceRequest, BidPriceResponse, ScenarioResult, AffordableBid,
    HealthResponse, MetaResponse, ErrorResponse,
    OnbidParseRequest, OnbidParseResponse, OnbidAreas, OnbidPayDue, OnbidFlags, OnbidDebugInfo
)
from utils import (
    get_env_var, get_env_float, clamp, generate_req_id,
    calculate_dsr_cap, simulate_investment, binary_search_bid_for_roi
)
from onbid_parser import OnbidParser

# Load environment variables
env_file = ".env.dev" if os.getenv("ENV", "dev") == "dev" else ".env.prod"
load_dotenv(dotenv_path=env_file)

# Global variables
APP_START_TIME = time.time()
APP_VERSION = "0.2.0"
GIT_COMMIT = os.getenv("GIT_COMMIT", "unknown")

# Environment configuration
ENV = os.getenv("ENV", "dev")
X_API_KEY = get_env_var("X_API_KEY", "dev")
DSR_CAP_SALARIED = get_env_float("DSR_CAP_SALARIED", 0.40)
DSR_CAP_SELFEMP = get_env_float("DSR_CAP_SELFEMP", 0.30)
STRESS_RATE_FLOOR = get_env_float("STRESS_RATE_FLOOR", 0.07)
LTV_CAP_DEFAULT = get_env_float("LTV_CAP_DEFAULT", 0.50)
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("komacore")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app with conditional docs
docs_config = {}
if ENV == "prod":
    docs_config = {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None
    }
else:
    docs_config = {
        "docs_url": "/docs",
        "redoc_url": "/redoc", 
        "openapi_url": "/openapi.json"
    }

app = FastAPI(
    title="KomaCore",
    description="부동산 투자 분석 API",
    version=APP_VERSION,
    docs_url=docs_config.get("docs_url"),
    redoc_url=docs_config.get("redoc_url"),
    openapi_url=docs_config.get("openapi_url")
)

# Add rate limiting
app.state.limiter = limiter

# Request tracing middleware
class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.headers.__dict__.setdefault("_list", []).append(
            (b"x-request-id", request_id.encode())
        )
        
        start_time = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        # Log request details (failures only for production)
        if ENV == "dev" or response.status_code >= 400:
            logger.info(
                f"{request.method} {request.url.path} {response.status_code} "
                f"{duration_ms}ms {request_id}"
            )
        
        return response

app.add_middleware(RequestTracingMiddleware)

# Add CORS middleware with development-friendly settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
    max_age=600
)

# Override default rate limit handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMIT",
                "msg": "Too Many Requests"
            }
        }
    )

# API Key validation dependency
async def validate_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != X_API_KEY:
        raise HTTPException(
            status_code=401, 
            detail={
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "msg": "Invalid API key"
                }
            }
        )
    return x_api_key

# Optional API key validation for public endpoints
async def validate_api_key_optional(x_api_key: Optional[str] = Header(None)):
    """Optional API key validation - doesn't fail if missing"""
    return x_api_key

# Root endpoint handling
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to docs in dev, return info in prod"""
    if ENV == "dev":
        return RedirectResponse("/docs")
    else:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "msg": "API documentation not available in production"
                }
            }
        )

@app.get("/api/v1/healthz", response_model=HealthResponse)
@limiter.limit(f"{RATE_LIMIT_PER_MIN}/minute")
async def health_check(request: Request):
    """Enhanced health check endpoint with uptime and version (public)"""
    uptime_s = time.time() - APP_START_TIME
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        uptime_s=round(uptime_s, 2)
    )

@app.get("/api/v1/meta", response_model=MetaResponse)
@limiter.limit(f"{RATE_LIMIT_PER_MIN}/minute")
async def meta_info(request: Request):
    """API metadata endpoint (public)"""
    return MetaResponse(
        version=APP_VERSION,
        git_commit=GIT_COMMIT,
        started_at=datetime.fromtimestamp(APP_START_TIME).isoformat()
    )

@app.post("/api/v1/profile", response_model=ProfileResponse)
@limiter.limit(f"{RATE_LIMIT_PER_MIN}/minute")
async def analyze_profile(
    request: Request,
    profile_request: ProfileRequest,
    api_key: str = Depends(validate_api_key)
):
    """Analyze personal financial profile and calculate loan limits"""
    
    # Calculate DSR cap based on job type
    dsr_cap = calculate_dsr_cap(profile_request.job, DSR_CAP_SALARIED, DSR_CAP_SELFEMP)
    
    # Stress rate (minimum of floor rate)
    stress_rate = max(STRESS_RATE_FLOOR, 0.07)
    
    # Calculate annual repayment capacity
    annual_repay_capacity = max(
        0, 
        profile_request.annual_income * dsr_cap - profile_request.existing_debt_monthly_payment * 12
    )
    
    # Calculate DSR limit
    dsr_limit = annual_repay_capacity / stress_rate if stress_rate > 0 else 0
    
    # Credit score adjustment
    credit_adj = clamp((profile_request.credit_score - 700) * 0.001, -0.1, 0.1)
    
    # Estimated loan limit
    est_loan_limit = int(max(0, dsr_limit * (1 + credit_adj)))
    
    # Cash cap (available cash)
    cash_cap = profile_request.cash_on_hand
    
    return ProfileResponse(
        est_loan_limit=est_loan_limit,
        cash_cap=cash_cap,
        assumptions=ProfileAssumptions(
            dsr_cap=dsr_cap,
            stress_rate=stress_rate,
            credit_adj=credit_adj
        ),
        req_id=generate_req_id()
    )

@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
@limiter.limit(f"{RATE_LIMIT_PER_MIN}/minute")
async def analyze_property(
    request: Request,
    analyze_request: AnalyzeRequest,
    api_key: str = Depends(validate_api_key)
):
    """Analyze property risk based on asset class and flags"""
    
    flags = []
    notes = []
    risk_level = "safe"  # Default to safe
    
    # Check risky conditions first
    if (analyze_request.flags_input.is_share_only or 
        not analyze_request.flags_input.has_land_right or 
        analyze_request.flags_input.building_only):
        risk_level = "risky"
        notes.append("지분/대지권/건물만")
        
        if analyze_request.flags_input.is_share_only:
            flags.append("share_only")
        if not analyze_request.flags_input.has_land_right:
            flags.append("no_land_right")
        if analyze_request.flags_input.building_only:
            flags.append("building_only")
    
    # Check conditional asset classes
    elif analyze_request.asset_class in ["국유재산", "수탁재산", "신탁공매"]:
        risk_level = "conditional"
        notes.append("경락 아님: VAT/대출/명의제약")
        flags.append("special_asset_class")
    
    # Check other conditional flags
    elif any([
        analyze_request.flags_input.tenant_with_seniority,
        analyze_request.flags_input.tax_arrears,
        analyze_request.flags_input.special_terms,
        analyze_request.flags_input.vat_applicable,
        analyze_request.flags_input.occupied,
        analyze_request.flags_input.defects
    ]):
        risk_level = "conditional"
        
        if analyze_request.flags_input.tenant_with_seniority:
            flags.append("tenant_with_seniority")
            notes.append("우선순위 임차인 있음")
        if analyze_request.flags_input.tax_arrears:
            flags.append("tax_arrears")
            notes.append("체납세금 있음")
        if analyze_request.flags_input.special_terms:
            flags.append("special_terms")
            notes.append("특수조건 있음")
        if analyze_request.flags_input.vat_applicable:
            flags.append("vat_applicable")
            notes.append("부가세 적용")
        if analyze_request.flags_input.occupied:
            flags.append("occupied")
            notes.append("점유자 있음")
        if analyze_request.flags_input.defects:
            flags.append("defects")
            notes.append("하자 있음")
    
    return AnalyzeResponse(
        risk_level=risk_level,
        flags=flags,
        notes=notes,
        req_id=generate_req_id()
    )

@app.post("/api/v1/bidprice", response_model=BidPriceResponse)
@limiter.limit(f"{RATE_LIMIT_PER_MIN}/minute")
async def calculate_bid_price(
    request: Request,
    bidprice_request: BidPriceRequest,
    api_key: str = Depends(validate_api_key)
):
    """Calculate optimal bid prices for different ROI scenarios"""
    
    # Define scenarios
    scenarios_config = [
        ("보수", bidprice_request.target_roi_base + 0.01),  # Conservative
        ("주력", bidprice_request.target_roi_base),         # Primary
        ("공격", bidprice_request.target_roi_base - 0.01)   # Aggressive
    ]
    
    scenarios = []
    affordable_reasons = []
    
    # Calculate bid prices for each scenario
    for scenario_name, target_roi in scenarios_config:
        bid_price, loan_amount, total_investment, monthly_net, annual_roi = binary_search_bid_for_roi(
            target_roi=target_roi,
            expected_monthly_rent=bidprice_request.expected_monthly_rent,
            mgmt_cost=bidprice_request.mgmt_cost,
            vacancy_rate=bidprice_request.vacancy_rate,
            property_tax_est=bidprice_request.property_tax_est,
            insurance_est=bidprice_request.insurance_est,
            repair_capex=bidprice_request.repair_capex,
            interest_rate=bidprice_request.interest_rate,
            est_loan_limit=bidprice_request.est_loan_limit,
            ltv_cap=LTV_CAP_DEFAULT,
            cash_cap=bidprice_request.cash_cap
        )
        
        scenarios.append(ScenarioResult(
            name=scenario_name,
            bid_price=round(bid_price),
            loan_amount=round(loan_amount),
            total_in=round(total_investment),
            monthly_net=round(monthly_net),
            annual_roi=round(annual_roi, 4)
        ))
    
    # Determine affordable bid (use primary scenario as base)
    primary_scenario = scenarios[1]  # "주력" scenario
    affordable_bid_price = primary_scenario.bid_price
    
    # Check constraints and add reasons
    if primary_scenario.loan_amount >= bidprice_request.est_loan_limit:
        affordable_reasons.append("대출한도 도달")
    if primary_scenario.total_in >= bidprice_request.cash_cap:
        affordable_reasons.append("현금보유액 한계")
    if primary_scenario.annual_roi < bidprice_request.target_roi_base:
        affordable_reasons.append("목표수익률 미달")
    
    if not affordable_reasons:
        affordable_reasons.append("제약조건 충족")
    
    return BidPriceResponse(
        scenarios=scenarios,
        affordable_bid=AffordableBid(
            bid_price=affordable_bid_price,
            reason=affordable_reasons
        ),
        req_id=generate_req_id()
    )

# Initialize OnbidParser
onbid_parser = OnbidParser()

# Debug and status endpoints for STRICT mode visibility
@app.get("/api/v1/debug/status")
async def debug_status(api_key: str = Depends(validate_api_key)):
    """Get system status and STRICT mode information"""
    strict_mode = os.getenv("SCRAPER_STRICT", "true").lower() == "true"
    
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "app_version": APP_VERSION,
        "environment": ENV,
        "strict_mode": {
            "enabled": strict_mode,
            "environment_var": os.getenv("SCRAPER_STRICT", "not_set"),
            "description": "STRICT mode blocks all mock/fake data generation"
        },
        "uptime_seconds": int(time.time() - APP_START_TIME),
        "git_commit": GIT_COMMIT,
        "rate_limits": {
            "per_minute": RATE_LIMIT_PER_MIN
        },
        "features": {
            "onbid_parser": "active",
            "cache_isolation": "enabled",
            "error_tracking": "active"
        }
    }

@app.get("/api/v1/debug/cache")
async def debug_cache(api_key: str = Depends(validate_api_key)):
    """Get cache status and STRICT mode cache info"""
    cache_dir = Path("cache")
    cache_info = {"total_entries": 0, "strict_mode_entries": 0, "contaminated_entries": 0}
    
    if cache_dir.exists():
        for case_dir in cache_dir.iterdir():
            if case_dir.is_dir():
                cache_info["total_entries"] += 1
                raw_file = case_dir / "raw_data.json"
                if raw_file.exists():
                    try:
                        with open(raw_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if data.get("strict_mode"):
                            cache_info["strict_mode_entries"] += 1
                        elif not data.get("mock_blocked", True):
                            cache_info["contaminated_entries"] += 1
                    except:
                        cache_info["contaminated_entries"] += 1
    
    return {
        "status": "ok",
        "cache_directory": str(cache_dir.absolute()),
        "cache_info": cache_info,
        "strict_mode_validation": "STRICT mode ignores non-strict cache entries"
    }

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convert 422 validation errors to 400 with structured error response"""
    return JSONResponse(
        status_code=400,
        content={
            "error_code": "INVALID_INPUT",
            "error_hint": "expected field 'case' (e.g. '2024-01774-006' or 'onbid:1234567')",
            "validation_details": exc.errors()
        }
    )

@app.post("/api/v1/onbid/parse", response_model=OnbidParseResponse)
@limiter.limit(f"{RATE_LIMIT_PER_MIN}/minute")
async def parse_onbid(
    request: Request,
    parse_request: OnbidParseRequest,
    api_key: str = Depends(validate_api_key)
):
    """Parse onbid case URL or case number and extract property information - Always returns 200"""
    
    # Always return 200 with graceful error handling - no exceptions thrown
    try:
        # Parse the onbid case - parser handles all validation and errors internally
        result = onbid_parser.parse_onbid_case(parse_request)
        return result
        
    except Exception as e:
        # Absolutely no exceptions should escape - create fallback error response
        logger.error(f"Unexpected error in parse_onbid endpoint: {str(e)}")
        
        return OnbidParseResponse(
            status="pending",
            case_no=None,
            asset_type=None,
            use_type=None,
            address=None,
            areas=OnbidAreas(),
            appraisal=None,
            min_bid=None,
            round=None,
            duty_deadline=None,
            pay_due=OnbidPayDue(),
            flags=OnbidFlags(),
            attachments=[],
            attachment_state="NONE",
            notes="시스템 오류가 발생했습니다.",
            extracted_keys=0,
            error_code="UNKNOWN",
            error_hint="알 수 없는 오류. 로그를 확인하세요.",
            debug=OnbidDebugInfo(source="unknown"),
            req_id=generate_req_id()
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
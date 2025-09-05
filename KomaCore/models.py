from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class ProfileRequest(BaseModel):
    job: str
    annual_income: int = Field(ge=0)
    credit_score: int = Field(ge=300, le=1000)
    existing_debt_principal: int = Field(default=0, ge=0)
    existing_debt_monthly_payment: int = Field(default=0, ge=0)
    desired_ltv: float = Field(default=60, ge=0, le=90)
    cash_on_hand: int = Field(default=0, ge=0)

class ProfileAssumptions(BaseModel):
    dsr_cap: float
    stress_rate: float
    credit_adj: float

class ProfileResponse(BaseModel):
    est_loan_limit: int
    cash_cap: int
    assumptions: ProfileAssumptions
    req_id: str

class FlagsInput(BaseModel):
    is_share_only: bool = False
    has_land_right: bool = True
    building_only: bool = False
    tenant_with_seniority: bool = False
    tax_arrears: bool = False
    special_terms: bool = False
    vat_applicable: bool = False
    occupied: bool = False
    defects: bool = False

class AnalyzeRequest(BaseModel):
    asset_class: str
    flags_input: FlagsInput

class AnalyzeResponse(BaseModel):
    risk_level: str
    flags: List[str]
    notes: List[str]
    req_id: str

class BidPriceRequest(BaseModel):
    appraisal_price: float
    market_avg_price: float
    expected_monthly_rent: float
    mgmt_cost: float
    vacancy_rate: float = Field(default=0.1, ge=0, le=0.5)
    repair_capex: float
    property_tax_est: float
    insurance_est: float
    interest_rate: float = Field(default=0.07, ge=0, le=0.25)
    target_roi_base: float = Field(default=0.08, gt=0)
    cash_cap: float
    est_loan_limit: float

class ScenarioResult(BaseModel):
    name: str
    bid_price: float
    loan_amount: float
    total_in: float
    monthly_net: float
    annual_roi: float

class AffordableBid(BaseModel):
    bid_price: float
    reason: List[str]

class BidPriceResponse(BaseModel):
    scenarios: List[ScenarioResult]
    affordable_bid: AffordableBid
    req_id: str

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_s: float

class MetaResponse(BaseModel):
    version: str
    git_commit: str
    started_at: str

class ErrorResponse(BaseModel):
    success: bool = False
    error: dict

# OnbidParse models
class OnbidParseRequest(BaseModel):
    model_config = {"populate_by_name": True}
    
    case: Optional[str] = Field(None, alias="case_no", description="Case number (e.g. '2024-01774-006') or URL or onbid ID (e.g. 'onbid:1234567')")
    url: Optional[str] = Field(None, description="Direct onbid URL (deprecated, use case instead)")
    force: bool = Field(False, description="Force re-collection ignoring cache")

class OnbidAreas(BaseModel):
    building_m2: Optional[float] = None
    land_m2: Optional[float] = None
    land_right: Optional[bool] = None

class OnbidPayDue(BaseModel):
    base_days: int = 30
    grace_days: int = 10

class OnbidFlags(BaseModel):
    지분: bool = False
    대지권없음: bool = False
    건물만: bool = False
    부가세: bool = False
    특약: bool = False

class OnbidAttachment(BaseModel):
    name: str
    saved: str

class OnbidDebugInfo(BaseModel):
    source: str  # "url" | "case" | "invalid"
    http_status: Optional[int] = None
    last_url: Optional[str] = None

class OnbidParseResponse(BaseModel):
    status: str  # "ok" | "pending"
    requested_case: Optional[str] = None  # User input (original case_no or url)
    case_key: Optional[str] = None  # Normalized internal key for storage
    case_no: Optional[str] = None  # Display case_no (if extractable)
    source_hint: Optional[str] = None  # "url" | "case"
    mismatch: bool = False  # True if requested_case != case_no/case_key
    asset_type: Optional[str] = None
    use_type: Optional[str] = None
    address: Optional[str] = None
    areas: OnbidAreas
    appraisal: Optional[float] = None
    min_bid: Optional[float] = None
    round: Optional[int] = None
    duty_deadline: Optional[str] = None
    pay_due: OnbidPayDue
    flags: OnbidFlags
    attachments: List[OnbidAttachment] = []
    attachment_state: str  # "READY" | "NONE" | "DOWNLOAD_FAIL"
    notes: Optional[str] = None
    extracted_keys: int  # Count of non-null fields
    error_code: Optional[str] = None
    error_hint: Optional[str] = None  # Korean error message for UI
    debug: OnbidDebugInfo
    req_id: str
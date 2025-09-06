from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class NoticeIn(BaseModel):
    raw: str
    fast: bool = True


class NoticeOut(BaseModel):
    asset_type: Optional[str] = None
    use_type: Optional[str] = None
    has_land_right: Optional[bool] = None
    is_share: Optional[bool] = None
    building_only: Optional[bool] = None
    area_m2: Optional[float] = None
    min_price: Optional[int] = None
    round_no: Optional[int] = None
    dist_deadline: Optional[str] = None
    pay_deadline_days: Optional[int] = None
    ids: Dict[str, str] = {}


class PriceOut(BaseModel):
    sale_mid: int  # 만원
    rent_mid: int  # 만원
    mgmt_tax_ins: int  # 만원


class RightsOut(BaseModel):
    baseline: str
    assume: List[str]
    erase: List[str]
    flags: List[str]


class BidPlan(BaseModel):
    scenario: str  # 보수/주력/공격
    bid: int  # 만원
    total_in: int  # 만원
    monthly_profit: float
    yearly_yield: float


class BundleOut(BaseModel):
    notice: NoticeOut
    rights: RightsOut
    price: PriceOut
    bids: List[BidPlan]
    meta: Dict[str, Any] = {}
import math
from typing import List
from .schema import NoticeOut, PriceOut, BidPlan


def solve_bid(R: float, E: float, Y: float, C: float, L: float, r: float) -> float:
    """
    입찰가 계산 공식
    R: 임대료, E: 운영비, Y: 목표수익률, C: 취득비용, L: 대출비율, r: 대출금리
    """
    if Y * (1 - L) + L * r <= 0:
        return 0
    
    numerator = 12 * (R - E) - Y * C
    denominator = Y * (1 - L) + L * r
    
    bid = max(0, numerator / denominator)
    return bid


def make_scenarios(min_price: int, price: PriceOut, target_y: float = 8, 
                  L: float = 60, r: float = 6, vacancy: float = 10) -> List[BidPlan]:
    """3가지 시나리오 생성"""
    
    scenarios = []
    
    # 기본값 (만원 단위)
    base_rent = price.rent_mid
    base_expense = price.mgmt_tax_ins
    
    # 공실률 적용
    effective_rent = base_rent * (1 - vacancy / 100)
    
    configs = [
        ("보수", target_y + 1.5, effective_rent, base_expense + 5),
        ("주력", target_y, effective_rent + 10, base_expense),
        ("공격", target_y - 1.5, effective_rent + 20, base_expense - 5)
    ]
    
    for scenario_name, Y, R, E in configs:
        # 취득비용 (입찰가의 8%)
        C_rate = 8
        
        # 이진 탐색으로 입찰가 계산
        low, high = 1000, min_price * 2 if min_price else 100000
        best_bid = 0
        
        for _ in range(50):  # 최대 50회 반복
            mid = (low + high) / 2
            C = mid * C_rate / 100
            
            calculated_bid = solve_bid(R, E, Y, C, L/100, r/100)
            
            if abs(calculated_bid - mid) < 10:  # 10만원 이내 수렴
                best_bid = mid
                break
            elif calculated_bid > mid:
                low = mid
            else:
                high = mid
        
        if best_bid == 0:
            best_bid = min_price * 0.7 if min_price else 20000
        
        # 결과 계산
        bid_int = int(best_bid)
        total_in = int(bid_int + bid_int * C_rate / 100)
        monthly_profit = R - E - (bid_int * L/100 * r/100 / 12)
        yearly_yield = (monthly_profit * 12) / (total_in * 10000) * 100 if total_in > 0 else 0
        
        scenarios.append(BidPlan(
            scenario=scenario_name,
            bid=bid_int,
            total_in=total_in,
            monthly_profit=monthly_profit,
            yearly_yield=round(yearly_yield, 2)
        ))
    
    return scenarios
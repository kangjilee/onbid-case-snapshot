import math
from typing import List
from .schema import NoticeOut, PriceOut, BidPlan


def solve_bid(R: float, E: float, Y: float, C: float, L: float, r: float) -> float:
    """
    입찰가 계산 공식
    총투입 = 낙찰가*(1-L) + C
    연순익 = 12*(R-E) - 낙찰가*L*r  
    수익률 = 연순익/총투입
    
    solve: max(0, (12*(R-E) - Y*C) / (Y*(1-L) + L*r))
    """
    denominator = Y * (1 - L) + L * r
    if denominator <= 0:
        return 0
    
    numerator = 12 * (R - E) - Y * C
    bid = max(0, numerator / denominator)
    return bid


def make_scenarios(min_price: int, price: PriceOut, target_y: float = 8, 
                  L: float = 60, r: float = 6, vacancy: float = 10) -> List[BidPlan]:
    """입찰가 3안 시나리오 생성"""
    
    scenarios = []
    base_rent = price.rent_mid
    base_expense = price.mgmt_tax_ins
    
    # 공실률 적용
    effective_rent = base_rent * (1 - vacancy / 100)
    
    # 3가지 시나리오 설정
    configs = [
        ("보수", target_y + 1.5, effective_rent, base_expense + 5, L - 10),  # 보수적
        ("주력", target_y, effective_rent, base_expense, L),                 # 표준
        ("공격", target_y - 1, effective_rent + 3, base_expense - 3, L + 5)  # 공격적
    ]
    
    for scenario_name, Y, R, E, loan_ratio in configs:
        # 취득비용 비율
        C_rate = 8  # 8%
        
        # 이진 탐색으로 입찰가 최적화
        low, high = 1000, (min_price * 1.5) if min_price else 100000
        best_bid = 0
        
        for _ in range(50):  # 최대 50회 반복
            mid = (low + high) / 2
            C = mid * C_rate / 100
            
            calculated_bid = solve_bid(R, E, Y, C, loan_ratio/100, r/100)
            
            if abs(calculated_bid - mid) < 10:  # 10만원 이내 수렴
                best_bid = mid
                break
            elif calculated_bid > mid:
                low = mid
            else:
                high = mid
        
        # 최저가 80% 하한 & 시세 90% 상한
        if min_price:
            best_bid = max(best_bid, min_price * 0.8)
        best_bid = min(best_bid, price.sale_mid * 0.9)
        
        if best_bid <= 0:
            best_bid = min_price * 0.7 if min_price else 20000
        
        # 결과 계산
        bid_int = int(best_bid)
        acquisition_cost = bid_int * C_rate / 100
        total_in = int(bid_int + acquisition_cost)
        
        # 월수익 = 임대료 - 운영비 - 대출이자
        loan_interest_monthly = bid_int * (loan_ratio/100) * (r/100) / 12
        monthly_profit = R - E - loan_interest_monthly
        
        # 연수익률
        yearly_yield = (monthly_profit * 12) / (total_in * 10000) * 100 if total_in > 0 else 0
        
        scenarios.append(BidPlan(
            scenario=scenario_name,
            bid=bid_int,
            total_in=total_in,
            monthly_profit=round(monthly_profit, 1),
            yearly_yield=round(yearly_yield, 2)
        ))
    
    return scenarios
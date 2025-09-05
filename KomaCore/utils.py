import os
from typing import Tuple, Optional
import uuid

def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default"""
    return os.getenv(key, default)

def get_env_float(key: str, default: float) -> float:
    """Get environment variable as float with default"""
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))

def generate_req_id() -> str:
    """Generate unique request ID"""
    return str(uuid.uuid4())

def calculate_dsr_cap(job: str, dsr_salaried: float, dsr_selfemp: float) -> float:
    """Calculate DSR cap based on job type"""
    salaried_jobs = ["직장인", "사무직", "근로소득"]
    return dsr_salaried if job in salaried_jobs else dsr_selfemp

def simulate_investment(
    bid_price: float,
    expected_monthly_rent: float,
    mgmt_cost: float,
    vacancy_rate: float,
    property_tax_est: float,
    insurance_est: float,
    repair_capex: float,
    interest_rate: float,
    est_loan_limit: float,
    ltv_cap: float
) -> Tuple[float, float, float, float]:
    """
    Simulate investment returns for a given bid price
    Returns: (loan_amount, total_investment, monthly_net, annual_roi)
    """
    # Calculate loan amount (minimum of loan limit and LTV cap)
    loan_amount = min(est_loan_limit, bid_price * ltv_cap)
    
    # Calculate total investment needed
    taxes_fees = bid_price * 0.045  # 4.5% for taxes and fees
    total_investment = bid_price + taxes_fees + repair_capex - loan_amount
    
    # Calculate monthly net income
    monthly_gross_rent = expected_monthly_rent * (1 - vacancy_rate)
    monthly_expenses = (
        mgmt_cost +
        property_tax_est / 12 +
        insurance_est / 12 +
        loan_amount * interest_rate / 12
    )
    monthly_net = monthly_gross_rent - monthly_expenses
    
    # Calculate annual ROI
    annual_roi = (monthly_net * 12) / total_investment if total_investment > 0 else 0
    
    return loan_amount, total_investment, monthly_net, annual_roi

def binary_search_bid_for_roi(
    target_roi: float,
    expected_monthly_rent: float,
    mgmt_cost: float,
    vacancy_rate: float,
    property_tax_est: float,
    insurance_est: float,
    repair_capex: float,
    interest_rate: float,
    est_loan_limit: float,
    ltv_cap: float,
    cash_cap: float,
    min_bid: float = 10000000,  # 10M KRW minimum
    max_bid: float = 10000000000,  # 10B KRW maximum
    tolerance: float = 0.001,
    max_iterations: int = 100
) -> Tuple[float, float, float, float, float]:
    """
    Binary search to find bid price that achieves target ROI
    Returns: (bid_price, loan_amount, total_investment, monthly_net, annual_roi)
    """
    low, high = min_bid, max_bid
    best_bid = min_bid
    best_result = None
    
    for _ in range(max_iterations):
        mid = (low + high) / 2
        
        loan_amount, total_investment, monthly_net, annual_roi = simulate_investment(
            mid, expected_monthly_rent, mgmt_cost, vacancy_rate,
            property_tax_est, insurance_est, repair_capex, interest_rate,
            est_loan_limit, ltv_cap
        )
        
        # Check if this bid meets our constraints
        if loan_amount <= est_loan_limit and total_investment <= cash_cap:
            if abs(annual_roi - target_roi) < tolerance:
                return mid, loan_amount, total_investment, monthly_net, annual_roi
            
            if annual_roi < target_roi:
                high = mid
            else:
                low = mid
                best_bid = mid
                best_result = (loan_amount, total_investment, monthly_net, annual_roi)
        else:
            # If constraints not met, reduce bid
            high = mid
    
    # Return best feasible result
    if best_result:
        return best_bid, *best_result
    else:
        # Return minimum bid simulation if no good result found
        loan_amount, total_investment, monthly_net, annual_roi = simulate_investment(
            min_bid, expected_monthly_rent, mgmt_cost, vacancy_rate,
            property_tax_est, insurance_est, repair_capex, interest_rate,
            est_loan_limit, ltv_cap
        )
        return min_bid, loan_amount, total_investment, monthly_net, annual_roi

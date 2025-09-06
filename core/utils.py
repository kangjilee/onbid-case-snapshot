import re
from cachetools import TTLCache
from typing import Optional, Tuple


ttl_cache = TTLCache(maxsize=5000, ttl=6*3600)  # 6시간 캐시


def parse_input(raw: str) -> Tuple[str, str]:
    """
    공매번호 유형 판별 및 정규화
    Returns: (id_type, normalized_number)
    """
    raw = raw.strip()
    
    # URL에서 번호 추출
    if 'onbid.co.kr' in raw:
        patterns = [
            (r'PLNM_NO=(\d+)', 'PLNM_NO'),
            (r'PBCT_NO=(\d+)', 'PBCT_NO'),
            (r'CLTR_NO=(\d+)', 'CLTR_NO'),
            (r'CLTR_MNMT_NO=(\d+)', 'CLTR_MNMT_NO')
        ]
        
        for pattern, id_type in patterns:
            match = re.search(pattern, raw)
            if match:
                return id_type, match.group(1)
    
    # 숫자만 있는 경우
    number_only = re.sub(r'\D', '', raw)
    if number_only:
        # 길이로 추정
        if len(number_only) >= 10:
            return 'PLNM_NO', number_only
        elif len(number_only) >= 8:
            return 'PBCT_NO', number_only
        else:
            return 'CLTR_NO', number_only
    
    return 'PLNM_NO', raw


def format_currency(amount: int) -> str:
    """금액을 한국어 형식으로 포맷"""
    if amount >= 10000:
        return f"{amount//10000:,}억 {amount%10000:,}만원"
    else:
        return f"{amount:,}만원"


def calculate_yield(monthly_profit: float, total_investment: int) -> float:
    """연수익률 계산"""
    if total_investment <= 0:
        return 0.0
    return (monthly_profit * 12) / (total_investment * 10000) * 100
import re
import urllib.parse
from cachetools import TTLCache
from typing import Dict, Any


# 6시간 TTL 캐시
cache = TTLCache(maxsize=5000, ttl=6*3600)


def parse_input(raw: str) -> Dict[str, Any]:
    """
    공매번호 유형 자동 판별 및 정규화
    Returns: dict with kind and appropriate parameters
    """
    s = raw.strip()
    
    # 온비드 URL에서 번호 추출
    if s.startswith("http"):
        q = urllib.parse.urlparse(s)
        qs = urllib.parse.parse_qs(q.query)
        
        # 관리번호 우선
        for k in ("CLTR_MNMT_NO", "cltr_mnmt_no"):
            if k in qs: 
                return {"kind": "CLTR_MNMT_NO", "CLTR_MNMT_NO": qs[k][0]}
        
        # 공고번호 + 물건번호
        for k in ("PLNM_NO", "plnm_no"):
            if k in qs:
                plnm = qs[k][0]
                cltr = qs.get("CLTR_NO", qs.get("cltr_no", ["1"]))[0]
                return {"kind": "PLNM_CLTR", "PLNM_NO": plnm, "CLTR_NO": str(int(cltr))}
    
    # 물건관리번호 YYYY-####-######
    if re.fullmatch(r"\d{4}-\d{4}-\d{6}", s):
        return {"kind": "CLTR_MNMT_NO", "CLTR_MNMT_NO": s}
    
    # 공고번호-물건순번 YYYY-#####-###
    m = re.fullmatch(r"(\d{4})-(\d{5})-(\d{3})", s)
    if m:
        plnm = f"{m.group(1)}{m.group(2)}"          # 예: 202401774
        cltr = str(int(m.group(3)))                 # 006 -> 6
        return {"kind": "PLNM_CLTR", "PLNM_NO": plnm, "CLTR_NO": cltr}
    
    # 단일 공고번호(9~11자리 숫자)
    if re.fullmatch(r"\d{9,11}", s):
        return {"kind": "PLNM_NO", "PLNM_NO": s}
    
    return {"kind": "UNKNOWN", "RAW": s}


def format_currency(amount: int) -> str:
    """금액을 한국어 형식으로 포맷 (만원 단위)"""
    if amount >= 10000:
        eok = amount // 10000
        man = amount % 10000
        if man > 0:
            return f"{eok:,}억 {man:,}만원"
        else:
            return f"{eok:,}억원"
    else:
        return f"{amount:,}만원"


def calculate_yield(monthly_profit: float, total_investment: int) -> float:
    """연수익률 계산"""
    if total_investment <= 0:
        return 0.0
    return (monthly_profit * 12) / (total_investment * 10000) * 100
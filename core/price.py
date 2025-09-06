from .schema import NoticeOut, PriceOut
from .utils import ttl_cache


def estimate_price(notice: NoticeOut) -> PriceOut:
    """시세 추정 (간소화된 모델)"""
    cache_key = f"price_{notice.asset_type}_{notice.area_m2}_{notice.use_type}"
    
    if cache_key in ttl_cache:
        return ttl_cache[cache_key]
    
    # 기본 평단가 (만원/㎡)
    base_price_per_m2 = {
        '아파트': 800,
        '오피스텔': 600,
        '상가': 1200,
        '사무실': 400,
        '토지': 300,
        '기타': 500
    }.get(notice.asset_type, 500)
    
    # 용도별 조정
    if notice.use_type == '주거용':
        base_price_per_m2 *= 1.0
    elif notice.use_type == '상업용':
        base_price_per_m2 *= 1.3
    else:
        base_price_per_m2 *= 0.9
    
    # 면적별 조정
    area = notice.area_m2 or 84.5
    if area < 50:
        base_price_per_m2 *= 0.9  # 소형 할인
    elif area > 150:
        base_price_per_m2 *= 1.1  # 대형 프리미엄
    
    # 권리 상태 조정
    if notice.is_share:
        base_price_per_m2 *= 0.7  # 지분 할인
    
    if not notice.has_land_right:
        base_price_per_m2 *= 0.8  # 대지권 없음 할인
    
    if notice.building_only:
        base_price_per_m2 *= 0.6  # 건물만 할인
    
    # 시세 계산
    sale_mid = int(base_price_per_m2 * area)
    
    # 임대료 (매매가의 4-6%)
    rent_rate = 0.05
    if notice.asset_type in ['상가', '사무실']:
        rent_rate = 0.08
    
    rent_mid = int(sale_mid * rent_rate / 12)  # 월세
    
    # 관리비+세금+보험 (임대료의 20-30%)
    mgmt_tax_ins = int(rent_mid * 0.25)
    
    price = PriceOut(
        sale_mid=sale_mid,
        rent_mid=rent_mid,
        mgmt_tax_ins=mgmt_tax_ins
    )
    
    ttl_cache[cache_key] = price
    return price
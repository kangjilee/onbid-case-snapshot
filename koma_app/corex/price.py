from .schema import NoticeOut, PriceOut
from .utils import cache


def quick_price(notice: NoticeOut) -> PriceOut:
    """용도·면적 기반 상수표로 중위 시세 산출 (키 불요)"""
    cache_key = f"price_{notice.asset_type}_{notice.area_m2}_{notice.use_type}"
    
    if cache_key in cache:
        return cache[cache_key]
    
    # 기본 평단가 (만원/㎡) - 한국 시장 기준
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
    area = notice.area_m2 or 84.5  # 기본 84.5㎡
    if area < 50:
        base_price_per_m2 *= 0.9  # 소형 할인
    elif area > 150:
        base_price_per_m2 *= 1.1  # 대형 프리미엄
    
    # 권리 상태별 할인
    if notice.is_share:
        base_price_per_m2 *= 0.7  # 지분 30% 할인
    
    if not notice.has_land_right:
        base_price_per_m2 *= 0.8  # 대지권 없음 20% 할인
    
    if notice.building_only:
        base_price_per_m2 *= 0.6  # 건물만 40% 할인
    
    # 시세 계산 (만원)
    sale_mid = int(base_price_per_m2 * area)
    
    # 임대료 (매매가의 4-8% 연율)
    rent_rate = 0.08 if notice.asset_type in ['상가', '사무실'] else 0.05
    rent_mid = int(sale_mid * rent_rate / 12)  # 월세
    
    # 관리비+세금+보험 (임대료의 25%)
    mgmt_tax_ins = int(rent_mid * 0.25)
    
    price = PriceOut(
        sale_mid=sale_mid,
        rent_mid=rent_mid,
        mgmt_tax_ins=mgmt_tax_ins
    )
    
    cache[cache_key] = price
    return price


def full_price(notice: NoticeOut) -> PriceOut:
    """TODO: 국토부·상권 API 연동 (full pricing)"""
    # TODO: 국토부 실거래가 API 연동
    # TODO: 상권정보 API 연동  
    # TODO: 네이버/다음 부동산 크롤링
    
    # 현재는 quick_price로 폴백
    return quick_price(notice)
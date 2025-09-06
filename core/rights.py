from typing import List
from .schema import NoticeOut, RightsOut


def analyze_rights(notice: NoticeOut) -> RightsOut:
    """권리 플래그 분석"""
    flags = []
    assume = []
    erase = []
    
    # 기본 베이스라인 설정
    if notice.asset_type in ['아파트', '오피스텔']:
        baseline = "안전"
    elif notice.asset_type in ['상가', '사무실']:
        baseline = "조건부"
    else:
        baseline = "위험"
    
    # 플래그 분석
    if notice.is_share:
        flags.append("지분")
        baseline = "위험"
        assume.append("지분 공유자와의 분할 협의 필요")
    
    if not notice.has_land_right:
        flags.append("대지권없음")
        if baseline == "안전":
            baseline = "조건부"
        assume.append("별도 토지 사용권 확인 필요")
    
    if notice.building_only:
        flags.append("건물만")
        baseline = "위험"
        assume.append("토지 소유권 없음, 지상권 등 확인")
    
    # 회차별 리스크
    if notice.round_no and notice.round_no > 1:
        flags.append(f"{notice.round_no}회차")
        if notice.round_no >= 3:
            assume.append("유찰 이력으로 인한 가격 하락 가능성")
    
    # 권리분석 기반 제거 요소
    if notice.asset_type == "아파트" and notice.has_land_right and not notice.is_share:
        erase.append("복잡한 권리관계")
        erase.append("소유권 분쟁")
    
    if notice.use_type == "주거용":
        erase.append("상업적 제약")
    
    # 면적 기반 판단
    if notice.area_m2:
        if notice.area_m2 < 40:
            flags.append("소형")
            assume.append("임대 수요 제한적")
        elif notice.area_m2 > 200:
            flags.append("대형")
            assume.append("매매 시장 제한적")
    
    return RightsOut(
        baseline=baseline,
        assume=assume,
        erase=erase,
        flags=flags
    )
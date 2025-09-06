from typing import List
from .schema import NoticeOut, RightsOut


def make_flags(asset_type: str, has_land_right: bool, is_share: bool, building_only: bool) -> List[str]:
    """권리 플래그 생성"""
    flags = []
    
    if is_share:
        flags.append("지분")
    if not has_land_right:
        flags.append("대지권없음")
    if building_only:
        flags.append("건물만")
        
    return flags


def summarize_rights(notice: NoticeOut) -> RightsOut:
    """권리 요약 분석"""
    
    # 기본 베이스라인 설정
    if notice.asset_type in ['아파트', '오피스텔']:
        baseline = "안전"
    elif notice.asset_type in ['상가', '사무실']:
        baseline = "조건부" 
    else:
        baseline = "위험"
    
    assume = ["관리비 체납 가능성"]
    erase = ["말소기준 이하 권리"]
    flags = []
    
    # 권리 상태별 조정
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
    
    # 비압류재산 판단 (단순 휴리스틱)
    if notice.asset_type == "아파트" and notice.has_land_right and not notice.is_share:
        flags.append("비압류재산")
        erase.extend(["복잡한 권리관계", "소유권 분쟁"])
    
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
"""
Tank 경매 사이트 데이터 파싱 모듈
메인 HTML + 부속 문서들을 통합하여 정규화된 데이터 생성
"""
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional

def parse_tank_html(html_content: str) -> Dict[str, Any]:
    """Tank HTML 콘텐츠를 파싱하여 정규화된 데이터 반환"""
    if not html_content:
        return {}
    
    result = {}
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text()
    
    # 1. 기본 케이스 정보
    case_patterns = [
        r'사건번호[:\s]*([0-9\-가-힣]+)',
        r'사건[:\s]*([0-9\-가-힣]+)',
        r'관리번호[:\s]*([0-9\-]+)'
    ]
    
    for pattern in case_patterns:
        match = re.search(pattern, text)
        if match:
            result['case_no'] = match.group(1).strip()
            break
    
    # 2. 물건 정보
    result.update(extract_property_details(soup, text))
    
    # 3. 가격 정보
    result.update(extract_price_info(text))
    
    # 4. 일정 정보
    result.update(extract_schedule_info(text))
    
    # 5. 기관/법원 정보
    result.update(extract_court_info(text))
    
    # 6. 권리 관계
    result.update(extract_rights_info(text))
    
    return result

def extract_property_details(soup: BeautifulSoup, text: str) -> Dict[str, Any]:
    """부동산 상세 정보 추출"""
    details = {}
    
    # 주소 추출
    addr_patterns = [
        r'소재지[:\s]*([가-힣\s\d\-]+)',
        r'주소[:\s]*([가-힣\s\d\-]+)',
        r'소재[:\s]*([가-힣\s\d\-]+)'
    ]
    
    for pattern in addr_patterns:
        match = re.search(pattern, text)
        if match:
            addr = match.group(1).strip()
            # 불필요한 문자 제거하고 주소만 추출
            addr = re.sub(r'[\[\]()최저가면적용도매각기간].*', '', addr).strip()
            if addr:
                details['addr'] = addr
                break
    
    # 면적 정보
    area_patterns = [
        r'면적[:\s]*([\d,\.]+)\s*㎡',
        r'전유면적[:\s]*([\d,\.]+)\s*㎡',
        r'([\d,\.]+)\s*㎡'
    ]
    
    for pattern in area_patterns:
        match = re.search(pattern, text)
        if match:
            area_str = match.group(1).replace(',', '')
            try:
                area_m2 = float(area_str)
                details['area_m2'] = area_m2
                details['area_p'] = round(area_m2 / 3.3058, 1)  # 평 변환
                break
            except ValueError:
                continue
    
    # 용도 정보
    use_patterns = [
        r'용도[:\s]*([가-힣]+)',
        r'종류[:\s]*([가-힣]+)'
    ]
    
    for pattern in use_patterns:
        match = re.search(pattern, text)
        if match:
            use_type = match.group(1).strip()
            # 용도에서 불필요한 부분 제거
            use_type = re.sub(r'매각기간.*', '', use_type).strip()
            if use_type:
                details['use'] = use_type
                break
    
    # 구조 정보
    structure_match = re.search(r'구조[:\s]*([^\n\r,]+)', text)
    if structure_match:
        details['structure'] = structure_match.group(1).strip()
    
    return details

def extract_price_info(text: str) -> Dict[str, Any]:
    """가격 정보 추출"""
    prices = {}
    
    # 최저가 추출 (다양한 패턴)
    min_price_patterns = [
        r'최저가[:\s]*([\d,]+)\s*원',
        r'최저입찰가격[:\s]*([\d,]+)\s*원',
        r'입찰가격[:\s]*([\d,]+)\s*원'
    ]
    
    for pattern in min_price_patterns:
        match = re.search(pattern, text)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                prices['min_price'] = int(price_str)
                break
            except ValueError:
                continue
    
    # 감정가격 추출
    appraise_patterns = [
        r'감정가격[:\s]*([\d,]+)\s*원',
        r'감정평가액[:\s]*([\d,]+)\s*원'
    ]
    
    for pattern in appraise_patterns:
        match = re.search(pattern, text)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                prices['appraise_price'] = int(price_str)
                break
            except ValueError:
                continue
    
    # 차수 정보
    round_match = re.search(r'(\d+)\s*회차', text)
    if round_match:
        prices['round'] = int(round_match.group(1))
    
    return prices

def extract_schedule_info(text: str) -> Dict[str, Any]:
    """일정 정보 추출"""
    schedule = {}
    
    # 매각기간
    sale_period_patterns = [
        r'매각기간[:\s]*(\d{4}[-\.]\d{1,2}[-\.]\d{1,2})[^0-9]*(\d{4}[-\.]\d{1,2}[-\.]\d{1,2})',
        r'입찰기간[:\s]*(\d{4}[-\.]\d{1,2}[-\.]\d{1,2})[^0-9]*(\d{4}[-\.]\d{1,2}[-\.]\d{1,2})'
    ]
    
    for pattern in sale_period_patterns:
        match = re.search(pattern, text)
        if match:
            schedule['sale_start'] = match.group(1).replace('.', '-')
            schedule['sale_end'] = match.group(2).replace('.', '-')
            break
    
    # 배분요구종기
    dividend_pattern = r'배분요구종기[:\s]*(\d{4}[-\.]\d{1,2}[-\.]\d{1,2})'
    dividend_match = re.search(dividend_pattern, text)
    if dividend_match:
        schedule['dividend_deadline'] = dividend_match.group(1).replace('.', '-')
    
    return schedule

def extract_court_info(text: str) -> Dict[str, Any]:
    """법원/기관 정보 추출"""
    court_info = {}
    
    # 법원명
    court_patterns = [
        r'([가-힣]+지방법원[^가-힣]*[가-힣]*지원?)',
        r'([가-힣]+지방법원)',
        r'법원[:\s]*([^\n\r,]+)'
    ]
    
    for pattern in court_patterns:
        match = re.search(pattern, text)
        if match:
            court_info['court'] = match.group(1).strip()
            break
    
    return court_info

def extract_rights_info(text: str) -> Dict[str, Any]:
    """권리관계 정보 추출"""
    rights = {}
    flags = []
    
    # 권리 관계 플래그들
    flag_patterns = {
        '지분': r'지분.*?소유|지분.*?매각',
        '대지권없음': r'대지권\s*없음|대지권이\s*없음',
        '건물만': r'건물만|건물\s*만',
        '선순위저당': r'선순위.*?저당|근저당권.*?설정',
        '임차인': r'임차인|세입자',
        '점유자': r'점유자|무단점유',
        '압류': r'압류|가압류',
        '가처분': r'가처분'
    }
    
    for flag_name, pattern in flag_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            flags.append(flag_name)
    
    if flags:
        rights['flags'] = flags
    
    return rights

def parse_tank_package(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Tank 패키지 전체를 파싱하여 통합된 데이터 반환"""
    # 메인 HTML 파싱
    main_html = payload.get("main_html", "")
    main_data = parse_tank_html(main_html)
    
    # 부속 문서들 파싱 및 병합
    docs = payload.get("docs", [])
    attachments = []
    
    for doc in docs:
        if doc.get("type") == "html":
            # HTML 문서 추가 파싱
            doc_html = doc.get("html", "") or doc.get("text", "")
            doc_data = parse_tank_html(doc_html)
            
            # 주요 필드들을 메인 데이터에 병합 (기존 값이 없을 때만)
            merge_fields = [
                "appraise_price", "min_price", "dividend_deadline", 
                "sale_start", "sale_end", "area_m2", "addr", "use"
            ]
            
            for field in merge_fields:
                if field in doc_data and (field not in main_data or not main_data[field]):
                    main_data[field] = doc_data[field]
        
        # 첨부파일 정보 수집
        if doc.get("url"):
            attachments.append({
                "url": doc.get("url"),
                "type": doc.get("type", "unknown"),
                "size": doc.get("size", 0)
            })
    
    # 첨부파일 목록 추가
    if attachments:
        main_data["_attachments"] = attachments
    
    # 메타 정보 추가
    main_data["_parsed_at"] = datetime.now().isoformat()
    main_data["_source"] = "tank_package"
    
    return main_data

# 레거시 지원을 위한 별칭
parse_tank_html_old = parse_tank_html
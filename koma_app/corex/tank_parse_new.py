"""
Tank 경매 사이트 DOM 기반 파서 - 테이블 구조 정확 추출
"""
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

def _clean(s):
    """텍스트 정리"""
    return re.sub(r"\s+", " ", s or "").strip()

def _num(s):
    """숫자 추출"""
    if not s:
        return None
    x = re.sub(r"[^\d.-]", "", s.replace(",", ""))
    return float(x) if re.search(r"\d", x) else None

def _pick_by_label(soup, labels):
    """라벨로 테이블 값 찾기"""
    if not soup:
        return None
    
    labels_tuple = tuple(labels)
    
    # th/td 표 형식
    for th in soup.find_all(["th", "td"]):
        t = _clean(th.get_text())
        if any(l in t for l in labels_tuple):
            # 같은 행의 다음 셀
            td = th.find_next_sibling(["td"])
            if td:
                return _clean(td.get_text())
            
            # 부모 행의 다음 셀들
            tr = th.find_parent("tr")
            if tr:
                tds = tr.find_all("td")
                for td in tds:
                    if td != th:  # 자기 자신 제외
                        val = _clean(td.get_text())
                        if val and val != t:  # 라벨과 다른 값
                            return val
    
    # div, span 등 일반 구조
    for el in soup.find_all(text=True):
        txt = _clean(el)
        if any(l in txt for l in labels_tuple):
            # 부모 요소의 다음 형제 요소
            parent = el.find_parent()
            if parent:
                next_elem = parent.find_next_sibling()
                if next_elem:
                    val = _clean(next_elem.get_text())
                    if val:
                        return val
    
    return None

def parse_tank_html(html_or_text: str) -> Dict[str, Any]:
    """Tank HTML 파싱 - 개선된 DOM 기반"""
    html = html_or_text or ""
    soup = BeautifulSoup(html, "html.parser") if "<" in html else None
    text = _clean(soup.get_text("\n")) if soup else _clean(html)
    
    # 테이블 기반 추출
    appraise_price = _num(_pick_by_label(soup, ["감정가격", "감정가"]))
    min_price = _num(_pick_by_label(soup, ["최저가격", "최저가", "최저입찰가"]))
    land_area = _num(_pick_by_label(soup, ["토지면적"]))
    bldg_area = _num(_pick_by_label(soup, ["건물면적", "전용면적", "전유면적"]))
    div_deadline = _pick_by_label(soup, ["배분요구종기", "배당요구종기"])
    period = _pick_by_label(soup, ["매각기간", "입찰기간"])
    
    # 매각기간 파싱
    sale_start, sale_end = None, None
    if period and re.search(r"\d{2}:\d{2}", period):
        matches = re.findall(r"(20\d{2}-\d{2}-\d{2}\s*\d{2}:\d{2})", period)
        if len(matches) >= 2:
            sale_start, sale_end = matches[0], matches[1]
    
    # 헤더 정보
    title = None
    header = soup.select_one("div.header, h1, h2, .title") if soup else None
    if header:
        title = _clean(header.get_text())
    
    addr = _pick_by_label(soup, ["소재지", "주소", "소재"])
    use_type = _pick_by_label(soup, ["용도", "주용도"])
    
    # 입찰 일정 테이블 (여러 회차)
    schedules = []
    if soup:
        for tr in soup.find_all("tr"):
            row_text = _clean(tr.get_text(" "))
            # 날짜 시간 ~ 날짜 시간 패턴 + 금액
            match = re.search(
                r"(20\d{2}-\d{2}-\d{2}\s*\d{2}:\d{2}).*?"
                r"(20\d{2}-\d{2}-\d{2}\s*\d{2}:\d{2}).*?"
                r"([\d,]{3,})\s*원", row_text
            )
            if match:
                schedules.append({
                    "open": match.group(1),
                    "close": match.group(2),
                    "min_price": _num(match.group(3))
                })
    
    # 텍스트 백업 스캔 (테이블이 없는 경우)
    if not schedules:
        for line in text.split("\n"):
            match = re.search(
                r"(20\d{2}-\d{2}-\d{2}\s*\d{2}:\d{2}).*?"
                r"(20\d{2}-\d{2}-\d{2}\s*\d{2}:\d{2}).*?"
                r"([\d,]{3,})\s*원", line
            )
            if match:
                schedules.append({
                    "open": match.group(1),
                    "close": match.group(2),
                    "min_price": _num(match.group(3))
                })
    
    # 면적 통합 (건물면적 우선, 없으면 토지면적)
    area_m2 = bldg_area or land_area
    area_p = round(area_m2 / 3.3058, 2) if area_m2 else None
    
    # 케이스 번호 추출
    case_no = None
    case_patterns = [
        r'사건번호[:\s]*([0-9\-]+)',
        r'관리번호[:\s]*([0-9\-]+)',
        r'공고번호[:\s]*([0-9\-]+)'
    ]
    
    for pattern in case_patterns:
        match = re.search(pattern, text)
        if match:
            case_no = match.group(1).strip()
            break
    
    return {
        "_source": "tank",
        "case_no": case_no,
        "title": title,
        "addr": addr,
        "use": use_type,
        "appraise_price": appraise_price,
        "min_price": min_price,
        "area_m2": area_m2,
        "area_p": area_p,
        "dividend_deadline": div_deadline,
        "sale_start": sale_start,
        "sale_end": sale_end,
        "schedules": schedules,
        "_parsed_at": datetime.now().isoformat()
    }

def parse_tank_package(pkg: Dict[str, Any]) -> Dict[str, Any]:
    """Tank 패키지 전체 파싱 - 메인 + 부속문서 병합"""
    # 메인 HTML 파싱
    main = parse_tank_html(pkg.get("main_html") or pkg.get("text", ""))
    
    # 부속 문서 파싱 및 병합
    for doc in pkg.get("docs", []):
        if doc.get("type") == "html":
            sub = parse_tank_html(doc.get("html") or doc.get("text", ""))
            
            # 주요 필드를 메인 데이터에 병합 (기존 값이 없을 때만)
            merge_fields = [
                "appraise_price", "min_price", "dividend_deadline",
                "sale_start", "sale_end", "area_m2", "addr", "use"
            ]
            
            for field in merge_fields:
                if field in sub and sub[field] and (field not in main or not main[field]):
                    main[field] = sub[field]
    
    # 첨부파일 정보
    attachments = []
    for doc in pkg.get("docs", []):
        if doc.get("url"):
            attachments.append({
                "url": doc.get("url"),
                "type": doc.get("type", "unknown"),
                "size": doc.get("size", 0)
            })
    
    if attachments:
        main["_attachments"] = attachments
    
    # 소스 URL 추가
    if pkg.get("source_url"):
        main["source_url"] = pkg["source_url"]
    
    return main

# 호환성을 위한 별칭
parse_tank_html_old = parse_tank_html
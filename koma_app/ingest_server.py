# FastAPI 수신 서버: http://localhost:9000/ingest
import threading
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
import os
import re
from bs4 import BeautifulSoup

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# 데이터 저장 디렉터리
from pathlib import Path
DATA_DIR = Path("./harvest")
DATA_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/ingest")
async def ingest(req: Request):
    payload = await req.json()
    
    # 타임스탬프 추가
    payload["harvested_at"] = datetime.now().isoformat()
    
    # 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tank_harvest_{timestamp}.json"
    
    # 데이터 저장
    filepath = DATA_DIR / filename
    filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    
    # Tank HTML 파싱 처리
    try:
        from corex.tank_parse_new import parse_tank_package
        normalized_data = parse_tank_package(payload)
        print(f"[INGEST] Parsed tank data: {len(normalized_data)} fields")
    except Exception as e:
        print(f"[INGEST] Parse error: {e}")
        normalized_data = None
    
    summary = {
        "main_html_size": len(payload.get("main_html", "")),
        "docs_count": len(payload.get("docs", [])),
        "saved_to": filename
    }
    
    print(f"[INGEST] Received tank data: {summary}")
    
    return {
        "ok": True, 
        "saved": str(filepath),
        "summary": summary,
        "got": {k: (len(v) if isinstance(v, str) else len(v) if isinstance(v, list) else v) 
                for k, v in payload.items() if k != "harvested_at"}
    }

@app.get("/ingest/status")
async def status():
    files = list(DATA_DIR.glob("*.json"))
    return {
        "status": "running",
        "harvested_files": len(files),
        "latest_files": [f.name for f in sorted(files, reverse=True)[:5]]
    }

def run_server():
    print("[INGEST] Starting ingest server on http://localhost:9000")
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="warning")

def parse_tank_payload(payload):
    """Tank 페이로드를 파싱하여 정규화된 데이터 반환"""
    result = {}
    
    # 메인 HTML에서 기본 정보 추출
    main_html = payload.get("main_html", "")
    if main_html:
        soup = BeautifulSoup(main_html, 'html.parser')
        
        # 케이스 번호 추출
        case_match = re.search(r'사건번호[:\s]*([0-9\-]+)', main_html)
        if case_match:
            result['case_no'] = case_match.group(1)
        
        # 물건 정보 추출
        prop_info = extract_property_info(soup)
        result.update(prop_info)
    
    # 추가 문서들에서 정보 추출
    docs = payload.get("docs", [])
    for doc in docs:
        if doc.get("type") == "html":
            doc_data = parse_document(doc)
            result.update(doc_data)
        elif doc.get("type") == "binary":
            # PDF 등 바이너리 파일은 메타정보만 저장
            result.setdefault('attachments', []).append({
                'url': doc.get('url'),
                'type': doc.get('contentType'),
                'size': doc.get('size')
            })
    
    return result

def extract_property_info(soup):
    """메인 페이지에서 부동산 기본 정보 추출"""
    info = {}
    
    # 테이블에서 정보 추출
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                
                # 주요 필드 매핑
                if '소재지' in key or '주소' in key:
                    info['address'] = value
                elif '면적' in key and 'm²' in value:
                    area_match = re.search(r'([\d,\.]+)', value.replace(',', ''))
                    if area_match:
                        info['area_m2'] = float(area_match.group(1))
                elif '최저가' in key or '감정가' in key:
                    price_match = re.search(r'([\d,]+)', value.replace(',', ''))
                    if price_match:
                        info['min_price'] = int(price_match.group(1)) * 10000  # 만원단위
                elif '용도' in key:
                    info['use_type'] = value
                elif '구조' in key:
                    info['structure'] = value
    
    return info

def parse_document(doc):
    """개별 문서 파싱"""
    result = {}
    
    if not doc.get("text"):
        return result
    
    text = doc["text"]
    url = doc.get("url", "")
    
    # 감정평가서인 경우
    if "감정평가" in url or "감정평가" in text:
        result.update(parse_appraisal(text))
    
    # 재산명세서인 경우  
    elif "재산명세" in url or "재산명세" in text:
        result.update(parse_property_statement(text))
    
    # 등기부등본인 경우
    elif "등기" in url or "등기부" in text:
        result.update(parse_registry(text))
    
    return result

def parse_appraisal(text):
    """감정평가서 파싱"""
    result = {}
    
    # 감정가격 추출
    price_match = re.search(r'감정가격[:\s]*([\d,]+)', text)
    if price_match:
        result['appraisal_price'] = int(price_match.group(1).replace(',', '')) * 10000
    
    # 시세정보 추출
    market_match = re.search(r'시세[:\s]*([\d,]+)', text)
    if market_match:
        result['market_price'] = int(market_match.group(1).replace(',', '')) * 10000
    
    return result

def parse_property_statement(text):
    """재산명세서 파싱"""
    result = {}
    
    # 권리관계 플래그 추출
    flags = []
    flag_patterns = [
        r'지분(?:소유|매각)',
        r'대지권없음',
        r'건물만',
        r'선순위(?:저당|전세)',
        r'임차인',
        r'점유자'
    ]
    
    for pattern in flag_patterns:
        if re.search(pattern, text):
            flags.append(pattern.replace(r'(?:', '').replace(r'|', '/').replace(r')', ''))
    
    if flags:
        result['property_flags'] = flags
    
    return result

def parse_registry(text):
    """등기부등본 파싱"""
    result = {}
    
    # 소유권 정보
    if '소유권보존' in text or '소유권이전' in text:
        result['ownership_type'] = '단독소유'
    elif '지분' in text:
        result['ownership_type'] = '공유'
    
    # 근저당권 체크
    if '근저당권설정' in text:
        result['has_mortgage'] = True
    
    return result

def ensure_server():
    """백그라운드에서 수신 서버 시작"""
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    print("[INGEST] Ingest server thread started")
    return True
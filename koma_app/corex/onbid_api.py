# 온비드 API 경로 교정 + XML 파싱 전환 - 지시문 완전 구현
import os, re, time, logging
import requests
import xmltodict
from urllib.parse import urlencode, urlparse, parse_qs
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 올바른 온비드 OpenAPI 경로
BASE = "http://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr"
ENC_KEY = os.getenv("ONBID_SERVICE_KEY_ENC", os.getenv("ONBID_KEY_ONBID", ""))
TIMEOUT = int(os.getenv("API_TIMEOUT_MS", "4000")) / 1000.0
RETRIES = int(os.getenv("API_RETRIES", "3"))
CACHE_TTL_SUCCESS = int(os.getenv("CACHE_TTL_SUCCESS_SEC", "21600"))  # 6시간
CACHE_TTL_NEG = int(os.getenv("CACHE_TTL_NEG_SEC", "300"))  # 5분

# 로깅 설정
logger = logging.getLogger(__name__)

# 캐시 저장소
cache = {}  # {key: (expires_ts, data)}

# 입력 패턴 정규식
re_mgmt = re.compile(r"^\d{4}-\d{4}-\d{6}$")      # 관리번호
re_pair = re.compile(r"^\d{4}-\d{5}-\d{3}$")      # 공고-물건
re_digits = re.compile(r"^\d{9,11}$")             # 숫자만

def normalize_input(s: str):
    """입력 자동판별 → 쿼리 시퀀스 반환"""
    s = s.strip()
    
    # URL이면 숫자 토큰 추출
    if s.startswith("http"):
        tokens = re.findall(r"\d{4}-\d{4}-\d{6}|\d{4}-\d{5}-\d{3}|\d{9,11}", s)
        if tokens:
            s = max(tokens, key=len)  # 가장 긴 패턴 우선
    
    # 패턴별 쿼리 시퀀스 생성
    if re_mgmt.match(s):
        return [{"CLTR_MNMT_NO": s}]
    
    if re_pair.match(s):
        yyyy, mid, tail = s.split("-")
        plnm = f"{yyyy}{mid}"
        cltr = str(int(tail))  # 006 → 6 (선행 0 제거)
        return [
            {"PLNM_NO": plnm, "CLTR_NO": cltr},
            {"PLNM_NO": plnm}  # fallback
        ]
    
    if re_digits.match(s):
        return [{"PLNM_NO": s}]
    
    return []  # 미일치

def _cache_get(key):
    """캐시 조회"""
    rec = cache.get(key)
    if not rec:
        return None
    exp, data = rec
    if time.time() > exp:
        cache.pop(key, None)
        return None
    return data

def _cache_set(key, data, ttl):
    """캐시 저장"""
    cache[key] = (time.time() + ttl, data)

# HTTP 세션 설정
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
})

def _call_onbid(params: dict):
    """온비드 OpenAPI 호출 (XML 파싱)"""
    qs = {"serviceKey": ENC_KEY, "pageNo": 1, "numOfRows": 10}
    qs.update(params)
    
    url = f"{BASE}?{urlencode(qs, doseq=True)}"
    safe_url = url.replace(ENC_KEY, "***ENC_KEY***")
    
    backoff = 0.2
    for i in range(RETRIES):
        t0 = time.time()
        try:
            # GET 요청 (params 사용으로 URL 안전성 보장)
            r = session.get(BASE, params=qs, timeout=TIMEOUT)
            ms = int((time.time() - t0) * 1000)
            
            meta = {
                "status": r.status_code,
                "ms": ms,
                "url": safe_url,
                "attempt": i + 1
            }
            
            if r.status_code == 200:
                try:
                    # XML 파싱
                    data = xmltodict.parse(r.text)
                    
                    # 응답 구조 분석
                    header = (data.get("response", {}) or {}).get("header", {}) or {}
                    body = (data.get("response", {}) or {}).get("body", {}) or {}
                    
                    rc = str(header.get("resultCode", ""))
                    items = body.get("items")
                    
                    # 성공 판정: resultCode=="00" 또는 items 존재
                    if rc == "00" or (items not in (None, [], {})):
                        meta["resultCode"] = rc
                        meta["resultMsg"] = header.get("resultMsg", "")
                        logger.info(f"OnBid Success: {safe_url} -> {r.status_code} ({ms}ms) resultCode={rc}")
                        return True, {"header": header, "body": body}, meta
                    else:
                        meta["resultCode"] = rc
                        meta["resultMsg"] = header.get("resultMsg", "")
                        logger.warning(f"OnBid No Data: {safe_url} -> resultCode={rc}")
                        
                except Exception as e:
                    meta["body"] = r.text[:200]
                    meta["parse_error"] = str(e)
                    logger.error(f"OnBid XML Parse Error: {safe_url} -> {str(e)}")
            else:
                meta["body"] = r.text[:200]
                logger.error(f"OnBid HTTP Error: {safe_url} -> {r.status_code}")
                
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            meta = {
                "status": "EXC",
                "err": str(e),
                "url": safe_url,
                "ms": ms,
                "attempt": i + 1
            }
            logger.error(f"OnBid Exception: {safe_url} -> {str(e)}")
        
        if i < RETRIES - 1:  # 마지막 시도가 아니면 백오프
            time.sleep(backoff)
            backoff *= 2
    
    return False, None, meta

def query_unify(input_text: str):
    """통합 쿼리 함수 - 메인 엔트리포인트"""
    attempts = normalize_input(input_text)
    if not attempts:
        return {
            "ok": False,
            "reason": "INPUT_NOT_MATCHED",
            "source": "onbid",
            "logs": [],
            "input": input_text
        }

    # 캐시 키: 규격화된 시도 시퀀스
    cache_key = "|".join(sorted([urlencode(a) for a in attempts]))
    cached = _cache_get(cache_key)
    if cached:
        logger.info(f"Cache Hit: {input_text} -> onbid")
        return cached

    logs = []
    
    # 온비드 API 시도
    for params in attempts:
        ok, data, meta = _call_onbid(params)
        logs.append({"try": params, **meta})
        
        if ok:
            result = {
                "ok": True,
                "source": "onbid",
                "data": data,
                "logs": logs,
                "input": input_text,
                "cache_key": cache_key
            }
            _cache_set(cache_key, result, CACHE_TTL_SUCCESS)
            return result

    # 실패 - 네거티브 캐시
    result = {
        "ok": False,
        "source": "onbid",
        "logs": logs,
        "input": input_text,
        "cache_key": cache_key
    }
    _cache_set(cache_key, result, CACHE_TTL_NEG)
    return result

# 기존 호환성을 위한 래퍼
def fetch_onbid(raw_input: str):
    """기존 fetch_onbid 함수 호환성 래퍼"""
    result = query_unify(raw_input)
    
    if result["ok"]:
        # 성공 시 기존 형식으로 변환
        data = result["data"]
        body = data.get("body", {})
        items = body.get("items", {})
        
        # items 구조 분석 및 정규화
        item = None
        if isinstance(items, dict):
            item_list = items.get("item", [])
            if isinstance(item_list, list) and item_list:
                item = item_list[0]
            elif isinstance(item_list, dict):
                item = item_list
        elif isinstance(items, list) and items:
            item = items[0]
        else:
            item = items
        
        if item:
            # 데이터 정규화
            normalized = normalize_unify_item(item)
            meta = {
                "ok": True,
                "source": "onbid",
                "tried_urls": [log.get("url", "") for log in result["logs"]],
                "logs": result["logs"]
            }
            return normalized, meta
    
    # 실패 시
    error_msg = "INVALID REQUEST PARAMETER"
    if result["logs"]:
        last_log = result["logs"][-1]
        if "err" in last_log:
            error_msg = last_log["err"]
        elif "resultCode" in last_log:
            error_msg = f"ResultCode: {last_log['resultCode']}"
    
    meta = {
        "ok": False,
        "error": error_msg,
        "tried_urls": [log.get("url", "") for log in result["logs"]],
        "logs": result["logs"]
    }
    return None, meta

def normalize_unify_item(item: dict):
    """API 응답 아이템 정규화"""
    def safe_get(obj, keys, default=None):
        for key in keys:
            if isinstance(obj, dict) and key in obj and obj[key] not in ("", None, "NULL"):
                return obj[key]
        return default
    
    def safe_float(val):
        if val is None:
            return None
        try:
            return float(str(val).replace(",", "").strip())
        except (ValueError, AttributeError):
            return None
    
    # 필드 매핑 (온비드 XML 응답 구조에 맞게)
    area = safe_float(safe_get(item, ["AREA", "BULD_AR", "BLD_AR", "TOT_AREA", "L1_AREA"]))
    min_price = safe_float(safe_get(item, ["LST_PRC", "MIN_BID_AMT", "MIN_BID_PRC", "LOW_PRICE"]))
    
    cltr_no = safe_get(item, ["CLTR_NO", "cltrNo", "CLTRNO", "CLTR_N0"])
    if cltr_no:
        try:
            cltr_no = str(int(float(str(cltr_no))))  # 정수화로 선행 0 제거
        except:
            pass
    
    return {
        "plnm_no": safe_get(item, ["PLNM_NO", "plnmNo", "PLNMNO"]),
        "cltr_no": cltr_no,
        "mnmt_no": safe_get(item, ["CLTR_MNMT_NO", "cltrMnmtNo"]),
        "title": safe_get(item, ["CLTR_NM", "cltrNm", "TD_CLTR_NM"]),
        "use": safe_get(item, ["CLTR_KD_CD_NM", "USAGE_NM", "cltrKdCdNm", "CLTR_USE_NM"]),
        "addr": safe_get(item, ["LD_ADRS", "LD_ADDR", "ADRES", "adres"]),
        "area_m2": area,
        "area_p": round(area / 3.3058, 2) if area else None,
        "appraise_price": safe_float(safe_get(item, ["APZ_AMT", "APZ_PRC", "APRSL_AMT"])),
        "min_price": min_price,
        "round": safe_get(item, ["PBCT_RND", "PBCT_NO", "BID_RND", "RD_NO"]),
        "bid_open_dt": safe_get(item, ["PBCT_BEGN_DTM", "PBCT_BEGN_DT", "BIDBGNDT", "PBCT_DT"]),
        "org": safe_get(item, ["USID_NM", "USID_ORG_NM", "CHRG_ORG_NM", "ORGN_NM"]),
        "_raw_keys": list(item.keys()) if isinstance(item, dict) else []
    }

# 스모크 테스트 함수
def smoke_test():
    """스모크 테스트 실행"""
    test_cases = [
        "2016-0500-000201",  # 관리번호
        "2024-01774-006",    # 공고-물건
        "202401774"          # 공고번호 단독
    ]
    
    print("온비드 API 스모크 테스트 시작")
    print(f"ENC_KEY: {'설정됨' if ENC_KEY else '없음'}")
    print(f"TIMEOUT: {TIMEOUT}s")
    print(f"RETRIES: {RETRIES}")
    print()
    
    for i, case in enumerate(test_cases, 1):
        print(f"테스트 {i}: {case}")
        result = query_unify(case)
        
        if result["ok"]:
            print(f"  성공 - {result['source']}")
            if result.get("logs"):
                for log in result["logs"]:
                    status = log.get('status', 'N/A')
                    ms = log.get('ms', 'N/A')
                    rc = log.get('resultCode', 'N/A')
                    print(f"    상태: {status} ({ms}ms) resultCode: {rc}")
        else:
            print(f"  실패 - {result.get('reason', 'Unknown')}")
            if result.get("logs"):
                for log in result["logs"]:
                    status = log.get('status', 'N/A')
                    ms = log.get('ms', 'N/A')
                    print(f"    상태: {status} ({ms}ms)")
        print()
    
    print(f"캐시 항목 수: {len(cache)}")
    return test_cases

if __name__ == "__main__":
    smoke_test()
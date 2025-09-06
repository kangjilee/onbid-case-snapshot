import os
import urllib.parse
import httpx
import xmltodict
import logging
from cachetools import TTLCache
from tenacity import retry, wait_exponential, stop_after_attempt
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

log = logging.getLogger("corex.onbid_client")

ONBID_KEY = os.getenv("ONBID_KEY")
MOCK_MODE = not bool(ONBID_KEY)
BASE = "http://apis.data.go.kr/1360000/AuctionInfoService"
KEY = urllib.parse.quote(ONBID_KEY or "DUMMY")
_cache = TTLCache(maxsize=5000, ttl=6*3600)


def _build_url(params: dict) -> str:
    """쿼리 파라미터와 필수값(pageNo, numOfRows)을 포함한 URL 생성"""
    base = {"serviceKey": KEY, "pageNo": 1, "numOfRows": 10}
    base.update({k: v for k, v in params.items() if v})
    return BASE + "/getUnifyUsageCltr?" + urllib.parse.urlencode(base)


@retry(wait=wait_exponential(multiplier=0.5, max=5), stop=stop_after_attempt(3))
async def _fetch(client: httpx.AsyncClient, url: str):
    """HTTP 요청 및 XML 파싱"""
    log.info("HTTP Request: %s", url)
    r = await client.get(url, timeout=4.0)
    if r.status_code >= 400:
        log.error("응답 상태: %s, 내용: %s", r.status_code, r.text[:200])
    r.raise_for_status()
    return xmltodict.parse(r.text)


async def fetch_unify_by_any(ids: dict):
    """다중 쿼리 시스템: 관리번호 → (공고번호+물건번호) → 공고번호 단일 순으로 재시도"""
    
    if MOCK_MODE:
        log.info("MOCK 모드로 응답 생성")
        return {"response": {"body": {"items": {"item": {
            "PLNM_NO": "202401774",
            "PBCT_NO": "123456", 
            "CLTR_NO": "6",
            "CLTR_MNMT_NO": ids.get("CLTR_MNMT_NO", "2016-0500-000201"),
            "CTGR_FULL_NM": "상가/업무",
            "SCR": "84.5",
            "MIN_BID_PRC": "250000000",
            "PBCT_RND": "1",
            "PYMNT_DDLN": "40"
        }}}}}
    
    # 캐시: 관리번호 키로만 저장
    key = ids.get("CLTR_MNMT_NO")
    if key and key in _cache:
        log.info("캐시에서 데이터 반환: %s", key)
        return _cache[key]

    # 시도 순서 정의
    tries = []
    if ids.get("CLTR_MNMT_NO"):
        tries.append({"CLTR_MNMT_NO": ids["CLTR_MNMT_NO"]})
    if ids.get("PLNM_NO") and ids.get("CLTR_NO"):
        tries.append({"PLNM_NO": ids["PLNM_NO"], "CLTR_NO": ids["CLTR_NO"]})
    if ids.get("PLNM_NO"):
        tries.append({"PLNM_NO": ids["PLNM_NO"]})

    last_err = None
    async with httpx.AsyncClient() as client:
        for i, params in enumerate(tries, 1):
            url = _build_url(params)
            try:
                log.info("시도 %d/%d: %s", i, len(tries), params)
                data = await _fetch(client, url)
                
                # 응답 구조 확인
                response_body = data.get("response", {}).get("body", {})
                items = response_body.get("items", {})
                
                if isinstance(items, dict) and "item" in items:
                    item = items["item"]
                    # 단일 item인지 리스트인지 확인
                    if isinstance(item, list) and len(item) > 0:
                        log.info("복수 결과에서 첫 번째 항목 사용")
                        data["response"]["body"]["items"]["item"] = item[0]
                    elif isinstance(item, dict):
                        log.info("단일 결과 사용")
                    else:
                        continue
                    
                    # 캐시 저장
                    if key:
                        _cache[key] = data
                    log.info("데이터 조회 성공")
                    return data
                else:
                    log.warning("응답에 유효한 items가 없음")
                    continue
                    
            except Exception as e:
                log.warning("시도 %d 실패: %s", i, e)
                last_err = e
                continue
    
    raise RuntimeError(f"온비드 조회 실패: {last_err}")


def normalize_unify(x: dict) -> dict:
    """API 응답을 표준 형식으로 정규화"""
    try:
        item = x["response"]["body"]["items"]["item"]
    except KeyError as e:
        raise ValueError(f"응답 구조 오류: {e}")
    
    # ID 정보 추출
    ids = {k: item.get(k, "") for k in ("PLNM_NO", "PBCT_NO", "CLTR_NO", "CLTR_MNMT_NO")}
    
    # 용도 분류
    ctgr = item.get("CTGR_FULL_NM", "")
    if "상가" in ctgr or "업무" in ctgr:
        asset_type = "상가"
        use_type = "상업용"
    elif "아파트" in ctgr:
        asset_type = "아파트" 
        use_type = "주거용"
    else:
        asset_type = "기타"
        use_type = "기타"
    
    # 수치 데이터 변환
    area = float(item.get("SCR") or 0)
    min_price = int(item.get("MIN_BID_PRC") or 0)
    if min_price > 0:
        min_price = min_price // 10000  # 원 -> 만원
    
    round_no = int(item.get("PBCT_RND") or 1)
    pay_deadline_days = int(item.get("PYMNT_DDLN") or 40)
    
    log.info("정규화 완료: %s, %.1f㎡, %d만원, %d회차", asset_type, area, min_price, round_no)
    
    return {
        "asset_type": asset_type,
        "use_type": use_type,
        "has_land_right": True,
        "is_share": False,
        "building_only": False,
        "area_m2": area,
        "min_price": min_price,
        "round_no": round_no,
        "dist_deadline": None,
        "pay_deadline_days": pay_deadline_days,
        "ids": ids
    }


# 기존 클래스 호환성을 위한 래퍼
class OnbidClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or ONBID_KEY
        self.mock_mode = MOCK_MODE
        
        if self.mock_mode:
            log.info("MOCK 모드로 실행 - API 키 없음")
        else:
            log.info(f"LIVE 모드로 실행 - API 키 확인됨 (길이: {len(self.api_key)})")
    
    async def get_unify_by_mgmt(self, mgmt_no: str):
        """기존 호환성을 위한 래퍼"""
        ids = {"CLTR_MNMT_NO": mgmt_no}
        return await fetch_unify_by_any(ids)
    
    def normalize_unify(self, data: dict):
        """기존 호환성을 위한 래퍼"""
        from .schema import NoticeOut
        normalized = normalize_unify(data)
        return NoticeOut(**normalized)
"""
ONBID API 핵심 설정 - TLS 컨텍스트 + 도메인별 키 + 브라우저 위장
SSLV3_ALERT_ILLEGAL_PARAMETER 및 SERVICE KEY NOT REGISTERED 오류 해결
"""
import os
import ssl
import time
import logging
import httpx
import xmltodict
import streamlit as st
from urllib.parse import unquote
from .utils import parse_input

logger = logging.getLogger(__name__)

# 1) 도메인별 API 키 분리
KEY_DATA_RAW = (os.getenv("ONBID_KEY_DATA") or os.getenv("ONBID_KEY") or "").strip()
KEY_ONBID_RAW = (os.getenv("ONBID_KEY_ONBID") or os.getenv("ONBID_KEY") or "").strip()

KEY_DATA = unquote(KEY_DATA_RAW) if "%" in KEY_DATA_RAW else KEY_DATA_RAW
KEY_ONBID = unquote(KEY_ONBID_RAW) if "%" in KEY_ONBID_RAW else KEY_ONBID_RAW

# 2) TLS 컨텍스트 생성 함수 - OpenSSL3 호환성
def make_ctx_onbid():
    """ONBID API 전용 TLS 컨텍스트 - SECLEVEL=1 + TLS1.2 강제"""
    ctx = ssl.create_default_context()
    ctx.set_ciphers("HIGH:!aNULL:!MD5:!3DES:!CAMELLIA:!PSK")
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # OpenSSL3 보안 레벨 완화 (legacy cipher 허용)
    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2  # TLS1.3 비활성화
    except AttributeError:
        # Python < 3.8 호환성
        pass
    
    return ctx

# 3) 도메인별 엔드포인트 설정 (키는 런타임에 로딩)
def get_endpoint_configs():
    """런타임에 API 키를 포함한 엔드포인트 설정 반환"""
    from dotenv import load_dotenv
    load_dotenv()
    
    key_data_raw = (os.getenv("ONBID_KEY_DATA") or os.getenv("ONBID_KEY") or "").strip()
    key_onbid_raw = (os.getenv("ONBID_KEY_ONBID") or os.getenv("ONBID_KEY") or "").strip()
    
    key_data = unquote(key_data_raw) if "%" in key_data_raw else key_data_raw
    key_onbid = unquote(key_onbid_raw) if "%" in key_onbid_raw else key_onbid_raw
    
    return [
        {
            "base": "https://apis.data.go.kr/1230000/OnbidSaleInfoService/getUnifyUsageCltr",
            "key": key_data,
            "domain": "data.go.kr",
            "use_tls": True
        },
        {
            "base": "https://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr", 
            "key": key_onbid,
            "domain": "onbid.co.kr",
            "use_tls": True
        },
        {
            "base": "http://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr",
            "key": key_onbid, 
            "domain": "onbid.co.kr",
            "use_tls": False
        }
    ]

# 4) 헤더: 브라우저 위장 + XML 전용
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://www.data.go.kr/",
    "Origin": "https://www.data.go.kr",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

# 5) 기본 파라미터
COMMON_PARAMS = {"pageNo": 1, "numOfRows": 10}


def _mask(d: dict) -> dict:
    """API 키 및 민감 정보 마스킹"""
    result = {}
    for k, v in d.items():
        if "key" in k.lower() or "token" in k.lower():
            result[k] = "***"
        elif isinstance(v, str) and len(v) > 20 and any(c in v for c in "+-/="):
            # Base64 형태의 긴 문자열도 마스킹
            result[k] = f"{v[:8]}***{v[-4:]}"
        else:
            result[k] = v
    return result


def _call(config: dict, params: dict) -> str:
    """HTTP 요청 실행 - TLS 컨텍스트 + 도메인별 키 적용"""
    base_url = config["base"]
    service_key = config["key"]
    
    # 파라미터에 키 추가
    final_params = {**COMMON_PARAMS, "serviceKey": service_key, **params}
    
    # TLS 컨텍스트 설정
    if config["use_tls"]:
        ssl_context = make_ctx_onbid()
        verify = ssl_context
    else:
        verify = False
        ssl_context = None
    
    # HTTP 클라이언트 생성
    client_config = {
        "timeout": 25,  # 타임아웃 증가
        "headers": HEADERS,
        "http2": False,
        "follow_redirects": True,
        "verify": verify,
        "trust_env": False  # 환경변수 프록시 비활성화
    }
    
    with httpx.Client(**client_config) as cli:
        try:
            r = cli.get(base_url, params=final_params)
            logger.info(f"[ONBID] {r.status_code} {config['domain']} {_mask(final_params)}")
            
            # SERVICE KEY 오류 감지
            if "SERVICE_KEY" in r.text or "SERVICE KEY NOT REGISTERED" in r.text:
                raise ValueError(f"SERVICE_KEY_ERROR: {config['domain']} key invalid")
            
            r.raise_for_status()
            
            # 인코딩 보정
            if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii"):
                r.encoding = "utf-8"
                
            return r.text
            
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            logger.warning(f"TLS/연결 오류 {config['domain']}: {e}")
            raise
        except Exception as e:
            logger.warning(f"요청 실패 {config['domain']}: {e}")
            raise


@st.cache_data(ttl=21600)  # 6시간 캐시로 일일쿼터 보호
def fetch_onbid(raw_input: str):
    """온비드 API 호출 - TLS 컨텍스트 + 도메인별 키 재시도"""
    
    # 입력 파싱
    ids = parse_input(raw_input)
    logger.info(f"입력 파싱 결과: {ids}")
    
    # 파라미터 조합 계획
    param_plans = []
    if ids.get("CLTR_MNMT_NO"):
        param_plans.append({"CLTR_MNMT_NO": ids["CLTR_MNMT_NO"]})
    if ids.get("PLNM_NO") and ids.get("CLTR_NO"):
        param_plans.append({"PLNM_NO": ids["PLNM_NO"], "CLTR_NO": ids["CLTR_NO"]})
    if ids.get("PLNM_NO"):
        param_plans.append({"PLNM_NO": ids["PLNM_NO"]})
    
    if not param_plans:
        return None, {"ok": False, "error": "INVALID_INPUT", "tries": 0}
    
    last_err, tried_attempts = None, []
    
    # 도메인별 + 파라미터별 시도
    endpoint_configs = get_endpoint_configs()
    for plan in param_plans:
        for config in endpoint_configs:
            # 키가 없는 경우 건너뛰기
            if not config["key"]:
                continue
                
            try:
                logger.info(f"시도: {config['domain']} with {_mask(plan)}")
                xml_response = _call(config, plan)
                data = xmltodict.parse(xml_response)
                
                # 도메인별 응답 구조 흡수
                if "apis.data.go.kr" in config["base"]:
                    body = data.get("response", {}).get("body", {})
                else:
                    body = data.get("Body") or data.get("body") or data
                
                items = None
                if isinstance(body, dict):
                    items_container = body.get("items", {})
                    if isinstance(items_container, dict):
                        items = items_container.get("item")
                    elif isinstance(items_container, list) and len(items_container) > 0:
                        items = items_container[0]
                
                if not items:
                    # 인증 오류 메시지 확인
                    auth_msg = ""
                    if isinstance(body, dict):
                        auth_msg = body.get("returnAuthMsg", "")
                    
                    error_detail = f"NO_ITEMS|{auth_msg}|{str(data)[:150]}"
                    last_err = error_detail
                    tried_attempts.append((config["domain"], plan, error_detail))
                    continue
                
                # 성공!
                result_item = items[0] if isinstance(items, list) else items
                logger.info(f"✅ API 성공: {config['domain']}")
                
                return result_item, {
                    "ok": True,
                    "domain": config["domain"],
                    "base": config["base"],
                    "params": _mask(plan),
                    "total_tries": len(tried_attempts) + 1
                }
                
            except ValueError as ve:
                # SERVICE KEY 오류는 즉시 다음 도메인으로
                if "SERVICE_KEY_ERROR" in str(ve):
                    logger.warning(f"키 오류 {config['domain']}: 다음 도메인 시도")
                    last_err = str(ve)
                    tried_attempts.append((config["domain"], plan, str(ve)))
                    continue
                else:
                    raise
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                last_err = error_msg
                tried_attempts.append((config["domain"], plan, error_msg))
                logger.warning(f"실패: {config['domain']} - {e}")
                time.sleep(0.4)  # 레이트 제한 방지
                continue
    
    # 모든 시도 실패 - 디버깅 정보 표시
    st.toast("❌ 온비드 조회 실패: API 키 또는 TLS 설정 확인 필요", icon="⚠️")
    
    # 시도한 도메인과 오류 요약
    if tried_attempts:
        st.write("**실패한 시도 요약:**")
        for domain, params, error in tried_attempts[:4]:
            st.code(f"{domain}: {error[:100]}", language=None)
    
    logger.error(f"[ONBID][COMPLETE_FAIL] {last_err} | 총 시도: {len(tried_attempts)}")
    return None, {"ok": False, "error": last_err, "tries": len(tried_attempts)}


def normalize_onbid_item(item: dict) -> dict:
    """온비드 응답 아이템을 표준 형식으로 변환"""
    if not item:
        return {}
    
    # 필드 매핑 (다양한 응답 형식 지원)
    asset_type = "기타"
    area_m2 = 0
    min_price = 0
    round_no = 1
    
    # 자산 유형
    ctgr = item.get("CTGR_FULL_NM") or item.get("goodsNm") or ""
    if "아파트" in ctgr:
        asset_type = "아파트"
    elif "오피스텔" in ctgr:
        asset_type = "오피스텔"
    elif "상가" in ctgr or "업무" in ctgr:
        asset_type = "상가"
    
    # 면적
    area_field = item.get("SCR") or item.get("goodsArea") or "0"
    try:
        area_m2 = float(area_field)
    except (ValueError, TypeError):
        area_m2 = 0
    
    # 최저가 (원 → 만원)
    price_field = item.get("MIN_BID_PRC") or item.get("minSellPrc") or "0"
    try:
        min_price = int(price_field) // 10000 if price_field else 0
    except (ValueError, TypeError):
        min_price = 0
    
    # 회차
    round_field = item.get("PBCT_RND") or item.get("dealSeq") or "1"
    try:
        round_no = int(round_field)
    except (ValueError, TypeError):
        round_no = 1
    
    # ID 정보 추출
    ids = {
        "PLNM_NO": item.get("PLNM_NO", ""),
        "PBCT_NO": item.get("PBCT_NO", ""), 
        "CLTR_NO": item.get("CLTR_NO", ""),
        "CLTR_MNMT_NO": item.get("CLTR_MNMT_NO", "")
    }
    
    logger.info(f"정규화 완료: {asset_type}, {area_m2}㎡, {min_price}만원, {round_no}회차")
    
    return {
        "asset_type": asset_type,
        "use_type": "상업용" if asset_type == "상가" else "주거용",
        "has_land_right": True,
        "is_share": False,
        "building_only": False,
        "area_m2": area_m2,
        "min_price": min_price,
        "round_no": round_no,
        "dist_deadline": None,
        "pay_deadline_days": 40,
        "ids": ids
    }
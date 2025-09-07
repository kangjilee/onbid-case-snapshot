import os, time, logging, ssl, httpx, xmltodict
from urllib.parse import unquote
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

def _norm(k): k=(k or "").strip(); return unquote(k) if "%" in k else k
KEY_ONBID = _norm(os.getenv("ONBID_KEY_ONBID"))
KEY_DATA  = _norm(os.getenv("ONBID_KEY_DATA"))
FORCE_HTTP = os.getenv("ONBID_FORCE_HTTP","0") == "1"
PROXY_URL  = (os.getenv("ONBID_PROXY_URL") or "").strip()
OUTBOUND_PROXY = (os.getenv("OUTBOUND_PROXY") or "").strip()
USE_SYSTEM_PROXY = os.getenv("USE_SYSTEM_PROXY","0") == "1"

ONBID_URL_HTTP  = "http://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr"
ONBID_URL_HTTPS = "https://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr"
DATA_URL        = "https://apis.data.go.kr/1230000/OnbidSaleInfoService/getUnifyUsageCltr"

HEADERS = {
  "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
  "Accept":"application/xml,text/xml;q=0.9,*/*;q=0.8",
}
COMMON = {"pageNo":1, "numOfRows":10}
TIMEOUT = httpx.Timeout(connect=3.0, read=8.0, write=5.0, pool=3.0)

def _mask(d): return {k: ("***" if "key" in k.lower() else v) for k,v in d.items()}

def _make_client(fam):
    """httpx.Client 생성 - 프록시 설정 포함"""
    client_kwargs = {
        "headers": HEADERS,
        "timeout": TIMEOUT,
        "http2": False,
        "follow_redirects": True,
        "trust_env": USE_SYSTEM_PROXY
    }
    
    # 프록시 설정
    if OUTBOUND_PROXY:
        client_kwargs["proxies"] = OUTBOUND_PROXY
    
    # SSL 설정
    if fam == "onbid_http":
        client_kwargs["verify"] = False
    elif fam == "onbid_https":
        ctx = ssl.create_default_context()
        try: 
            ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.options |= ssl.OP_NO_TLSv1_3
        except: pass
        client_kwargs["verify"] = ctx
    
    return httpx.Client(**client_kwargs)

# 파서
def parse_input(s: str):
    import re, urllib.parse
    s=(s or "").strip()
    if "onbid" in s.lower():
        q = urllib.parse.parse_qs(urllib.parse.urlparse(s).query)
        return {"mnmt":None,"plnm":q.get("PLNM_NO",[None])[0] or q.get("plnmno",[None])[0],
                "cltr":(q.get("CLTR_NO",[None])[0] or q.get("cltrno",[None])[0])}
    if re.fullmatch(r"\d{4}-\d{4}-\d{6}", s): return {"mnmt":s,"plnm":None,"cltr":None}
    m = re.fullmatch(r"(\d{4})-(\d{5})-(\d{3})", s)
    if m: return {"mnmt":None,"plnm":f"{m.group(1)}{m.group(2)}","cltr":str(int(m.group(3)))}
    if re.fullmatch(r"\d{9}", s): return {"mnmt":None,"plnm":s,"cltr":None}
    return {"mnmt":None,"plnm":None,"cltr":None}

# 정규화기
def _num(x):
    import re
    if x is None: return None
    s = str(x).replace(",","").strip()
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else None

ALIAS = {
  "plnm_no":["PLNM_NO","plnmNo","PLNMNO"], "cltr_no":["CLTR_NO","cltrNo","CLTRNO","CLTR_N0"], 
  "mnmt_no":["CLTR_MNMT_NO","cltrMnmtNo"], "title":["CLTR_NM","cltrNm","TD_CLTR_NM"], 
  "use":["CLTR_KD_CD_NM","USAGE_NM","cltrKdCdNm","CLTR_USE_NM"],
  "addr":["LD_ADRS","LD_ADDR","ADRES","adres"], "area_m2":["AREA","BULD_AR","BLD_AR","TOT_AREA","L1_AREA"],
  "appraise":["APZ_AMT","APZ_PRC","APRSL_AMT"], "min_price":["LST_PRC","MIN_BID_AMT","MIN_BID_PRC","LOW_PRICE"],
  "round":["PBCT_RND","PBCT_NO","BID_RND","RD_NO"], "bid_open":["PBCT_BEGN_DTM","PBCT_BEGN_DT","BIDBGNDT","PBCT_DT"], 
  "org":["USID_NM","USID_ORG_NM","CHRG_ORG_NM","ORGN_NM"]
}

def normalize_unify_item(item: dict):
    d = {(k.upper() if isinstance(k,str) else k): v for k,v in dict(item).items()}
    def pick(key):
        for k in ALIAS[key]:
            if k in d and d[k] not in ("",None,"NULL"): return d[k]
    area = _num(pick("area_m2"))
    cltr = pick("cltr_no"); cltr = str(int(_num(cltr))) if cltr else None
    return {
        "plnm_no":pick("plnm_no"), "cltr_no":cltr, "mnmt_no":pick("mnmt_no"),
        "title":pick("title"), "use":pick("use"), "addr":pick("addr"),
        "area_m2":area, "area_p":(round(area/3.3058,2) if area else None),
        "appraise_price":_num(pick("appraise")), "min_price":_num(pick("min_price")),
        "round":pick("round"), "bid_open_dt":pick("bid_open"), "org":pick("org"),
        "_raw_keys":list(d.keys())
    }

def _extract_items(xml_text: str):
    data = xmltodict.parse(xml_text)
    body = (data.get("response") or {}).get("body") or data.get("Body") or data
    items = ((body.get("items") or {}).get("item")) if isinstance(body, dict) else None
    return items

def fetch_onbid(raw_input: str):
    ids = parse_input(raw_input)
    plans = []
    if ids["mnmt"]: plans.append({"mnmt": ids["mnmt"]})
    if ids["plnm"] and ids["cltr"]: plans.append({"plnm_no": ids["plnm"], "cltr_no": ids["cltr"]})
    if ids["plnm"]: plans.append({"plnm_no": ids["plnm"]})

    tried_urls, last_err = [], None

    # 1) 리레이 우선
    if PROXY_URL:
        client_kwargs = {"headers": {"Accept":"application/xml"}, "timeout": TIMEOUT, "trust_env": USE_SYSTEM_PROXY}
        if OUTBOUND_PROXY: client_kwargs["proxies"] = OUTBOUND_PROXY
        
        for q in plans:
            try:
                r = httpx.get(PROXY_URL, params=q, **client_kwargs)
                tried_urls.append(str(httpx.Request("GET", PROXY_URL, params=q).url))
                logging.info(f"[RELAY] {r.status_code} {PROXY_URL} {_mask(q)}")
                r.raise_for_status()
                items = _extract_items(r.text)
                if items: 
                    item = items[0] if isinstance(items, list) else items
                    return normalize_unify_item(item), {"ok":True, "via":"relay", "tried_urls": tried_urls}
                last_err = "NO_ITEMS(relay)"
            except Exception as e:
                last_err = f"RELAY_ERROR:{type(e).__name__}:{e}"

    # 2) 직접 호출
    bases = []
    if KEY_ONBID:
        if FORCE_HTTP: bases = [(ONBID_URL_HTTP, KEY_ONBID, "onbid_http")]
        else: bases = [(ONBID_URL_HTTPS, KEY_ONBID, "onbid_https"), (ONBID_URL_HTTP, KEY_ONBID, "onbid_http")]
    if KEY_DATA and not FORCE_HTTP: bases.append((DATA_URL, KEY_DATA, "data_https"))

    for base, key, fam in bases:
        for q in plans:
            # 파라미터 구성
            if "mnmt" in q:
                params = {"serviceKey": key, **COMMON, "CLTR_MNMT_NO": q["mnmt"]}
            elif "cltr_no" in q:
                params = {"serviceKey": key, **COMMON, "PLNM_NO": q["plnm_no"], "CLTR_NO": q["cltr_no"]}
            else:
                params = {"serviceKey": key, **COMMON, "PLNM_NO": q["plnm_no"]}
                
            cli = _make_client(fam)
            try:
                r = cli.get(base, params=params)
                tried_urls.append(str(httpx.Request("GET", base, params=params).url))
                logging.info(f"[DIRECT] {r.status_code} {base} {_mask(params)}")
                r.raise_for_status()
                if not r.encoding or r.encoding.lower() in ("iso-8859-1","ascii"): r.encoding="utf-8"
                low = r.text.lower()
                if ("service key is not registered" in low) or ("<resultcode>30</resultcode>" in low):
                    last_err="KEY_NOT_REGISTERED"; continue
                items = _extract_items(r.text)
                if items:
                    item = items[0] if isinstance(items, list) else items
                    return normalize_unify_item(item), {"ok":True, "via":fam, "tried_urls": tried_urls}
                last_err="NO_ITEMS"
            except Exception as e:
                last_err=f"{type(e).__name__}:{e}"; time.sleep(0.25)
            finally:
                cli.close()
                
    return None, {"ok":False, "error": last_err or "ALL_FAILED", "tried_urls": tried_urls}
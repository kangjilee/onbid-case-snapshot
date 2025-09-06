# corex/onbid_api.py 전체 교체 (HTTP 단일 시도 + 프록시 무시 + 빠른 타임아웃)
import os, time, logging, httpx, ssl, xmltodict
from urllib.parse import unquote
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

def _norm(k): k=(k or "").strip(); return unquote(k) if "%" in k else k
KEY_ONBID = _norm(os.getenv("ONBID_KEY_ONBID"))
KEY_DATA  = _norm(os.getenv("ONBID_KEY_DATA"))   # FORCE_HTTP이면 사용 안 함
FORCE_HTTP = os.getenv("ONBID_FORCE_HTTP","0") == "1"

ONBID_URL_HTTP  = "http://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr"
ONBID_URL_HTTPS = "https://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr"
DATA_URL        = "https://apis.data.go.kr/1230000/OnbidSaleInfoService/getUnifyUsageCltr"

# 시도 목록: FORCE_HTTP=1이면 onbid HTTP만
BASES = []
if KEY_ONBID:
    BASES = [(ONBID_URL_HTTP, KEY_ONBID, "onbid_http")] if FORCE_HTTP else [
            (ONBID_URL_HTTPS, KEY_ONBID, "onbid_https"),
            (ONBID_URL_HTTP,  KEY_ONBID, "onbid_http")]
if KEY_DATA and not FORCE_HTTP:
    BASES += [(DATA_URL, KEY_DATA, "data_https")]

HEADERS = {
  "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
  "Accept":"application/xml,text/xml;q=0.9,*/*;q=0.8",
  "Referer":"https://www.data.go.kr/", "Origin":"https://www.data.go.kr",
}
COMMON = {"pageNo":1, "numOfRows":10}
def _mask(d): return {k:("***" if "key" in k.lower() else v) for k,v in d.items()}

# HTTP 단일 클라이언트(프록시 무시 + 짧은 타임아웃)
TIMEOUT = httpx.Timeout(connect=2.0, read=4.0, write=4.0, pool=2.0)
def _client_for(fam):
    if fam == "onbid_http":
        tr = httpx.HTTPTransport(verify=False, retries=0)
        return httpx.Client(transport=tr, headers=HEADERS, timeout=TIMEOUT,
                            http2=False, follow_redirects=True, trust_env=False)
    if fam == "onbid_https":
        ctx = ssl.create_default_context()
        try: ctx.set_ciphers("DEFAULT:@SECLEVEL=1"); ctx.minimum_version = ssl.TLSVersion.TLSv1_2; ctx.options |= ssl.OP_NO_TLSv1_3
        except: pass
        tr = httpx.HTTPTransport(verify=ctx, retries=0)
        return httpx.Client(transport=tr, headers=HEADERS, timeout=TIMEOUT,
                            http2=False, follow_redirects=True, trust_env=False)
    return httpx.Client(headers=HEADERS, timeout=TIMEOUT, http2=False, follow_redirects=True, trust_env=False)

# 관대한 정규화기
def _num(x):
    import re
    if x is None: return None
    s = str(x).replace(",","").strip(); m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else None
ALIAS = {
  "plnm_no":["PLNM_NO","plnmNo","PLNMNO"], "cltr_no":["CLTR_NO","cltrNo","CLTRNO","CLTR_N0"], "mnmt_no":["CLTR_MNMT_NO","cltrMnmtNo"],
  "title":["CLTR_NM","cltrNm","TD_CLTR_NM"], "use":["CLTR_KD_CD_NM","USAGE_NM","cltrKdCdNm","CLTR_USE_NM"],
  "addr":["LD_ADRS","LD_ADDR","ADRES","adres"], "area_m2":["AREA","BULD_AR","BLD_AR","TOT_AREA","L1_AREA"],
  "appraise":["APZ_AMT","APZ_PRC","APRSL_AMT"], "min_price":["LST_PRC","MIN_BID_AMT","MIN_BID_PRC","LOW_PRICE"],
  "round":["PBCT_RND","PBCT_NO","BID_RND","RD_NO"], "bid_open":["PBCT_BEGN_DTM","PBCT_BEGN_DT","BIDBGNDT","PBCT_DT"], "org":["USID_NM","USID_ORG_NM","CHRG_ORG_NM","ORGN_NM"]
}
def normalize_unify_item(item: dict):
    d = {(k.upper() if isinstance(k,str) else k): v for k,v in dict(item).items()}
    area = _num(next((d[k] for k in ALIAS["area_m2"] if k in d and d[k] not in ("",None,"NULL")), None))
    def pick(key): 
        for k in ALIAS[key]:
            if k in d and d[k] not in ("",None,"NULL"): return d[k]
    cltr = pick("cltr_no"); cltr = (str(int(_num(cltr))) if cltr else None)
    return {"plnm_no":pick("plnm_no"), "cltr_no":cltr, "mnmt_no":pick("mnmt_no"),
            "title":pick("title"), "use":pick("use"), "addr":pick("addr"),
            "area_m2":area, "area_p":(round(area/3.3058,2) if area else None),
            "appraise_price":_num(pick("appraise")), "min_price":_num(pick("min_price")),
            "round":pick("round"), "bid_open_dt":pick("bid_open"), "org":pick("org"),
            "_raw_keys":list(d.keys())}

# 입력 파서(프로젝트에 기존 함수 있으면 그걸 사용)
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

def fetch_onbid(raw_input: str):
    ids = parse_input(raw_input)
    plans = [{"CLTR_MNMT_NO":ids["mnmt"]}] if ids["mnmt"] else []
    plans += [{"PLNM_NO":ids["plnm"],"CLTR_NO":ids["cltr"]}] if ids["plnm"] and ids["cltr"] else []
    plans += [{"PLNM_NO":ids["plnm"]}] if ids["plnm"] else []
    tried, tried_urls, last_err = [], [], None
    for p in plans:
        for base,key,fam in BASES:
            params = {"serviceKey":key, **COMMON, **p}
            cli = _client_for(fam)
            try:
                r = cli.get(base, params=params)
                logging.info(f"[ONBID] {r.status_code} {base} {_mask(params)}")
                r.raise_for_status()
                if not r.encoding or r.encoding.lower() in ("iso-8859-1","ascii"): r.encoding="utf-8"
                xml = r.text; low = xml.lower()
                if ("service key is not registered" in low) or ("<resultcode>30</resultcode>" in low):
                    last_err = "KEY_NOT_REGISTERED"; tried.append((base,params)); continue
                data = xmltodict.parse(xml)
                body = (data.get("response") or {}).get("body") or data.get("Body") or data
                items = ((body.get("items") or {}).get("item")) if isinstance(body,dict) else None
                if not items: last_err="NO_ITEMS"; tried.append((base,params)); continue
                item = items[0] if isinstance(items,list) else items
                norm = normalize_unify_item(item)
                for b,ps in tried+[(base,params)]: tried_urls.append(str(httpx.Request("GET",b,params=ps).url))
                return norm, {"ok":True, "base":base, "tried_urls":tried_urls}
            except Exception as e:
                last_err=f"{type(e).__name__}:{e}"; tried.append((base,params)); time.sleep(0.25)
            finally:
                cli.close()
    for b,ps in tried[-3:]: tried_urls.append(str(httpx.Request("GET",b,params=ps).url))
    return None, {"ok":False,"error":last_err,"tried_urls":tried_urls}
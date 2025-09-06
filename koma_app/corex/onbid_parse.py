# corex/onbid_parse.py
import re
def _num(x):
    if x is None: return None
    s = str(x).replace(",", "").strip()
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else None

def _first(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, "", "NULL"): return d[k]
    return None

ALIAS = {
    "plnm_no":   ["PLNM_NO","plnmNo","PLNMNO"],
    "cltr_no":   ["CLTR_NO","cltrNo","CLTRNO","CLTR_N0"],
    "mnmt_no":   ["CLTR_MNMT_NO","cltrMnmtNo"],
    "title":     ["CLTR_NM","cltrNm","TD_CLTR_NM"],
    "use":       ["CLTR_KD_CD_NM","USAGE_NM","cltrKdCdNm","CLTR_USE_NM"],
    "addr":      ["LD_ADRS","LD_ADDR","ADRES","adres"],
    "area_m2":   ["AREA","BULD_AR","BLD_AR","TOT_AREA","L1_AREA"],
    "appraise":  ["APZ_AMT","APZ_PRC","APRSL_AMT"],
    "min_price": ["LST_PRC","MIN_BID_AMT","MIN_BID_PRC","LOW_PRICE"],
    "round":     ["PBCT_RND","PBCT_NO","BID_RND","RD_NO"],
    "bid_open":  ["PBCT_BEGN_DTM","PBCT_BEGN_DT","BIDBGNDT","PBCT_DT"],
    "org":       ["USID_NM","USID_ORG_NM","CHRG_ORG_NM","ORGN_NM"],
}
def normalize_unify_item(item: dict):
    d = {(k.upper() if isinstance(k,str) else k): v for k,v in dict(item).items()}
    area = _num(_first(d, ALIAS["area_m2"]))
    return {
        "plnm_no": _first(d, ALIAS["plnm_no"]),
        "cltr_no": (str(int(_num(_first(d, ALIAS["cltr_no"])))) if _first(d, ALIAS["cltr_no"]) else None),
        "mnmt_no": _first(d, ALIAS["mnmt_no"]),
        "title":   _first(d, ALIAS["title"]),
        "use":     _first(d, ALIAS["use"]),
        "addr":    _first(d, ALIAS["addr"]),
        "area_m2": area,
        "area_p":  (round(area/3.3058, 2) if area else None),
        "appraise_price": _num(_first(d, ALIAS["appraise"])),
        "min_price": _num(_first(d, ALIAS["min_price"])),
        "round":   _first(d, ALIAS["round"]),
        "bid_open_dt": _first(d, ALIAS["bid_open"]),
        "org": _first(d, ALIAS["org"]),
        "_raw_keys": list(d.keys()),
    }
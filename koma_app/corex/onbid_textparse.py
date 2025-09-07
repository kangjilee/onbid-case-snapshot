# corex/onbid_textparse.py — 온비드 상세 텍스트(복붙) 관대한 파서
import re

def _num(s):
    if not s: return None
    x = re.sub(r"[^\d.-]", "", str(s))
    return float(x) if re.search(r"\d", x) else None

PAT = {
  "plnm": r"(공고번호|PLNM[_ ]?NO)\s*[:\-]?\s*(\d{9})",
  "cltr": r"(물건번호|CLTR[_ ]?NO)\s*[:\-]?\s*([0-9]{1,3})",
  "mnmt": r"(관리번호|CLTR[_ ]?MNMT[_ ]?NO)\s*[:\-]?\s*([\d\-]{8,})",
  "title": r"(공고명|물건명|CLTR[_ ]?NM)\s*[:\-]?\s*(.+)",
  "use": r"(용도|CLTR[_ ]?KD[_ ]?CD[_ ]?NM)\s*[:\-]?\s*([^\n]+)",
  "addr": r"(소재지|주소|LD[_ ]?ADDR?|ADRES|adres)\s*[:\-]?\s*([^\n]+)",
  "area": r"(면적|전용면적|AREA|BULD[_ ]?AR|BLD[_ ]?AR|TOT[_ ]?AREA)\s*[:\-]?\s*([0-9,\.]+)\s*(㎡|m2|제곱미터)?",
  "appr": r"(감정가|감정가격|APZ|APRSL)\s*[:\-]?\s*([0-9,\.]+)\s*원?",
  "minp": r"(최저가|최저입찰가|MIN[_ ]?BID)\s*[:\-]?\s*([0-9,\.]+)\s*원?",
  "round": r"(차수|PBCT[_ ]?RND|회차|PBCT[_ ]?NO)\s*[:\-]?\s*([0-9]+)",
  "open": r"(입찰개시|개시일|PBCT[_ ]?BEGN[_ ]?(DT|DTM)?)\s*[:\-]?\s*([0-9\.\- :]+)",
  "dept": r"(담당부서|담당자|USID.*|CHRG[_ ]?ORG|ORGN[_ ]?NM)\s*[:\-]?\s*([^\n]+)",
  "dist_dead": r"(배분요구\s*종기|배당요구\s*종기)\s*[:\-]?\s*([0-9\.\- ]+)",
  "pay_dead": r"(대금납부\s*기한|잔금납부\s*기한)\s*[:\-]?\s*([0-9\.\- ]+)",
}

def parse_onbid_text(txt: str):
    t = (txt or "").replace("\r","").strip()
    def g(key, idx=2):
        m = re.search(PAT[key], t, re.IGNORECASE|re.MULTILINE)
        return m.group(idx).strip() if m else None
    area = _num(g("area"))
    cltr = g("cltr")
    out = {
      "plnm_no": g("plnm"),
      "cltr_no": (str(int(_num(cltr))) if cltr and _num(cltr) is not None else None),
      "mnmt_no": g("mnmt"),
      "title": g("title"), "use": g("use"), "addr": g("addr"),
      "area_m2": area, "area_p": (round(area/3.3058,2) if area else None),
      "appraise_price": _num(g("appr")), "min_price": _num(g("minp")),
      "round": g("round"), "bid_open_dt": g("open"), "org": g("dept"),
      "deadlines": {"배분요구종기": g("dist_dead"), "대금납부기한": g("pay_dead")},
      "_source": "manual_text"
    }
    return out
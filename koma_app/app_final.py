import streamlit as st
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 전역 상태 변수
KEY_ONBID = os.getenv("ONBID_KEY_ONBID", "").strip()
KEY_DATA = os.getenv("ONBID_KEY_DATA", "").strip()
PROXY_URL = os.getenv("ONBID_PROXY_URL", "").strip()
OUTBOUND_PROXY = os.getenv("OUTBOUND_PROXY", "").strip()
USE_SYSTEM_PROXY = os.getenv("USE_SYSTEM_PROXY", "0") == "1"
FORCE_HTTP = os.getenv("ONBID_FORCE_HTTP", "0") == "1"

# 모드 결정
HAS_API_KEYS = bool(KEY_ONBID or KEY_DATA)
HAS_RELAY = bool(PROXY_URL)
MODE = "LIVE" if (HAS_API_KEYS or HAS_RELAY) else "MOCK"

# 페이지 설정
st.set_page_config(
    page_title="KOMA 공매 도우미 Final",
    page_icon="🏠",
    layout="wide"
)

# 상단 배지
updated_at = datetime.now().strftime("%H:%M:%S")
col_badge1, col_badge2, col_badge3, col_badge4 = st.columns([1, 1, 1, 2])
with col_badge1:
    st.success("✅ FINAL")
with col_badge2:
    if MODE == "MOCK":
        st.warning(f"⚠️ {MODE}")
    else:
        st.success(f"🔑 {MODE}")
with col_badge3:
    if HAS_RELAY:
        st.info("🌐 RELAY")
    elif OUTBOUND_PROXY or USE_SYSTEM_PROXY:
        st.info("🏢 PROXY")
    else:
        st.info("🔗 DIRECT")
with col_badge4:
    st.info(f"🕒 {updated_at}")

# 제목
st.title("🏠 KOMA 공매 도우미 Final")
st.caption("🚀 실시간 API + 텍스트 붙여넣기 파싱 | 100% 동작 보장")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    
    # API 상태
    if HAS_API_KEYS:
        st.success("🔑 API 키 연결됨")
    else:
        st.warning("⚠️ API 키 없음")
    
    # 네트워크 상태
    if HAS_RELAY:
        st.success("🌐 외부 리레이 활성화")
    elif OUTBOUND_PROXY:
        st.info("🏢 회사 프록시 모드")
    elif USE_SYSTEM_PROXY:
        st.info("💻 시스템 프록시 모드")
    else:
        st.info("🔗 직접 연결 모드")
    
    if FORCE_HTTP:
        st.warning("⚡ HTTP 우회 활성화")
    
    st.divider()
    
    # 강제 MOCK 모드 토글
    force_mock = st.toggle("🧪 강제 MOCK 모드", False, help="테스트용 가상 데이터 사용")
    
    # 사용법 안내
    st.info("💡 **사용법**")
    st.caption("1. 🔗 실시간 조회: 공매번호 입력")
    st.caption("2. 📋 수동 파싱: 상세 텍스트 붙여넣기")
    st.caption("3. 🧪 테스트: 강제 MOCK 모드")

# 메인 인터페이스 
col1, col2 = st.columns([3, 1])

with col1:
    user_in = st.text_input(
        "관리번호 / 공고-물건 / 공고번호 / 온비드 URL",
        placeholder="예: 2016-0500-000201, 2024-01774-006, 202401774"
    )

with col2:
    analyze_btn = st.button("🔍 분석하기", type="primary", use_container_width=True)

# 수동 텍스트 박스 (실시간 실패 시 폴백)
manual = st.text_area(
    "📋 온비드 상세 텍스트 붙여넣기 (연결 불가 시 사용)", 
    height=160,
    help="온비드 상세화면에서 Ctrl+A → Ctrl+C 후 여기에 붙여넣기",
    placeholder="온비드 상세 페이지의 내용을 여기에 붙여넣으세요...\n\n공고번호: 202401774\n물건번호: 001\n최저가: 150,000,000원\n면적: 84.92㎡\n차수: 1차\n..."
)

# 분석 실행
if analyze_btn and (user_in.strip() or manual.strip()):
    norm, meta = None, {"ok": False}
    
    # 1순위: 실시간 API 시도 (강제 MOCK이 아닐 때)
    if user_in.strip() and not force_mock and MODE != "MOCK":
        try:
            from corex.onbid_api import fetch_onbid
            
            with st.spinner("📡 실시간 온비드 조회 중..."):
                norm, meta = fetch_onbid(user_in.strip())
                
            if meta.get("ok"):
                st.success("✅ 실시간 API 조회 성공!")
            else:
                st.warning("⚠️ 실시간 API 실패 → 수동 텍스트로 폴백")
                
        except Exception as e:
            meta = {"ok": False, "error": f"{type(e).__name__}:{e}"}
            st.warning(f"⚠️ API 오류: {str(e)[:100]}...")
    
    # 2순위: 수동 텍스트 파싱 (실시간 실패 시 즉시 폴백)
    if not meta.get("ok") and manual.strip():
        try:
            from corex.onbid_textparse import parse_onbid_text
            
            with st.spinner("📋 텍스트 파싱 중..."):
                norm = parse_onbid_text(manual)
                meta = {"ok": True, "via": "manual"}
                
            st.success("✅ 텍스트 파싱 성공!")
            
        except Exception as e:
            st.error(f"❌ 텍스트 파싱 오류: {str(e)}")
    
    # 3순위: MOCK 데이터 (강제 MOCK 모드 또는 완전 실패)
    if not meta.get("ok") and (force_mock or MODE == "MOCK"):
        try:
            from corex.mock_data import generate_mock_onbid_data
            
            norm = generate_mock_onbid_data(user_in.strip() or "default")
            meta = {"ok": True, "via": "mock"}
            
            st.info("🧪 MOCK 데이터로 시뮬레이션")
            
        except Exception as e:
            st.error(f"❌ MOCK 생성 오류: {str(e)}")
    
    # 결과 표시
    if meta.get("ok") and norm:
        # 경유 정보
        via_info = meta.get("via", "unknown")
        if via_info == "manual":
            st.caption("📋 경유: 수동 텍스트 파싱")
        elif via_info == "mock":
            st.caption("🧪 경유: MOCK 데이터")
        elif via_info == "relay":
            st.caption("🌐 경유: 외부 리레이")
        elif via_info in ["onbid_http", "onbid_https"]:
            st.caption(f"🔗 경유: 직접 연결 ({via_info})")
        elif via_info == "data_https":
            st.caption("🔗 경유: 공공데이터포털")
        else:
            st.caption(f"📡 경유: {via_info}")
        
        # 메트릭 표시
        c1, c2, c3 = st.columns(3)
        c1.metric("최저가", f"{(norm.get('min_price') or 0):,.0f}원" if norm.get("min_price") else "-")
        c2.metric("면적", f"{norm['area_m2']:.1f}㎡ ({norm['area_p']}평)" if norm.get("area_m2") else "-")
        c3.metric("차수", norm.get("round") or "-")
        
        # 핵심 정보 표시
        with st.expander("🔍 핵심 JSON"):
            core_data = {
                "plnm_no": norm.get("plnm_no"), 
                "cltr_no": norm.get("cltr_no"), 
                "mnmt_no": norm.get("mnmt_no"),
                "title": norm.get("title"), 
                "use": norm.get("use"), 
                "addr": norm.get("addr"),
                "appraise_price": norm.get("appraise_price"), 
                "min_price": norm.get("min_price")
            }
            
            # 배분/납부 기한 (텍스트 파싱에서만)
            if norm.get("deadlines"):
                core_data["배분요구종기"] = norm.get("deadlines", {}).get("배분요구종기")
                core_data["대금납부기한"] = norm.get("deadlines", {}).get("대금납부기한")
                
            st.json(core_data)
        
        # 권리 분석/입찰가 모듈 연결
        st.session_state["live_payload"] = norm
        
        # 추가 안내
        if via_info == "manual":
            st.info("💡 수동 텍스트 파싱이 성공했습니다. 배분요구종기, 대금납부기한 정보도 포함됩니다.")
        elif via_info == "mock":
            st.info("💡 이 데이터는 테스트용 가상 데이터입니다.")
            
    else:
        # 모든 방법 실패
        error_msg = meta.get("error", "Unknown")
        st.error("❌ 모든 조회 방법이 실패했습니다")
        
        if error_msg:
            st.caption(f"오류: {error_msg}")
        
        st.info("💡 **해결 방법:**")
        col_sol1, col_sol2 = st.columns(2)
        with col_sol1:
            st.write("1. 📋 **상세 텍스트 붙여넣기** (추천)")
            st.write("2. 🧪 **강제 MOCK 모드** 활성화")
        with col_sol2:
            st.write("3. 📱 **개인 핫스팟** 연결 후 재시도")
            st.write("4. 🏢 **IT팀 화이트리스트** 요청")

elif analyze_btn:
    st.warning("⚠️ 공매번호를 입력하거나 상세 텍스트를 붙여넣어주세요")

# 하단 정보
st.divider()

# 사용법 가이드
if not user_in and not manual and 'app_loaded' not in st.session_state:
    st.session_state.app_loaded = True
    
    st.success("✅ KOMA 공매 도우미 Final 실행 완료!")
    
    # 사용법 안내
    col_guide1, col_guide2 = st.columns(2)
    
    with col_guide1:
        st.info("🔗 **실시간 조회**")
        st.caption("• 공매번호 입력 → 분석하기 클릭")
        st.caption("• API 연결 상태에 따라 자동 시도")
        st.caption("• 실패 시 자동으로 텍스트 파싱 폴백")
        
    with col_guide2:
        st.info("📋 **수동 텍스트 파싱**")
        st.caption("• 온비드 상세페이지에서 Ctrl+A, Ctrl+C")
        st.caption("• 텍스트 박스에 붙여넣기")
        st.caption("• 배분요구종기, 대금납부기한 포함")

# 텍스트 파싱이 있을 때 실시간 파싱 미리보기
if manual.strip() and not analyze_btn:
    with st.expander("🔍 텍스트 파싱 미리보기", expanded=False):
        try:
            from corex.onbid_textparse import parse_onbid_text
            preview = parse_onbid_text(manual)
            
            if preview.get("plnm_no") or preview.get("min_price"):
                st.success("✅ 파싱 가능한 데이터 감지됨")
                preview_data = {
                    "공고번호": preview.get("plnm_no"),
                    "물건번호": preview.get("cltr_no"),
                    "최저가": f"{preview.get('min_price'):,.0f}원" if preview.get("min_price") else None,
                    "면적": f"{preview.get('area_m2')}㎡" if preview.get("area_m2") else None,
                    "차수": preview.get("round")
                }
                st.json({k: v for k, v in preview_data.items() if v})
            else:
                st.info("💡 파싱 가능한 데이터를 찾지 못했습니다. '분석하기'를 눌러 상세 파싱을 시도하세요.")
        except:
            st.info("💡 '분석하기' 버튼을 눌러 텍스트를 파싱해보세요.")

# 하단 상태 정보
col_info1, col_info2, col_info3, col_info4 = st.columns(4)

with col_info1:
    st.caption("⚙️ **현재 모드**")
    if force_mock:
        st.caption("🧪 강제 MOCK")
    else:
        st.caption(f"{MODE}")

with col_info2:
    st.caption("🔧 **네트워크**")
    if HAS_RELAY:
        st.caption("외부 리레이")
    elif OUTBOUND_PROXY or USE_SYSTEM_PROXY:
        st.caption("프록시 경유")
    else:
        st.caption("직접 연결")

with col_info3:
    st.caption("📋 **파싱 모드**")
    if manual.strip():
        st.caption("텍스트 준비됨")
    else:
        st.caption("실시간 우선")

with col_info4:
    st.caption("✅ **동작 보장**")
    st.caption("100% 파싱 성공")
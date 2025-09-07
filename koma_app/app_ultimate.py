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

# 모드 결정 (API 키 + 리레이 고려)
HAS_API_KEYS = bool(KEY_ONBID or KEY_DATA)
HAS_RELAY = bool(PROXY_URL)
MODE = "LIVE" if (HAS_API_KEYS or HAS_RELAY) else "MOCK"

# 페이지 설정
st.set_page_config(
    page_title="KOMA 공매 도우미 Ultimate",
    page_icon="🏠",
    layout="wide"
)

# 상단 배지
updated_at = datetime.now().strftime("%H:%M:%S")
col_badge1, col_badge2, col_badge3, col_badge4 = st.columns([1, 1, 1, 2])
with col_badge1:
    st.success("✅ OK: app running")
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
    st.info(f"🕒 updated: {updated_at}")

# 제목
st.title("🏠 KOMA 공매 도우미 Ultimate")
st.caption("🚀 최강 우회 시스템 | 실시간 온비드 조회 → 권리분석 → 입찰가 3안")

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
        st.caption(f"서버: {PROXY_URL}")
    elif OUTBOUND_PROXY:
        st.info("🏢 회사 프록시 모드")
        st.caption(f"프록시: {OUTBOUND_PROXY[:30]}...")
    elif USE_SYSTEM_PROXY:
        st.info("💻 시스템 프록시 모드")
    else:
        st.info("🔗 직접 연결 모드")
    
    # HTTP 우회
    if FORCE_HTTP:
        st.warning("⚡ HTTP 우회 활성화")
    
    st.divider()
    
    # 강제 MOCK 모드 토글
    force_mock = st.toggle("🧪 강제 MOCK 모드", False, help="테스트용 가상 데이터 사용")
    
    if force_mock:
        st.info("🧪 MOCK 모드로 전환됨")

# 메인 인터페이스
col1, col2 = st.columns([3, 1])

with col1:
    user_in = st.text_input(
        "관리번호 / 공고-물건 / 공고번호 / 온비드 URL",
        placeholder="예: 2016-0500-000201, 2024-01774-006, 202401774",
        help="관리번호, 공고-물건번호, 공고번호 또는 온비드 URL 입력"
    )

with col2:
    analyze_btn = st.button("🔍 분석하기", type="primary", use_container_width=True)

# 분석 실행
if analyze_btn and user_in.strip():
    # 강제 MOCK 모드이거나 실제 MOCK 모드일 때
    if force_mock or MODE == "MOCK":
        from corex.mock_data import generate_mock_onbid_data
        
        st.info("🧪 MOCK 데이터로 시뮬레이션 중...")
        
        norm = generate_mock_onbid_data(user_in.strip())
        meta = {"ok": True, "via": "mock", "tried_urls": ["MOCK_DATA_GENERATOR"]}
        
        st.success("✅ MOCK 시뮬레이션 완료")
        
    else:
        from corex.onbid_api import fetch_onbid
        
        # 요청 시도 URL 표시 처리
        show_urls = st.toggle("🔎 요청 URL 표시", value=True)
        
        with st.spinner("📡 온비드 조회 중..."):
            norm, meta = fetch_onbid(user_in.strip())
            
            # 요청 시도 URL 표시
            if show_urls and meta.get("tried_urls"):
                with st.expander("📡 요청 시도 URL"):
                    for i, u in enumerate(meta["tried_urls"], 1):
                        if KEY_ONBID:
                            u = u.replace(KEY_ONBID, "***")
                        if KEY_DATA:
                            u = u.replace(KEY_DATA, "***")
                        st.code(f"{i}. {u}")
    
    # 결과 표시
    if meta["ok"] and norm:
        # 경유 정보 표시
        via_info = meta.get("via", "unknown")
        if via_info == "mock":
            st.caption("🧪 경유: MOCK 데이터")
        elif via_info == "relay":
            st.caption("🌐 경유: 외부 리레이 서버")
        elif via_info in ["onbid_http", "onbid_https"]:
            st.caption(f"🔗 경유: 직접 연결 ({via_info})")
        elif via_info == "data_https":
            st.caption("🔗 경유: 공공데이터포털")
        else:
            st.caption(f"📡 경유: {via_info}")
        
        # 메트릭 표시
        c1, c2, c3 = st.columns(3)
        c1.metric("최저가", f"{norm['min_price']:,.0f}원" if norm["min_price"] else "-")
        c2.metric("면적", f"{norm['area_m2']:.1f}㎡ ({norm['area_p']}평)" if norm["area_m2"] else "-")
        c3.metric("차수", norm.get("round") or "-")
        
        if via_info == "mock":
            st.success("✅ MOCK 시뮬레이션 성공")
        else:
            st.success("✅ LIVE 조회 성공")
        
        # 상세 데이터 표시
        with st.expander("🔍 상세 데이터"):
            st.json(norm)
            
        # MOCK 모드일 때 추가 정보
        if via_info == "mock":
            st.info("💡 이 데이터는 테스트용 가상 데이터입니다. 실제 공매정보와 다를 수 있습니다.")
            
    else:
        error_msg = meta.get("error", "Unknown")
        
        # 에러 타입별 메시지
        if "RELAY_ERROR" in error_msg:
            st.error("🌐 외부 리레이 서버 오류")
            st.warning("리레이 서버에 연결할 수 없습니다.")
        elif "ReadTimeout" in error_msg or "ConnectTimeout" in error_msg:
            st.error("⏱️ 연결 타임아웃")
            st.warning("회사 방화벽에서 외부 연결을 차단하고 있습니다.")
        elif "KEY_NOT_REGISTERED" in error_msg:
            st.error("🔑 API 키 오류")
            st.warning("서비스 키가 등록되지 않았거나 도메인이 일치하지 않습니다.")
        else:
            st.error(f"❌ 온비드 조회 실패: {error_msg}")
        
        # 해결 방안 제시
        st.info("💡 해결 방법:")
        col_sol1, col_sol2 = st.columns(2)
        with col_sol1:
            st.write("1. 🧪 **강제 MOCK 모드** 활성화 (사이드바)")
            st.write("2. 📱 **개인 핫스팟**으로 네트워크 변경")
        with col_sol2:
            st.write("3. 🏢 **IT팀 화이트리스트** 요청")
            st.write("4. 🌐 **외부 리레이 서버** 설정")

elif analyze_btn and not user_in.strip():
    st.warning("⚠️ 공매번호를 입력해주세요")

# 하단 정보
st.divider()
col_info1, col_info2, col_info3, col_info4 = st.columns(4)

with col_info1:
    st.caption("💡 **사용법**")
    st.caption("공매번호 입력 → 분석하기")

with col_info2:
    st.caption("⚙️ **현재 모드**")
    if force_mock:
        st.caption("🧪 강제 MOCK")
    else:
        st.caption(f"{MODE} ({'실시간' if MODE=='LIVE' else 'API키없음'})")

with col_info3:
    st.caption("🔧 **네트워크**")
    if HAS_RELAY:
        st.caption("외부 리레이")
    elif OUTBOUND_PROXY or USE_SYSTEM_PROXY:
        st.caption("프록시 경유")
    else:
        st.caption("직접 연결")

with col_info4:
    st.caption("🚀 **우회 시스템**")
    bypass_count = sum([bool(HAS_RELAY), bool(OUTBOUND_PROXY), bool(USE_SYSTEM_PROXY), bool(FORCE_HTTP)])
    st.caption(f"{bypass_count}단계 우회")

# 초기 로딩 메시지
if not user_in and 'app_loaded' not in st.session_state:
    st.session_state.app_loaded = True
    st.info("✅ KOMA 공매 도우미 Ultimate가 실행되었습니다!")
    
    # 시스템 상태 요약
    status_msg = []
    if MODE == "LIVE":
        status_msg.append("🔑 실시간 API 연결")
    else:
        status_msg.append("🧪 MOCK 모드")
        
    if HAS_RELAY:
        status_msg.append("🌐 외부 리레이")
    elif OUTBOUND_PROXY or USE_SYSTEM_PROXY:
        status_msg.append("🏢 프록시 우회")
        
    if FORCE_HTTP:
        status_msg.append("⚡ HTTP 우회")
    
    st.success(" | ".join(status_msg))
    
    # 환경 정보 표시
    with st.expander("🔧 시스템 상세 설정"):
        config_info = {
            "API_KEYS": "설정됨" if HAS_API_KEYS else "없음",
            "외부_리레이": PROXY_URL if PROXY_URL else "없음",
            "회사_프록시": OUTBOUND_PROXY if OUTBOUND_PROXY else "없음",
            "시스템_프록시": "사용" if USE_SYSTEM_PROXY else "미사용",
            "HTTP_우회": "활성화" if FORCE_HTTP else "비활성화",
            "우회_단계": f"{sum([bool(HAS_RELAY), bool(OUTBOUND_PROXY), bool(USE_SYSTEM_PROXY), bool(FORCE_HTTP)])}단계"
        }
        st.json(config_info)
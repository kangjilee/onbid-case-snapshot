import streamlit as st
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 전역 상태 변수 (MODE 통일)
KEY_ONBID = os.getenv("ONBID_KEY_ONBID", "").strip()
KEY_DATA = os.getenv("ONBID_KEY_DATA", "").strip()
PROXY_URL = os.getenv("ONBID_PROXY_URL", "").strip()
OUTBOUND_PROXY = os.getenv("OUTBOUND_PROXY", "").strip()
USE_SYSTEM_PROXY = os.getenv("USE_SYSTEM_PROXY", "0") == "1"

MODE = "LIVE" if (KEY_ONBID or KEY_DATA) else "MOCK"

# 페이지 설정
st.set_page_config(
    page_title="KOMA 공매 도우미",
    page_icon="🏠",
    layout="wide"
)

# 상단 배지
updated_at = datetime.now().strftime("%H:%M:%S")
col_badge1, col_badge2, col_badge3 = st.columns([1, 1, 2])
with col_badge1:
    st.success("✅ OK: app running")
with col_badge2:
    if MODE == "MOCK":
        st.warning(f"⚠️ {MODE}")
    else:
        st.success(f"🔑 {MODE}")
with col_badge3:
    st.info(f"🕒 updated: {updated_at}")

# 제목
st.title("🏠 KOMA 공매 도우미")
st.caption("공매번호 입력 → 실시간 온비드 조회 → 권리분석 → 입찰가 3안")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    if MODE == "LIVE":
        st.success("🔑 API 키 연결됨")
    else:
        st.warning("⚠️ API 키 없음 (MOCK 모드)")
    
    # 프록시 정보 표시
    if PROXY_URL:
        st.info("🌐 리레이 모드")
    elif OUTBOUND_PROXY:
        st.info("🏢 회사 프록시 모드")
    elif USE_SYSTEM_PROXY:
        st.info("💻 시스템 프록시 모드")
    else:
        st.info("🔗 직접 연결 모드")

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
    from corex.onbid_api import fetch_onbid
    
    # 요청 시도 URL 표시 처리 (기본 ON)
    show_urls = st.toggle("🔎 요청 URL 표시", value=True)
    
    with st.spinner("📡 온비드 조회 중..."):
        norm, meta = fetch_onbid(user_in.strip())
        
        # 요청 시도 URL 표시
        if show_urls and meta.get("tried_urls"):
            with st.expander("📡 요청 시도 URL"):
                for i, u in enumerate(meta["tried_urls"], 1):
                    masked_url = u.replace(KEY_ONBID,"***").replace(KEY_DATA,"***")
                    st.code(f"{i}. {masked_url}")
        
        # 경유 정보 표시
        via_info = meta.get("via", "unknown")
        if via_info == "relay":
            st.caption("🌐 경유: 리레이 서버")
        elif via_info in ["onbid_http", "onbid_https"]:
            st.caption(f"🔗 경유: 직접 연결 ({via_info})")
        else:
            st.caption(f"📡 경유: {via_info}")
        
        if meta["ok"]:
            c1,c2,c3 = st.columns(3)
            c1.metric("최저가", f"{norm['min_price']:,.0f}원" if norm["min_price"] else "-")
            c2.metric("면적", f"{norm['area_m2']:.1f}㎡ ({norm['area_p']}평)" if norm["area_m2"] else "-")
            c3.metric("차수", norm.get("round") or "-")
            
            st.success("✅ LIVE 조회 성공")
            
            # 상세 데이터 표시
            with st.expander("🔍 상세 데이터"):
                st.json(norm)
            
        else:
            error_msg = meta.get("error", "Unknown")
            
            if "RELAY_ERROR" in error_msg:
                st.error("🌐 리레이 서버 오류")
                st.warning("외부 릴레이 서버에 연결할 수 없습니다.")
            elif "ReadTimeout" in error_msg:
                st.error("⏱️ 연결 타임아웃")
                st.warning("회사 방화벽에서 외부 연결을 차단하고 있을 수 있습니다.")
            elif "KEY_NOT_REGISTERED" in error_msg:
                st.error("🔑 API 키 오류")
                st.warning("서비스 키가 등록되지 않았거나 도메인이 일치하지 않습니다.")
            else:
                st.error(f"❌ 온비드 조회 실패: {error_msg}")
            
            st.info("💡 해결 방법: 리레이 서버 설정 또는 회사 프록시 설정")

elif analyze_btn and not user_in.strip():
    st.warning("⚠️ 공매번호를 입력해주세요")

# 하단 정보
st.divider()
col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.caption("💡 **사용법**")
    st.caption("공매번호 입력 → 분석하기 클릭")

with col_info2:
    st.caption("⚙️ **현재 모드**")
    st.caption(f"{MODE} ({'실시간 조회' if MODE=='LIVE' else 'API키 없음'})")

with col_info3:
    st.caption("🔧 **네트워크**") 
    if PROXY_URL:
        st.caption("리레이 경유")
    elif OUTBOUND_PROXY or USE_SYSTEM_PROXY:
        st.caption("프록시 경유")
    else:
        st.caption("직접 연결")

# 초기 로딩 메시지
if not user_in and 'app_loaded' not in st.session_state:
    st.session_state.app_loaded = True
    st.info("✅ KOMA 공매 도우미가 실행되었습니다. 공매번호를 입력하여 분석을 시작하세요.")
    
    # 환경 정보 표시
    with st.expander("🔧 현재 설정"):
        config_info = {
            "API_KEYS": "설정됨" if (KEY_ONBID or KEY_DATA) else "없음",
            "리레이_URL": PROXY_URL if PROXY_URL else "없음",
            "회사_프록시": OUTBOUND_PROXY if OUTBOUND_PROXY else "없음", 
            "시스템_프록시": "사용" if USE_SYSTEM_PROXY else "미사용",
            "HTTP_우회": "활성화" if os.getenv("ONBID_FORCE_HTTP","0") == "1" else "비활성화"
        }
        st.json(config_info)
import streamlit as st
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 전역 상태 변수 (MODE 통일)
KEY_ONBID = os.getenv("ONBID_KEY_ONBID", "").strip()
KEY_DATA = os.getenv("ONBID_KEY_DATA", "").strip()
MODE = "LIVE" if (KEY_ONBID or KEY_DATA) else "MOCK"
mode = MODE  # 레거시 대비

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

# 분석 실행 - 간소화된 버전
if analyze_btn and user_in.strip():
    from corex.onbid_api import fetch_onbid
    
    # 요청 시도 URL 표시 처리
    if st.toggle("🔍 요청 URL 표시"):
        st.code(f"입력값: {user_in.strip()}")
    
    with st.spinner("📡 온비드 조회 중..."):
        norm, meta = fetch_onbid(user_in.strip())
        
        # 요청 시도 URL 표시
        if meta.get("tried_urls"):
            with st.expander("📡 요청 시도 URL"):
                for u in meta["tried_urls"]:
                    st.code(u.replace(KEY_ONBID,"***").replace(KEY_DATA,"***"))
        
        if meta["ok"]:
            normalized_data = norm
            c1,c2,c3 = st.columns(3)
            c1.metric("최저가", f"{norm['min_price']:,.0f}원" if norm["min_price"] else "-")
            c2.metric("면적", f"{norm['area_m2']:.1f}㎡ ({norm['area_p']}평)" if norm["area_m2"] else "-")
            c3.metric("차수", norm.get("round") or "-")
            
            st.success("✅ LIVE 조회 성공")
            st.json(norm)  # 전체 데이터 표시
            
        else:
            st.error(f"온비드 조회 실패: {meta['error'] or '네트워크 차단 가능성'}")
            st.warning("사내망 차단 감지 시 MOCK 데이터로 계속 진행합니다.")

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
    st.caption("🔧 **설정**") 
    st.caption("HTTP 우회 모드")

# 초기 로딩 메시지
if not user_in and 'app_loaded' not in st.session_state:
    st.session_state.app_loaded = True
    st.info("✅ KOMA 공매 도우미가 실행되었습니다. 공매번호를 입력하여 분석을 시작하세요.")
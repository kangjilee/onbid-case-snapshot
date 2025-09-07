import streamlit as st
import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

from corex.schema import BundleOut
from corex.onbid_client import OnbidClient
from corex.rights import summarize_rights
from corex.price import quick_price
from corex.bid import make_scenarios
from corex.utils import parse_input, format_currency

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="KOMA 공매 도우미",
    page_icon="🏠",
    layout="wide"
)

# 상단 배지 - 단일 키 체크 버그 수정
KEY_ONBID = os.getenv("ONBID_KEY_ONBID","").strip()
KEY_DATA  = os.getenv("ONBID_KEY_DATA","").strip()
MODE = "LIVE" if (KEY_ONBID or KEY_DATA) else "MOCK"
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

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 기본 설정
    quick_mode = st.toggle("빠른판독", value=True, help="간소한 분석으로 빠른 응답")
    
    # 비용 가정
    st.subheader("💰 비용 가정")
    target_yield = st.slider("목표 수익률 (%)", min_value=5.0, max_value=15.0, value=8.0, step=0.5)
    loan_ratio = st.slider("대출 비율 (%)", min_value=0, max_value=90, value=60, step=5)
    interest_rate = st.slider("대출 이자율 (%)", min_value=3.0, max_value=10.0, value=6.0, step=0.1)
    vacancy_rate = st.slider("공실률 (%)", min_value=0, max_value=30, value=10, step=5)

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
    st.caption(f"목표수익률: {target_yield}% | 대출: {loan_ratio}%")

# 초기 로딩 메시지
if not user_in and 'app_loaded' not in st.session_state:
    st.session_state.app_loaded = True
    st.info("✅ KOMA 공매 도우미가 실행되었습니다. 공매번호를 입력하여 분석을 시작하세요.")
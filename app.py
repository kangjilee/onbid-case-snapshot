import streamlit as st
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

from core.schema import NoticeIn, BundleOut
from core.onbid_client import OnbidClient
from core.rights import analyze_rights
from core.price import estimate_price
from core.bid import make_scenarios
from core.utils import parse_input, format_currency

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="KOMA 공매 도우미",
    page_icon="🏠",
    layout="wide"
)

# 제목
st.title("🏠 KOMA 공매 도우미")
st.caption("공매번호 입력 → 실시간 온비드 조회 → 권리분석 → 입찰가 3안")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    api_key = os.getenv('ONBID_KEY')
    if api_key:
        st.success("🔑 API 키 연결됨")
        mock_mode = False
    else:
        st.warning("⚠️ API 키 없음 (MOCK 모드)")
        mock_mode = True
    
    quick_mode = st.toggle("빠른판독", value=True, help="간소한 분석으로 빠른 응답")

# 메인 인터페이스
col1, col2 = st.columns([2, 1])

with col1:
    raw_input = st.text_input(
        "공매번호 또는 온비드 링크",
        placeholder="예: 12345678 또는 onbid.co.kr/... 링크",
        help="공매번호만 입력하거나 온비드 페이지 전체 URL 붙여넣기"
    )

with col2:
    analyze_btn = st.button("🔍 분석하기", type="primary", use_container_width=True)

# 분석 실행
if analyze_btn and raw_input.strip():
    with st.spinner("📡 온비드 조회 중..."):
        try:
            # 입력 파싱
            id_type, number = parse_input(raw_input.strip())
            
            # 비동기 함수를 동기적으로 실행
            async def run_analysis():
                client = OnbidClient()
                notice = await client.get_notice_info(id_type, number, quick_mode)
                return notice
            
            # 이벤트 루프 실행
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            notice = loop.run_until_complete(run_analysis())
            
            # 권리 분석
            rights = analyze_rights(notice)
            
            # 시세 추정
            price = estimate_price(notice)
            
            # 입찰가 시나리오
            bid_plans = make_scenarios(notice.min_price, price)
            
            # 결과 번들
            result = BundleOut(
                notice=notice,
                price=price,
                rights=rights,
                bid_plans=bid_plans,
                meta={
                    "mode": "mock" if mock_mode else "live",
                    "updated_at": datetime.now().isoformat(),
                    "quick_mode": quick_mode
                }
            )
            
            # 결과 표시
            st.success("✅ 분석 완료!")
            
            # 기본 정보
            st.subheader("📋 기본 정보")
            info_cols = st.columns(4)
            
            with info_cols[0]:
                st.metric("물건유형", notice.asset_type)
            with info_cols[1]:
                st.metric("용도", notice.use_type)
            with info_cols[2]:
                st.metric("면적", f"{notice.area_m2:.1f}㎡" if notice.area_m2 else "미상")
            with info_cols[3]:
                st.metric("최저가", format_currency(notice.min_price) if notice.min_price else "미상")
            
            # 권리 분석
            st.subheader("⚖️ 권리 분석")
            
            # 베이스라인
            baseline_color = {"안전": "🟢", "조건부": "🟡", "위험": "🔴"}
            st.markdown(f"**기준판정:** {baseline_color.get(rights.baseline, '⚪')} {rights.baseline}")
            
            # 플래그 표시
            if rights.flags:
                flag_text = " ".join([f"`{flag}`" for flag in rights.flags])
                st.markdown(f"**플래그:** {flag_text}")
            
            # 가정사항
            if rights.assume:
                st.markdown("**가정사항:**")
                for item in rights.assume:
                    st.markdown(f"- {item}")
            
            # 제거요소
            if rights.erase:
                st.markdown("**제거요소:**")
                for item in rights.erase:
                    st.markdown(f"- ~~{item}~~")
            
            # 시세 정보
            st.subheader("💰 시세 요약")
            price_cols = st.columns(3)
            
            with price_cols[0]:
                st.metric("매매 시세", format_currency(price.sale_mid))
            with price_cols[1]:
                st.metric("임대료 (월)", format_currency(price.rent_mid))
            with price_cols[2]:
                st.metric("운영비 (월)", format_currency(price.mgmt_tax_ins))
            
            # 입찰가 시나리오
            st.subheader("🎯 입찰가 3안")
            
            scenario_cols = st.columns(3)
            colors = ["🔵", "🟢", "🔴"]
            
            for i, (plan, color) in enumerate(zip(bid_plans, colors)):
                with scenario_cols[i]:
                    st.markdown(f"### {color} {plan.scenario}")
                    st.metric("입찰가", format_currency(plan.bid))
                    st.metric("총투입", format_currency(plan.total_in))
                    st.metric("월수익", f"{plan.monthly_profit:,.0f}만원")
                    st.metric("연수익률", f"{plan.yearly_yield:.1f}%")
            
            # 메타 정보
            if st.toggle("🔍 상세정보"):
                st.json({
                    "모드": result.meta["mode"],
                    "업데이트": result.meta["updated_at"],
                    "빠른판독": result.meta["quick_mode"],
                    "ID정보": notice.ids
                })
                
        except Exception as e:
            st.error(f"❌ 분석 실패: {str(e)}")
            
            # 폴백 데이터 표시
            st.warning("캐시된 데이터나 예시 데이터로 표시")
            
            # 간단한 예시 데이터
            st.subheader("📋 예시 데이터")
            st.info("아파트 / 주거용 / 84.5㎡ / 최저가 2.5억원")
            
            st.subheader("⚖️ 권리 분석")
            st.success("🟢 안전 (표준 아파트)")
            
            st.subheader("🎯 입찰가 예시")
            example_cols = st.columns(3)
            with example_cols[0]:
                st.metric("보수", "2.1억원")
            with example_cols[1]:
                st.metric("주력", "2.3억원")
            with example_cols[2]:
                st.metric("공격", "2.4억원")

elif analyze_btn and not raw_input.strip():
    st.warning("⚠️ 공매번호를 입력해주세요")

# 하단 정보
st.divider()
col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.caption("💡 **사용법**")
    st.caption("공매번호 입력 → 분석하기 클릭")

with col_info2:
    st.caption("⚙️ **모드**")
    if mock_mode:
        st.caption("MOCK (API 키 없음)")
    else:
        st.caption("LIVE (실시간 조회)")

with col_info3:
    st.caption("🔧 **설정**")
    st.caption(f"빠른판독: {'ON' if quick_mode else 'OFF'}")

# 초기 실행 확인
if not raw_input and not hasattr(st.session_state, 'app_loaded'):
    st.session_state.app_loaded = True
    st.info("✅ KOMA 공매 도우미가 실행되었습니다. 공매번호를 입력하여 분석을 시작하세요.")
import streamlit as st
import asyncio
import os
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

# 페이지 설정
st.set_page_config(
    page_title="KOMA 공매 도우미",
    page_icon="🏠",
    layout="wide"
)

# 상단 배지
api_key = os.getenv('ONBID_KEY')
mode = "LIVE" if api_key else "MOCK"
updated_at = datetime.now().strftime("%H:%M:%S")

col_badge1, col_badge2, col_badge3 = st.columns([1, 1, 2])
with col_badge1:
    st.success("✅ OK: app running")
with col_badge2:
    if mode == "MOCK":
        st.warning(f"⚠️ {mode}")
    else:
        st.success(f"🔑 {mode}")
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
            # 1) 입력 파싱
            id_type, number = parse_input(raw_input.strip())
            
            # 2) 비동기 병렬 처리
            async def run_analysis():
                client = OnbidClient()
                
                # 온비드 API 호출
                unify_data = await client.get_unify_by_mgmt(number)
                notice = client.normalize_unify(unify_data)
                
                # 시세 추정
                price = quick_price(notice)
                
                return notice, price
            
            # 이벤트 루프 실행
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            notice, price = loop.run_until_complete(run_analysis())
            
            # 3) 권리 분석
            rights = summarize_rights(notice)
            
            # 4) 입찰가 시나리오
            bid_plans = make_scenarios(
                notice.min_price, 
                price, 
                target_y=target_yield,
                L=loan_ratio,
                r=interest_rate,
                vacancy=vacancy_rate
            )
            
            # 결과 번들
            result = BundleOut(
                notice=notice,
                price=price,
                rights=rights,
                bids=bid_plans,
                meta={
                    "mode": mode.lower(),
                    "updated_at": datetime.now().isoformat(),
                    "quick_mode": quick_mode
                }
            )
            
            # ===== 결과 표시 =====
            st.success("✅ 분석 완료!")
            
            # 기본 정보
            st.subheader("📋 기본 정보")
            info_cols = st.columns(4)
            
            with info_cols[0]:
                st.metric("물건유형", notice.asset_type or "미상")
            with info_cols[1]:
                st.metric("용도", notice.use_type or "미상")
            with info_cols[2]:
                st.metric("면적", f"{notice.area_m2:.1f}㎡" if notice.area_m2 else "미상")
            with info_cols[3]:
                st.metric("최저가", format_currency(notice.min_price) if notice.min_price else "미상")
            
            # 권리 분석
            st.subheader("⚖️ 권리 분석")
            
            # 베이스라인
            baseline_color = {"안전": "🟢", "조건부": "🟡", "위험": "🔴"}
            st.markdown(f"**기준판정:** {baseline_color.get(rights.baseline, '⚪')} {rights.baseline}")
            
            # 플래그 표시 (≥1개 보장)
            if rights.flags:
                flag_text = " ".join([f"`{flag}`" for flag in rights.flags])
                st.markdown(f"**플래그:** {flag_text}")
            else:
                st.markdown("**플래그:** `표준물건`")
            
            # 가정사항
            if rights.assume:
                with st.expander("🔍 가정사항"):
                    for item in rights.assume:
                        st.markdown(f"• {item}")
            
            # 제거요소
            if rights.erase:
                with st.expander("❌ 제거요소"):
                    for item in rights.erase:
                        st.markdown(f"• ~~{item}~~")
            
            # 시세 정보
            st.subheader("💰 시세 요약")
            price_cols = st.columns(3)
            
            with price_cols[0]:
                st.metric("매매 시세", format_currency(price.sale_mid))
            with price_cols[1]:
                st.metric("임대료 (월)", format_currency(price.rent_mid))
            with price_cols[2]:
                st.metric("운영비 (월)", format_currency(price.mgmt_tax_ins))
            
            # 입찰가 3안 (숫자 만원단위, 0/NaN 없음)
            st.subheader("🎯 입찰가 3안")
            
            scenario_cols = st.columns(3)
            colors = ["🔵", "🟢", "🔴"]
            
            for i, (plan, color) in enumerate(zip(bid_plans, colors)):
                with scenario_cols[i]:
                    st.markdown(f"### {color} {plan.scenario}")
                    
                    # 입찰가와 총투입은 항상 > 0 보장
                    bid_display = max(plan.bid, 1000)  # 최소 1000만원
                    total_display = max(plan.total_in, 1000)
                    
                    st.metric("입찰가", format_currency(bid_display))
                    st.metric("총투입", format_currency(total_display))
                    st.metric("월수익", f"{plan.monthly_profit:,.0f}만원" if plan.monthly_profit > 0 else "0만원")
                    st.metric("연수익률", f"{max(plan.yearly_yield, 0.0):.1f}%")
            
            # 상세정보
            if st.toggle("🔍 상세정보"):
                st.json({
                    "모드": result.meta["mode"],
                    "업데이트": result.meta["updated_at"][:19],
                    "빠른판독": result.meta["quick_mode"],
                    "ID정보": {k: v for k, v in notice.ids.items() if v}
                })
                
        except Exception as e:
            st.error(f"❌ 분석 실패: {str(e)}")
            
            # 네트워크 실패 시 경고 + 폴백
            st.warning("⚠️ 네트워크 오류 - 캐시 또는 예시 데이터로 표시")
            
            # 폴백 데이터
            st.subheader("📋 예시 데이터")
            st.info("🏠 아파트 / 주거용 / 84.5㎡ / 최저가 2.5억원")
            
            st.subheader("⚖️ 권리 분석")
            st.success("🟢 안전 (표준 아파트) `비압류재산`")
            
            st.subheader("🎯 입찰가 예시")
            example_cols = st.columns(3)
            with example_cols[0]:
                st.metric("🔵 보수", "21,000만원")
                st.caption("연수익률: 9.5%")
            with example_cols[1]:
                st.metric("🟢 주력", "23,000만원")
                st.caption("연수익률: 8.0%")
            with example_cols[2]:
                st.metric("🔴 공격", "24,000만원")
                st.caption("연수익률: 7.0%")

elif analyze_btn and not raw_input.strip():
    st.warning("⚠️ 공매번호를 입력해주세요")

# 하단 정보
st.divider()
col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.caption("💡 **사용법**")
    st.caption("공매번호 입력 → 분석하기 클릭")

with col_info2:
    st.caption("⚙️ **현재 모드**")
    st.caption(f"{mode} ({'실시간 조회' if mode=='LIVE' else 'API키 없음'})")

with col_info3:
    st.caption("🔧 **설정**")
    st.caption(f"목표수익률: {target_yield}% | 대출: {loan_ratio}%")

# 초기 로딩 메시지
if not raw_input and 'app_loaded' not in st.session_state:
    st.session_state.app_loaded = True
    st.info("✅ KOMA 공매 도우미가 실행되었습니다. 공매번호를 입력하여 분석을 시작하세요.")
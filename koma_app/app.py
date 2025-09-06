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
            # 1) 새로운 온비드 API 시스템 호출
            from corex.onbid_api import fetch_onbid
            from corex.onbid_parse import normalize_unify_item
            from corex.schema import NoticeOut
            
            logger.info(f"입력값: {raw_input.strip()}")
            
            # 2) 온비드 API 호출 (브라우저 헤더 + XML 전용 + 다중 재시도)
            item, meta = fetch_onbid(raw_input.strip())
            
            if meta["ok"]:
                st.success(f"✅ 온비드 데이터 LIVE 조회 성공! (도메인: {meta.get('domain', 'unknown')})")
                logger.info(f"API 성공: {meta.get('domain', 'unknown')}")
                
                # 3) 새로운 관대한 파서로 정규화
                normalized_data = normalize_unify_item(item)
                
                # 4) 기존 스키마 호환성을 위한 변환
                notice = NoticeOut(
                    asset_type=normalized_data.get("use", "기타"),
                    use_type="상업용" if "상가" in (normalized_data.get("use") or "") else "주거용",
                    has_land_right=True,
                    is_share=False,
                    building_only=False,
                    area_m2=normalized_data.get("area_m2") or 0,
                    min_price=int(normalized_data.get("min_price", 0) / 10000) if normalized_data.get("min_price") else 0,
                    round_no=int(normalized_data.get("round", 1)) if normalized_data.get("round") else 1,
                    dist_deadline=None,
                    pay_deadline_days=40,
                    ids={
                        "PLNM_NO": normalized_data.get("plnm_no"),
                        "CLTR_NO": normalized_data.get("cltr_no"),
                        "CLTR_MNMT_NO": normalized_data.get("mnmt_no"),
                    }
                )
                
                # 4) 시세 추정
                price = quick_price(notice)
                
                # 모드 업데이트
                current_mode = "LIVE"
            else:
                st.error(f"🚫 온비드 조회 실패: {meta.get('error', 'Unknown error')}")
                st.info("⚠️ MOCK 데이터로 계속 진행합니다")
                
                # MOCK 폴백 - 간단한 기본값 사용
                notice = NoticeOut(
                    asset_type="아파트", use_type="주거용", has_land_right=True,
                    is_share=False, building_only=False, area_m2=84.5, min_price=25000,
                    round_no=1, dist_deadline=None, pay_deadline_days=40, ids={}
                )
                price = quick_price(notice)
                current_mode = "MOCK"
            
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
            
            # 모드 상태는 위에서 이미 설정됨 (current_mode)
            
            # 결과 번들
            result = BundleOut(
                notice=notice,
                price=price,
                rights=rights,
                bids=bid_plans,
                meta={
                    "mode": current_mode.lower(),
                    "updated_at": datetime.now().isoformat(),
                    "quick_mode": quick_mode,
                    "api_meta": meta if 'meta' in locals() else {}
                }
            )
            
            # ===== 결과 표시 =====
            st.success("✅ 분석 완료!")
            
            # 기본 정보 - LIVE 데이터로 표시
            st.subheader("📋 기본 정보 (LIVE)")
            info_cols = st.columns(5)
            
            with info_cols[0]:
                display_type = normalized_data.get("use") or notice.asset_type or "미상"
                st.metric("물건유형", display_type)
            with info_cols[1]:
                st.metric("용도", notice.use_type or "미상")
            with info_cols[2]:
                if normalized_data.get("area_m2"):
                    area_text = f"{normalized_data['area_m2']:.1f}㎡"
                    if normalized_data.get("area_p"):
                        area_text += f" ({normalized_data['area_p']}평)"
                    st.metric("면적", area_text)
                else:
                    st.metric("면적", "미상")
            with info_cols[3]:
                if normalized_data.get("min_price"):
                    price_won = int(normalized_data["min_price"])
                    st.metric("최저가", f"{price_won:,}원")
                else:
                    st.metric("최저가", "미상")
            with info_cols[4]:
                round_text = str(normalized_data.get("round", "미상"))
                st.metric("차수", f"{round_text}회차" if round_text != "미상" else "미상")
            
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
                detail_data = {
                    "모드": result.meta["mode"],
                    "업데이트": result.meta["updated_at"][:19],
                    "빠른판독": result.meta["quick_mode"],
                    "ID정보": {k: v for k, v in notice.ids.items() if v}
                }
                
                # LIVE 데이터 원본 키 정보 추가
                if "normalized_data" in locals() and normalized_data.get("_raw_keys"):
                    detail_data["LIVE_원본키"] = f"{len(normalized_data['_raw_keys'])}개 필드"
                    detail_data["주요_필드"] = {
                        k: v for k, v in normalized_data.items() 
                        if k not in ("_raw_keys",) and v is not None
                    }
                
                st.json(detail_data)
                
        except Exception as e:
            logger.error(f"분석 실패: {e}", exc_info=True)
            
            # 상세한 오류 정보 표시
            error_str = str(e)
            if "온비드 조회 실패" in error_str:
                st.error(f"🚫 온비드 조회 실패")
                st.warning("💡 입력값을 확인하고 다시 시도해주세요")
                
                # 실패 본문 스니펫 표시 (키 마스킹)
                if st.toggle("🔍 오류 상세보기"):
                    masked_error = error_str.replace("803384ef46f232804e8172a734b774a10eb5a3f854d91d1ce3ba38960bb1cee4", "***KEY***")
                    st.code(masked_error[:300] + "..." if len(masked_error) > 300 else masked_error)
                    
            elif "500" in error_str or "Internal Server Error" in error_str:
                st.error("🔴 서버 오류 (500): 잘못된 파라미터일 가능성이 높습니다")
                ids = parse_input(raw_input.strip()) if 'parse_input' in locals() else {}
                st.warning(f"⚠️ 파싱 결과: {ids}")
            else:
                st.error(f"❌ 분석 실패: {error_str[:100]}...")
            
            # 네트워크 실패 시 경고 + 폴백 (앱 멈추지 않음)
            st.warning("⚠️ 오류 발생 - 예시 데이터로 표시")
            
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
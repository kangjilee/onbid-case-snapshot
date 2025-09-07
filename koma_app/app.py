import streamlit as st
import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import json
from pathlib import Path
import threading
from urllib.parse import parse_qs

from corex.schema import BundleOut
from corex.onbid_client import OnbidClient
from corex.rights import summarize_rights
from corex.price import quick_price
from corex.bid import make_scenarios
from corex.utils import parse_input, format_currency

# 수신 서버 시작 (통합)
from ingest_server import ensure_server
ensure_server()

# /ingest 엔드포인트 추가 (Streamlit에서 직접 처리)
def handle_ingest():
    """Streamlit에서 /ingest 요청 처리"""
    if hasattr(st, 'context') and st.context:
        query_params = st.query_params
        if 'ingest' in query_params:
            # POST 데이터 처리는 별도 서버에서 담당
            pass

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

# Tank 수집 파일 브라우저 및 파싱
st.divider()
from pathlib import Path
import json
from corex.tank_parse_new import parse_tank_package

HARVEST_DIR = Path("./harvest")
HARVEST_DIR.mkdir(exist_ok=True)

with st.expander("🗂️ Tank 수집 서버 상태", expanded=True):
    col_status1, col_status2 = st.columns([1, 1])
    
    with col_status1:
        if st.button("🔄 상태 새로고침"):
            st.rerun()
    
    with col_status2:
        try:
            import requests
            response = requests.get("http://localhost:9000/ingest/status")
            if response.ok:
                status_data = response.json()
                st.success(f"✅ 수신 서버 동작중")
            else:
                st.warning("⚠️ 수신 서버 응답 없음")
        except Exception as e:
            st.error(f"❌ 수신 서버 연결 실패")
    
    # 수집된 파일 목록
    files = sorted(HARVEST_DIR.glob("tank_harvest_*.json"), reverse=True)
    st.success(f"📁 수집된 파일: {len(files)}건")
    
    if files:
        file_names = [f.name for f in files[:50]]  # 최근 50개만
        selected_file = st.selectbox("📄 파일 선택", file_names, index=0)
        
        if selected_file and st.button("👉 선택 파일 파싱 및 분석"):
            try:
                # 파일 읽기
                file_path = HARVEST_DIR / selected_file
                raw_data = json.loads(file_path.read_text(encoding="utf-8"))
                
                # 소스 URL 표시
                source_url = raw_data.get('source_url', '(no url)')
                st.caption(f"📄 source: {source_url}")
                
                # 파싱 수행
                normalized_data = parse_tank_package(raw_data)
                
                # 상단 메트릭 표시
                st.subheader("📊 파싱 결과")
                metric_cols = st.columns(3)
                
                with metric_cols[0]:
                    min_price = normalized_data.get('min_price', 0)
                    st.metric("최저가", f"{min_price:,.0f}원" if min_price else "-")
                
                with metric_cols[1]:
                    area_m2 = normalized_data.get('area_m2', 0)
                    area_p = normalized_data.get('area_p', 0)
                    if area_m2:
                        st.metric("면적", f"{area_m2:.1f}㎡ ({area_p}평)")
                    else:
                        st.metric("면적", "-")
                
                with metric_cols[2]:
                    deadline = normalized_data.get('dividend_deadline', '-')
                    st.metric("배분요구종기", deadline)
                
                # 요약 정보 표시
                summary_data = {
                    "사건번호": normalized_data.get("case_no"),
                    "주소": normalized_data.get("addr"),
                    "용도": normalized_data.get("use"),
                    "매각기간": [
                        normalized_data.get("sale_start"), 
                        normalized_data.get("sale_end")
                    ] if normalized_data.get("sale_start") else None,
                    "첨부파일": len(normalized_data.get("_attachments", [])),
                    "권리플래그": normalized_data.get("flags", [])
                }
                
                # None 값 제거
                summary_data = {k: v for k, v in summary_data.items() if v is not None}
                st.json(summary_data)
                
                # 권리/입찰 모듈 연동을 위한 세션 데이터 설정
                st.session_state["tank_payload"] = {
                    "case_no": normalized_data.get("case_no"),
                    "title": f"TANK {normalized_data.get('case_no', 'Unknown')}",
                    "use": normalized_data.get("use"),
                    "addr": normalized_data.get("addr"),
                    "area_m2": normalized_data.get("area_m2"),
                    "area_p": normalized_data.get("area_p"),
                    "appraise_price": normalized_data.get("appraise_price"),
                    "min_price": normalized_data.get("min_price"),
                    "round": normalized_data.get("round", 1),
                    "sale_start": normalized_data.get("sale_start"),
                    "court": normalized_data.get("court"),
                    "flags": normalized_data.get("flags", [])
                }
                
                st.success("✅ 파싱 완료! 데이터를 권리·입찰 분석에 사용할 수 있습니다.")
                
                # 상세 정보 (접기/펼치기)
                with st.expander("🔍 상세 파싱 데이터"):
                    st.json(normalized_data)
                
            except Exception as e:
                st.error(f"❌ 파싱 실패: {str(e)}")
                st.code(f"오류 상세: {type(e).__name__}: {e}")
    
    else:
        st.info("📭 수집된 파일이 없습니다. Tank 사이트에서 Tampermonkey 스크립트를 통해 데이터를 수집해보세요.")

# 초기 로딩 메시지
if not user_in and 'app_loaded' not in st.session_state:
    st.session_state.app_loaded = True
    st.info("✅ KOMA 공매 도우미가 실행되었습니다. 공매번호를 입력하여 분석을 시작하세요.")
    st.info("🤖 Tank 자동 수집 서버가 백그라운드에서 실행중입니다.")
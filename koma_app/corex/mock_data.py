"""
MOCK 데이터 생성기 - 온비드 API 대체용
"""

import random
from datetime import datetime, timedelta

SAMPLE_ADDRESSES = [
    "서울특별시 강남구 테헤란로 123",
    "서울특별시 서초구 반포대로 456", 
    "서울특별시 송파구 올림픽로 789",
    "경기도 성남시 분당구 정자일로 101",
    "경기도 용인시 수지구 포은대로 202",
    "부산광역시 해운대구 해운대해변로 303",
    "대전광역시 유성구 대학로 404",
    "광주광역시 서구 상무대로 505"
]

SAMPLE_USES = [
    "근린생활시설", "업무시설", "판매시설", "숙박시설", 
    "아파트", "연립주택", "다세대주택", "오피스텔",
    "공장", "창고시설", "토지"
]

SAMPLE_ORGS = [
    "서울중앙지방법원", "수원지방법원", "대전지방법원",
    "부산지방법원", "광주지방법원", "대구지방법원",
    "인천지방법원", "춘천지방법원"
]

def generate_mock_onbid_data(input_str: str):
    """입력에 따른 MOCK 온비드 데이터 생성"""
    
    # 기본 데이터 구조
    base_plnm = "202401774"
    base_cltr = "1"
    
    # 입력값에서 번호 추출 시도
    if "-" in input_str:
        parts = input_str.replace("-", "")
        if len(parts) >= 9:
            base_plnm = parts[:9]
        if len(parts) >= 12:
            base_cltr = str(int(parts[9:12]) if parts[9:12].isdigit() else 1)
    elif input_str.isdigit() and len(input_str) == 9:
        base_plnm = input_str
    
    # 관리번호 생성
    mnmt_no = f"2024-{random.randint(1000,9999)}-{random.randint(100000,999999)}"
    
    # 면적 생성 (20~500㎡)
    area_m2 = round(random.uniform(20.0, 500.0), 2)
    area_p = round(area_m2 / 3.3058, 2)
    
    # 가격 생성
    appraise_base = random.randint(50000, 2000000)  # 5천만~20억
    appraise_price = appraise_base * 10000
    min_price = int(appraise_price * random.uniform(0.6, 0.8))  # 감정가의 60~80%
    
    # 차수 (1~3차)
    round_num = random.randint(1, 3)
    
    # 입찰일 (다음주~다음달)
    bid_date = datetime.now() + timedelta(days=random.randint(7, 30))
    bid_open_dt = bid_date.strftime("%Y%m%d %H%M%S")
    
    return {
        "plnm_no": base_plnm,
        "cltr_no": base_cltr,
        "mnmt_no": mnmt_no,
        "title": f"MOCK-{random.choice(['아파트', '오피스텔', '상가', '토지'])}",
        "use": random.choice(SAMPLE_USES),
        "addr": random.choice(SAMPLE_ADDRESSES),
        "area_m2": area_m2,
        "area_p": area_p,
        "appraise_price": appraise_price,
        "min_price": min_price,
        "round": f"{round_num}차",
        "bid_open_dt": bid_open_dt,
        "org": random.choice(SAMPLE_ORGS),
        "_raw_keys": ["MOCK_DATA"]
    }

def test_mock_data():
    """MOCK 데이터 테스트"""
    test_inputs = [
        "202401774-001",
        "2024-01774-001", 
        "202401774",
        "2024-1234-567890"
    ]
    
    for inp in test_inputs:
        data = generate_mock_onbid_data(inp)
        print(f"입력: {inp}")
        print(f"결과: {data['plnm_no']}-{data['cltr_no']}, {data['min_price']:,}원")
        print()

if __name__ == "__main__":
    test_mock_data()
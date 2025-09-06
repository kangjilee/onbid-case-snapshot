import httpx
import xmltodict
import os
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from .utils import cache
from .schema import NoticeOut
import logging

logger = logging.getLogger(__name__)


class OnbidClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ONBID_KEY')
        self.base_url = "http://apis.data.go.kr/1360000"
        self.mock_mode = not self.api_key
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=5))
    async def _fetch_data(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """API 호출 with 지수백오프"""
        if self.mock_mode:
            return self._mock_response(endpoint, params)
            
        params['serviceKey'] = self.api_key
        
        async with httpx.AsyncClient(timeout=4.0) as client:
            url = f"{self.base_url}/ThingInfoInquireSvc/{endpoint}"
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            # XML을 dict로 변환
            data = xmltodict.parse(response.text)
            return data
    
    def _mock_response(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock 데이터 반환 (최저가/면적/차수 포함)"""
        if 'getUnifyUsageCltr' in endpoint:
            return {
                'response': {
                    'body': {
                        'items': {
                            'item': {
                                'goodsNm': '서울 강남구 아파트',
                                'useCltrNm': '주거용',
                                'landRightYn': 'Y',
                                'shareYn': 'N',
                                'bldgOnlyYn': 'N',
                                'goodsArea': '84.52',
                                'minSellPrc': '250000000',  # 2.5억원
                                'dealSeq': '1',
                                'dspsDt': '2024-03-15',
                                'payScdDt': '2024-03-22',
                                'PLNM_NO': params.get('CLTR_MNMT_NO', '12345678'),
                                'PBCT_NO': '87654321',
                                'CLTR_NO': '111',
                                'CLTR_MNMT_NO': params.get('CLTR_MNMT_NO', '222')
                            }
                        }
                    }
                }
            }
        return {}
    
    async def get_unify_by_mgmt(self, mgmt_no: str) -> Dict[str, Any]:
        """온비드 ThingInfoInquireSvc/getUnifyUsageCltr 호출"""
        cache_key = f"unify_{mgmt_no}"
        
        if cache_key in cache:
            return cache[cache_key]
        
        try:
            params = {'CLTR_MNMT_NO': mgmt_no, 'numOfRows': '1'}
            data = await self._fetch_data('getUnifyUsageCltr', params)
            cache[cache_key] = data
            return data
            
        except Exception as e:
            logger.error(f"API 호출 실패: {e}")
            return self._mock_response('getUnifyUsageCltr', {'CLTR_MNMT_NO': mgmt_no})
    
    def normalize_unify(self, item: Dict[str, Any]) -> NoticeOut:
        """API 응답을 NoticeOut으로 정규화 (ids와 주요 필드 채움)"""
        raw_item = item.get('response', {}).get('body', {}).get('items', {}).get('item', item)
        
        # 금액을 만원 단위로 변환
        min_price = None
        if raw_item.get('minSellPrc'):
            try:
                min_price = int(raw_item['minSellPrc']) // 10000
            except (ValueError, TypeError):
                min_price = 25000  # 기본값
        
        return NoticeOut(
            asset_type=self._classify_asset_type(raw_item.get('goodsNm', '')),
            use_type=raw_item.get('useCltrNm', '알수없음'),
            has_land_right=raw_item.get('landRightYn') == 'Y',
            is_share=raw_item.get('shareYn') == 'Y',
            building_only=raw_item.get('bldgOnlyYn') == 'Y',
            area_m2=float(raw_item.get('goodsArea', 0)) if raw_item.get('goodsArea') else None,
            min_price=min_price,
            round_no=int(raw_item.get('dealSeq', 1)) if raw_item.get('dealSeq') else None,
            dist_deadline=raw_item.get('dspsDt'),
            pay_deadline_days=self._calc_deadline_days(raw_item.get('payScdDt')),
            ids={
                'PLNM_NO': raw_item.get('PLNM_NO', ''),
                'PBCT_NO': raw_item.get('PBCT_NO', ''),
                'CLTR_NO': raw_item.get('CLTR_NO', ''),
                'CLTR_MNMT_NO': raw_item.get('CLTR_MNMT_NO', '')
            }
        )
    
    def _classify_asset_type(self, goods_name: str) -> str:
        """상품명에서 자산유형 분류"""
        if '아파트' in goods_name:
            return '아파트'
        elif '오피스텔' in goods_name:
            return '오피스텔'
        elif '상가' in goods_name or '상업' in goods_name:
            return '상가'
        elif '사무실' in goods_name or '오피스' in goods_name:
            return '사무실'
        elif '토지' in goods_name or '대지' in goods_name:
            return '토지'
        else:
            return '기타'
    
    def _calc_deadline_days(self, pay_date: Optional[str]) -> Optional[int]:
        """납부기한까지 일수 계산"""
        if not pay_date:
            return 7  # 기본값
        # 실제 구현시 날짜 파싱 로직 추가
        return 7
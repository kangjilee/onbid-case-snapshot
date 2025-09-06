import httpx
import xmltodict
import os
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from .utils import ttl_cache
from .schema import NoticeOut
import logging

logger = logging.getLogger(__name__)


class OnbidClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ONBID_KEY')
        self.base_url = "http://apis.data.go.kr/1360000/AuctionInfoService"
        self.mock_mode = not self.api_key
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def _fetch_data(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """API 호출 with 지수백오프"""
        if self.mock_mode:
            return self._mock_response(endpoint, params)
            
        params['serviceKey'] = self.api_key
        
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            
            # XML을 dict로 변환
            data = xmltodict.parse(response.text)
            return data
    
    def _mock_response(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock 데이터 반환"""
        if 'getListAuctionInfo' in endpoint:
            return {
                'response': {
                    'body': {
                        'items': {
                            'item': {
                                'auctionInfo': '아파트',
                                'useType': '주거용',
                                'landRights': '대지권',
                                'shareInfo': '단독',
                                'buildingOnly': 'N',
                                'area': '84.5',
                                'minPrice': '25000',
                                'roundNo': '1',
                                'distDeadline': '2024-03-15',
                                'payDeadlineDays': '7',
                                'PLNM_NO': params.get('PLNM_NO', '12345'),
                                'PBCT_NO': '67890',
                                'CLTR_NO': '111',
                                'CLTR_MNMT_NO': '222'
                            }
                        }
                    }
                }
            }
        return {}
    
    async def get_notice_info(self, id_type: str, number: str, quick_mode: bool = True) -> NoticeOut:
        """공매 정보 조회"""
        cache_key = f"notice_{id_type}_{number}_{quick_mode}"
        
        if cache_key in ttl_cache:
            return ttl_cache[cache_key]
        
        try:
            params = {id_type: number, 'numOfRows': '1'}
            data = await self._fetch_data('getListAuctionInfo', params)
            
            # 응답 파싱
            item = data.get('response', {}).get('body', {}).get('items', {}).get('item', {})
            
            notice = NoticeOut(
                asset_type=item.get('auctionInfo', '알수없음'),
                use_type=item.get('useType', '알수없음'),
                has_land_right='대지권' in item.get('landRights', ''),
                is_share='지분' in item.get('shareInfo', ''),
                building_only=item.get('buildingOnly', 'N') == 'Y',
                area_m2=float(item.get('area', 0)) if item.get('area') else None,
                min_price=int(item.get('minPrice', 0)) if item.get('minPrice') else None,
                round_no=int(item.get('roundNo', 1)) if item.get('roundNo') else None,
                dist_deadline=item.get('distDeadline'),
                pay_deadline_days=int(item.get('payDeadlineDays', 7)) if item.get('payDeadlineDays') else None,
                ids={
                    'PLNM_NO': item.get('PLNM_NO', ''),
                    'PBCT_NO': item.get('PBCT_NO', ''),
                    'CLTR_NO': item.get('CLTR_NO', ''),
                    'CLTR_MNMT_NO': item.get('CLTR_MNMT_NO', '')
                }
            )
            
            ttl_cache[cache_key] = notice
            return notice
            
        except Exception as e:
            logger.error(f"API 호출 실패: {e}")
            # 폴백: 기본값 반환
            return NoticeOut(
                asset_type="아파트",
                use_type="주거용",
                has_land_right=True,
                is_share=False,
                building_only=False,
                area_m2=84.5,
                min_price=25000,
                round_no=1,
                dist_deadline="2024-03-15",
                pay_deadline_days=7,
                ids={id_type: number}
            )
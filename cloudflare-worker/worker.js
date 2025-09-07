// worker.js — ONBID API 릴레이 (회사망 우회용)
// URL: /unify?plnm_no=&cltr_no=&mnmt= 지원
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // CORS 헤더 설정
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };
    
    // OPTIONS 요청 처리
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }
    
    // /unify 엔드포인트만 처리
    if (url.pathname !== '/unify') {
      return new Response('404 Not Found', { status: 404 });
    }
    
    try {
      // 쿼리 파라미터 추출
      const plnm = url.searchParams.get("plnm_no");
      const cltr = url.searchParams.get("cltr_no"); 
      const mnmt = url.searchParams.get("mnmt");
      
      // ONBID API 기본 설정
      const baseUrl = "http://openapi.onbid.co.kr/openapi/services/ThingInfoInquireSvc/getUnifyUsageCltr";
      const params = new URLSearchParams({
        serviceKey: env.ONBID_KEY,
        pageNo: "1",
        numOfRows: "10"
      });
      
      // 조건에 따른 파라미터 추가
      if (mnmt) {
        params.set("CLTR_MNMT_NO", mnmt);
      } else if (plnm && cltr) {
        params.set("PLNM_NO", plnm);
        params.set("CLTR_NO", cltr);
      } else if (plnm) {
        params.set("PLNM_NO", plnm);
      } else {
        return new Response('Bad Request: Missing required parameters', { 
          status: 400,
          headers: corsHeaders 
        });
      }
      
      // ONBID API 호출
      const apiUrl = `${baseUrl}?${params.toString()}`;
      const response = await fetch(apiUrl, {
        headers: {
          "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
        timeout: 10000
      });
      
      const xmlText = await response.text();
      
      // XML 응답 그대로 전달
      return new Response(xmlText, {
        status: response.status,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/xml; charset=utf-8'
        }
      });
      
    } catch (error) {
      console.error('Worker error:', error);
      return new Response(`Internal Server Error: ${error.message}`, { 
        status: 500,
        headers: corsHeaders 
      });
    }
  }
};
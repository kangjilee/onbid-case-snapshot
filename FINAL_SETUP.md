# KOMA Tank 자동 수집 최종 설정

## 1. 즉시 테스트 북마클릿

브라우저 북마크에 아래 URL을 추가하여 사용:

**제목**: KOMA Tank 수집
**URL**: 
```javascript
javascript:(async()=>{try{const payload={source:'tank',source_url:location.href,main_html:document.documentElement.outerHTML.slice(0,400000),docs:[],harvested_at:new Date().toISOString(),user_agent:navigator.userAgent};const response=await fetch('http://localhost:9000/ingest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(response.ok){const result=await response.json();alert('✅ KOMA로 전송 완료!\n파일: '+result.summary.saved_to);}else{alert('❌ 전송 실패: '+response.status);}}catch(e){alert('❌ 오류: '+e.message);}})();
```

## 2. Tampermonkey 자동 스크립트

기존 스크립트를 OFF하고 `tank_harvester_v2.user.js` 추가:

- 매치: `https://tankauction.com/*`
- 자동 실행: Tank 상세페이지 감지시 3초 후 자동 수집
- 전송: `http://localhost:9000/ingest`

## 3. 앱 사용법

1. **앱 접속**: http://localhost:8501
2. **"Tank 수집 서버 상태"** 섹션 열기
3. **"상태 새로고침"** 클릭하여 파일 목록 갱신
4. **최신 파일 선택**
5. **"선택 파일 파싱 및 분석"** 클릭

## 4. 확인사항

파싱 결과에서 다음 항목들이 표시되어야 함:
- ✅ 최저가: XX,XXX,XXX원
- ✅ 면적: XX.X㎡ (XX평)
- ✅ 배분요구종기: YYYY-MM-DD
- ✅ 주소: 정확한 소재지
- ✅ 용도: 아파트/상가 등
- ✅ source: Tank 페이지 URL

## 5. 개선된 기능

- **DOM 기반 파서**: 테이블 구조 정확 인식
- **소스 URL 표시**: 어느 페이지에서 수집했는지 확인 가능
- **다중 문서 병합**: 감정평가서, 재산명세서 등 자동 통합
- **입찰 일정 추출**: 여러 회차 일정 자동 인식

Tank 상세 페이지에서 북마클릿 클릭만으로 즉시 데이터 수집 가능!
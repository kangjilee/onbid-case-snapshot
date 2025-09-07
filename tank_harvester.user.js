// ==UserScript==
// @name         KOMA Tank Auto-Harvester
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Tank auction site auto data harvester
// @author       KOMA
// @match        https://tankauction.com/pa/paView.php*
// @match        https://www.tankauction.com/pa/paView.php*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';
    
    console.log('[KOMA] Tank Auto-Harvester loading...');
    
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    
    // 관심 링크 패턴들 
    const pickLinks = () => {
        const keywords = [
            "감정평가서", "재산명세서", "건축물대장", "토지이용계획",
            "감정평가", "사진보기", "등기부", "지적도", "건물등기", 
            "토지대장", "첨부파일", "도면", "현황사진", "위치도"
        ];
        
        const anchors = Array.from(document.querySelectorAll('a, button, [onclick]'));
        const foundLinks = [];
        
        anchors.forEach(elem => {
            const text = (elem.innerText || elem.textContent || '').trim();
            const href = elem.href || elem.getAttribute('onclick') || elem.dataset?.href || '';
            
            // 키워드 매칭
            const hasKeyword = keywords.some(keyword => text.includes(keyword));
            
            if (hasKeyword && href) {
                foundLinks.push({
                    text: text,
                    href: href,
                    element: elem.tagName
                });
            }
        });
        
        console.log('[KOMA] Found links:', foundLinks.length);
        return foundLinks.map(link => link.href).filter(Boolean);
    };
    
    // URL 정규화
    const resolveHref = (href) => {
        if (!href) return null;
        if (href.startsWith('javascript:')) return null;
        if (href.startsWith('http')) return href;
        
        try {
            return new URL(href, location.href).toString();
        } catch {
            return null;
        }
    };
    
    // 개별 문서 fetch
    async function fetchDocument(url) {
        try {
            console.log('[KOMA] Fetching:', url);
            
            const response = await fetch(url, {
                credentials: 'include',
                headers: {
                    'User-Agent': navigator.userAgent,
                    'Referer': location.href
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const contentType = (response.headers.get('content-type') || '').toLowerCase();
            
            // PDF나 바이너리 파일 처리
            if (contentType.includes('pdf') || contentType.includes('octet-stream') || contentType.includes('application/')) {
                const size = Number(response.headers.get('content-length') || 0);
                return {
                    type: 'binary',
                    url: url,
                    contentType: contentType,
                    size: size,
                    timestamp: new Date().toISOString()
                };
            }
            
            // HTML 텍스트 처리
            const html = await response.text();
            
            // 텍스트만 추출 (용량 절감)
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            
            // 스크립트, 스타일 태그 제거
            tempDiv.querySelectorAll('script, style, nav, header, footer').forEach(el => el.remove());
            
            const textContent = tempDiv.innerText.replace(/\s+/g, ' ').trim();
            
            return {
                type: 'html',
                url: url,
                html: html.slice(0, 200000), // HTML 용량 제한
                text: textContent.slice(0, 100000), // 텍스트 용량 제한
                timestamp: new Date().toISOString()
            };
            
        } catch (error) {
            console.error('[KOMA] Fetch error for', url, ':', error);
            return {
                type: 'error',
                url: url,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    // 메인 실행 함수
    async function harvest() {
        try {
            console.log('[KOMA] Starting harvest for:', location.href);
            
            // 현재 페이지 HTML
            const mainHtml = document.documentElement.outerHTML.slice(0, 300000);
            
            // 관련 링크들 수집
            const linkHrefs = pickLinks();
            const resolvedUrls = Array.from(new Set(
                linkHrefs.map(resolveHref).filter(Boolean)
            ));
            
            console.log('[KOMA] Will fetch', resolvedUrls.length, 'documents');
            
            // 각 문서 수집
            const documents = [];
            for (const url of resolvedUrls) {
                const doc = await fetchDocument(url);
                documents.push(doc);
                
                // 서버 부하 방지
                await sleep(300);
            }
            
            // 수집 데이터 패키지
            const payload = {
                source: 'tank',
                source_url: location.href,
                main_html: mainHtml,
                docs: documents,
                harvested_at: new Date().toISOString(),
                user_agent: navigator.userAgent
            };
            
            // 로컬 앱으로 전송 (ingest 서버 포트 9000)
            const response = await fetch('http://localhost:9000/ingest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('[KOMA] Successfully sent:', result.summary);
                
                // 성공 알림 (UI 추가)
                showNotification(`✅ KOMA 수집 완료: ${documents.length}개 문서`, 'success');
            } else {
                throw new Error(`Server response: ${response.status}`);
            }
            
        } catch (error) {
            console.error('[KOMA] Harvest failed:', error);
            showNotification(`❌ KOMA 수집 실패: ${error.message}`, 'error');
        }
    }
    
    // 알림 표시 함수
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 4px;
            color: white;
            font-weight: bold;
            z-index: 99999;
            font-size: 14px;
            max-width: 300px;
            background-color: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // 5초 후 자동 제거
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    // 상태 표시 추가
    function addStatusIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'koma-status';
        indicator.style.cssText = `
            position: fixed;
            top: 10px;
            left: 20px;
            padding: 8px 12px;
            background: #1976D2;
            color: white;
            border-radius: 20px;
            font-size: 12px;
            z-index: 99998;
            font-family: Arial, sans-serif;
        `;
        indicator.textContent = '🤖 KOMA 수집기 동작중...';
        
        document.body.appendChild(indicator);
        
        // 10초 후 제거
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 10000);
    }
    
    // 페이지 로드 완료 후 실행
    function initialize() {
        // Tank 상세 페이지인지 확인
        if (!location.pathname.includes('paView.php')) {
            console.log('[KOMA] Not a tank detail page, skipping');
            return;
        }
        
        console.log('[KOMA] Tank detail page detected');
        
        // 상태 표시
        addStatusIndicator();
        
        // 잠시 대기 후 수집 시작
        setTimeout(harvest, 2000);
    }
    
    // 페이지 준비되면 실행
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
    
    console.log('[KOMA] Tank Auto-Harvester loaded');
})();
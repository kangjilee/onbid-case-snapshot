// ==UserScript==
// @name         KOMA Tank Auto-Harvester v2
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Tank auction auto harvester - improved version
// @author       KOMA
// @match        https://tankauction.com/*
// @match        https://www.tankauction.com/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';
    
    const POST_URL = "http://localhost:9000/ingest";   // ingest 서버 포트
    const onTarget = location.pathname.includes("/pa/paView.php");
    
    if (!onTarget) {
        console.log('[KOMA] Not a tank detail page, skipping');
        return;
    }
    
    console.log('[KOMA] Tank Auto-Harvester v2 starting...');
    
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    
    const resolveHref = (href) => {
        try {
            if (!href) return null;
            if (href.startsWith('javascript:')) return null;
            return new URL(href, location.href).toString();
        } catch {
            return null;
        }
    };
    
    const pickLinks = () => {
        const keywords = ["감정평가", "재산명세", "건축물", "토지이용", "등기", "지적", "사진"];
        const elements = Array.from(document.querySelectorAll('a, button'));
        const links = [];
        
        elements.forEach(elem => {
            const text = (elem.innerText || elem.textContent || '').trim();
            const href = elem.href || elem.getAttribute('onclick') || elem.dataset?.href;
            
            if (href && keywords.some(keyword => text.includes(keyword))) {
                const resolved = resolveHref(href);
                if (resolved && !links.includes(resolved)) {
                    links.push(resolved);
                }
            }
        });
        
        console.log(`[KOMA] Found ${links.length} document links`);
        return links;
    };
    
    async function fetchDocument(url) {
        try {
            console.log(`[KOMA] Fetching: ${url}`);
            
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
            
            if (contentType.includes('pdf') || contentType.includes('octet-stream')) {
                return {
                    type: 'binary',
                    url: url,
                    contentType: contentType,
                    size: Number(response.headers.get('content-length') || 0),
                    timestamp: new Date().toISOString()
                };
            }
            
            const html = await response.text();
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            
            // 불필요한 태그 제거
            tempDiv.querySelectorAll('script, style, nav, header, footer').forEach(el => el.remove());
            
            const textContent = tempDiv.innerText.replace(/\s+/g, ' ').trim();
            
            return {
                type: 'html',
                url: url,
                html: html.slice(0, 200000),
                text: textContent.slice(0, 100000),
                timestamp: new Date().toISOString()
            };
            
        } catch (error) {
            console.error(`[KOMA] Fetch error for ${url}:`, error);
            return {
                type: 'error',
                url: url,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    async function harvest() {
        try {
            console.log('[KOMA] Starting harvest for:', location.href);
            showNotification('🤖 KOMA 수집 시작...', 'info');
            
            // 메인 페이지 HTML
            const mainHtml = document.documentElement.outerHTML.slice(0, 300000);
            
            // 관련 링크 수집
            const links = pickLinks();
            
            // 각 문서 수집
            const documents = [];
            for (const url of links.slice(0, 10)) {  // 최대 10개 제한
                const doc = await fetchDocument(url);
                documents.push(doc);
                await sleep(200);  // 서버 부하 방지
            }
            
            // 페이로드 생성
            const payload = {
                source: 'tank',
                source_url: location.href,
                main_html: mainHtml,
                docs: documents,
                harvested_at: new Date().toISOString(),
                user_agent: navigator.userAgent
            };
            
            console.log(`[KOMA] Sending ${documents.length} documents to ${POST_URL}`);
            
            // 전송
            const response = await fetch(POST_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('[KOMA] Successfully sent:', result.summary);
                showNotification(`✅ KOMA 수집 완료: ${documents.length}개 문서`, 'success');
            } else {
                throw new Error(`Server response: ${response.status}`);
            }
            
        } catch (error) {
            console.error('[KOMA] Harvest failed:', error);
            showNotification(`❌ KOMA 수집 실패: ${error.message}`, 'error');
        }
    }
    
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
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    // 실행
    console.log('[KOMA] Tank detail page detected');
    
    // 페이지 로딩 완료 후 3초 대기하여 실행
    setTimeout(() => {
        harvest();
    }, 3000);
    
    console.log('[KOMA] Tank Auto-Harvester v2 loaded');
})();
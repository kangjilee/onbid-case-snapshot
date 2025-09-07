# ONBID API Relay - Cloudflare Worker

회사망에서 ONBID API 직접 호출이 차단될 때 사용하는 릴레이 서버입니다.

## 배포 방법

1. **Wrangler 설치 및 로그인**
```bash
npm install -g wrangler
wrangler login
```

2. **프로젝트 초기화**
```bash
cd cloudflare-worker
wrangler init onbid-relay --yes
# worker.js와 wrangler.toml 파일이 이미 준비되어 있습니다
```

3. **API 키 설정**
```bash
wrangler secret put ONBID_KEY
# 프롬프트에서 다음 키 입력: 803384ef46f232804e8172a734b774a10eb5a3f854d91d1ce3ba38960bb1cee4
```

4. **배포**
```bash
wrangler deploy
```

5. **배포 완료 후 URL 확인**
배포가 완료되면 다음과 같은 형태의 URL을 받게 됩니다:
```
https://onbid-relay.yourname.workers.dev
```

## 사용법

배포된 Worker URL을 `.env` 파일에 추가:
```
ONBID_PROXY_URL=https://onbid-relay.yourname.workers.dev/unify
```

## API 엔드포인트

- `GET /unify?plnm_no=202401774&cltr_no=6` - 공고번호+물건번호 조회
- `GET /unify?plnm_no=202401774` - 공고번호 조회  
- `GET /unify?mnmt=2016-0500-000201` - 관리번호 조회

## 테스트

Worker 배포 후 브라우저에서 테스트:
```
https://your-worker.workers.dev/unify?plnm_no=202401774
```

XML 응답이 나오면 정상 작동입니다.
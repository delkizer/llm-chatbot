# spo-chatbot 프레임워크 검증 샘플

embed Web Component(`<spo-chatbot>`)의 크로스 프레임워크 호환성을 검증하기 위한 샘플 모음이다. 각 샘플은 해당 프레임워크 환경에서 챗봇을 삽입하고, 속성 바인딩/테마 변경/동적 속성 반영이 정상 동작하는지 확인한다.

## 사전 준비

embed.js가 빌드되어 있어야 한다.

```bash
cd embed
npm install
npm run build
# dist/embed.js 생성 확인
```

## 게이트웨이 서버 (추천)

단일 포트(5174)에서 전체 샘플을 URI 경로로 접근할 수 있다.

```bash
cd embed/samples

# 전체 샘플 빌드 (최초 1회)
./manage.sh build-all

# 게이트웨이 서버 실행 (포트 5174)
./manage.sh serve
# 또는: uvicorn gateway:app --port 5174 --reload
```

| URL | 샘플 |
|-----|------|
| `http://localhost:5174/` | 랜딩 페이지 (샘플 목록) |
| `http://localhost:5174/sample/vanilla/` | Vanilla HTML |
| `http://localhost:5174/sample/vue3/` | Vue 3 |
| `http://localhost:5174/sample/react/` | React |
| `http://localhost:5174/sample/svelte/` | Svelte |
| `http://localhost:5174/sample/nextjs/` | Next.js |
| `http://localhost:5174/sample/angular/` | Angular |
| `http://localhost:5174/sample/htmx/` | HTMX |
| `http://localhost:5174/sample/iframe/` | iframe |

> 게이트웨이는 FastAPI 기반이며, 각 프레임워크의 빌드 결과물을 정적 파일로 서빙한다.
> HTMX 샘플만 Jinja2 서버 사이드 렌더링으로 처리된다.

## 개별 실행 (개발 시)

HMR이 필요한 개발 시에는 각 샘플을 개별 포트로 실행할 수 있다.

| # | 샘플 | 포트 | 실행 방법 |
|---|------|------|----------|
| 1 | vanilla | 5170 | `python3 -m http.server 5170` |
| 2 | vue3 | 5171 | `npm run dev` |
| 3 | react | 5172 | `npm run dev` |
| 4 | svelte | 5173 | `npm run dev` |
| 5 | nextjs | 5174 | `npm run dev` |
| 6 | angular | 5175 | `npm run start` |
| 7 | htmx | 5176 | `uvicorn server:app --port 5176 --reload` |
| 8 | iframe | 5177 | `python3 -m http.server 5177` |

## manage.sh 사용법

```bash
# 게이트웨이 서버 실행 (포트 5174)
./manage.sh serve

# embed.js + 전체 샘플 빌드
./manage.sh build-all

# 전체 의존성 설치
./manage.sh install

# 개별 샘플 빌드
./manage.sh build

# 전체 개발 서버 실행 (개별 포트, 백그라운드)
./manage.sh dev

# 특정 샘플만 실행 (포그라운드)
./manage.sh dev angular

# 백그라운드 개발 서버 종료
./manage.sh stop

# node_modules, dist, __pycache__ 등 정리
./manage.sh clean
```

## 주의사항

- **embed.js 빌드 필수**: 모든 샘플은 `embed/dist/embed.js`를 참조한다. 빌드하지 않으면 chatbot이 렌더링되지 않는다.
- **Next.js 심볼릭 링크**: Next.js 샘플은 `public/` 폴더에 `embed.js` 심볼릭 링크가 필요하다. `ln -s ../../../dist/embed.js public/embed.js`
- **Angular 의존성**: Angular 샘플은 `npm install` 후 `@angular/cli`가 설치되어야 `npm run start`가 동작한다.
- **HTMX Python 환경**: htmx 샘플은 Python 가상환경에서 `pip install -r requirements.txt`로 fastapi, uvicorn, jinja2를 설치해야 한다.
- **API 서버**: 실제 챗봇 동작을 확인하려면 `http://localhost:4502`에 chatbot API 서버가 실행 중이어야 한다.

## 관련 문서

| 문서 | 설명 |
|------|------|
| `docs/embed/01-embed-overview.md` | embed 도메인 개요, 속성 정의 |
| `docs/embed/02-component-design.md` | 컴포넌트 상세 설계 |
| `docs/embed/03-api-integration.md` | API 연동 설계 |
| `docs/embed/04-framework-samples.md` | 프레임워크별 검증 설계 |

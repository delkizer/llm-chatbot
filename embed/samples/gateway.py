"""
spo-chatbot 프레임워크 검증 샘플 게이트웨이

8종 프레임워크 샘플을 단일 포트(5174)에서 URI 기반으로 서빙한다.

실행:
    cd embed/samples
    uvicorn gateway:app --port 5174 --reload
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

# ============================================================
# 환경 설정 (.env 2단계 로드 — Config 클래스와 동일 패턴)
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
_django_env = os.getenv("DJANGO_ENV", "development")
load_dotenv(PROJECT_ROOT / f".env.{_django_env}", override=True)

CHATBOT_API_URL = os.getenv("CHATBOT_API_URL", "http://localhost:4502")

# ============================================================
# 경로 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
EMBED_DIST_DIR = BASE_DIR.parent / "dist"
EMBED_JS_PATH = EMBED_DIST_DIR / "embed.js"

# htmx 템플릿 디렉토리
HTMX_TEMPLATES_DIR = BASE_DIR / "htmx" / "templates"

# 게이트웨이 랜딩 페이지 템플릿
GATEWAY_TEMPLATES_DIR = BASE_DIR / "templates"

# ============================================================
# 토큰 주입 미들웨어 (서버 사이드 HTML 치환)
# ============================================================

DEV_TEST_TOKEN = "dev-test-token"
API_URL_PLACEHOLDER = "__CHATBOT_API_URL__"

# 치환 대상 Content-Type
_REPLACEABLE_TYPES = ("text/html", "application/javascript", "text/javascript")


class TokenInjectionMiddleware(BaseHTTPMiddleware):
    """응답 내 플레이스홀더를 실제 값으로 서버 사이드 치환한다.

    치환 대상:
    - __CHATBOT_API_URL__ → CHATBOT_API_URL 환경변수 값
    - dev-test-token → 요청에서 전달된 실제 토큰
    """

    async def dispatch(self, request, call_next):
        token = request.query_params.get("token") or request.cookies.get("access_token")

        response = await call_next(request)
        content_type = response.headers.get("content-type", "")

        # HTML 또는 JS 응답만 치환
        if not any(ct in content_type for ct in _REPLACEABLE_TYPES):
            return response

        # api-url 치환이 필요하거나, 토큰 치환이 필요한 경우
        needs_api_replace = CHATBOT_API_URL != API_URL_PLACEHOLDER
        needs_token_replace = token and token != DEV_TEST_TOKEN

        if not needs_api_replace and not needs_token_replace:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        text = body.decode("utf-8")

        if needs_api_replace:
            text = text.replace(API_URL_PLACEHOLDER, CHATBOT_API_URL)
        if needs_token_replace:
            text = text.replace(DEV_TEST_TOKEN, token)

        headers = {
            k: v for k, v in response.headers.items()
            if k.lower() not in ("content-length", "content-type")
        }

        # 원래 Content-Type 유지
        media_type = "text/html" if "text/html" in content_type else "application/javascript"
        return Response(
            content=text,
            status_code=response.status_code,
            headers=headers,
            media_type=media_type,
        )


# ============================================================
# FastAPI 앱 생성
# ============================================================

app = FastAPI(title="spo-chatbot Sample Gateway")
app.add_middleware(TokenInjectionMiddleware)

# 템플릿 엔진
gateway_templates = Jinja2Templates(directory=str(GATEWAY_TEMPLATES_DIR))
htmx_templates = Jinja2Templates(directory=str(HTMX_TEMPLATES_DIR))

# ============================================================
# embed.js 서빙 (두 경로 모두)
# ============================================================


@app.get("/embed.js")
async def serve_embed_js():
    """Vite 기반 샘플(vue3, react, svelte)용 — /embed.js"""
    return FileResponse(
        str(EMBED_JS_PATH),
        media_type="application/javascript",
    )


@app.get("/dist/embed.js")
async def serve_embed_js_dist():
    """vanilla, iframe 호환용 — /dist/embed.js"""
    return FileResponse(
        str(EMBED_JS_PATH),
        media_type="application/javascript",
    )


# ============================================================
# 랜딩 페이지
# ============================================================


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """샘플 목록 랜딩 페이지"""
    return gateway_templates.TemplateResponse("landing.html", {
        "request": request,
    })


# ============================================================
# htmx — Jinja2 템플릿 렌더링
# ============================================================


@app.get("/sample/htmx/", response_class=HTMLResponse)
async def htmx_index(request: Request):
    """htmx 샘플 — 서버 사이드 렌더링"""
    return htmx_templates.TemplateResponse("index.html", {
        "request": request,
        "token": "dev-test-token",
        "theme": "bwf",
    })


# ============================================================
# iframe — host.html을 기본 페이지로 서빙
# ============================================================


@app.get("/sample/iframe/", response_class=HTMLResponse)
async def iframe_index():
    """iframe 샘플 — host.html 서빙 (index.html 없음)"""
    return FileResponse(
        str(BASE_DIR / "iframe" / "host.html"),
        media_type="text/html",
    )


# ============================================================
# 정적 파일 마운트 (StaticFiles)
#
# 순서 주의: 구체적 경로 → 일반적 경로
# html=True 옵션으로 index.html 자동 서빙
# ============================================================

# Vite 빌드 결과물
app.mount(
    "/sample/vue3",
    StaticFiles(directory=str(BASE_DIR / "vue3" / "dist"), html=True),
    name="vue3",
)

app.mount(
    "/sample/react",
    StaticFiles(directory=str(BASE_DIR / "react" / "dist"), html=True),
    name="react",
)

app.mount(
    "/sample/svelte",
    StaticFiles(directory=str(BASE_DIR / "svelte" / "dist"), html=True),
    name="svelte",
)

# Next.js 정적 내보내기
app.mount(
    "/sample/nextjs",
    StaticFiles(directory=str(BASE_DIR / "nextjs" / "out"), html=True),
    name="nextjs",
)

# Angular 빌드 결과물
app.mount(
    "/sample/angular",
    StaticFiles(
        directory=str(BASE_DIR / "angular" / "dist" / "browser"),
        html=True,
    ),
    name="angular",
)

# 정적 HTML 샘플
app.mount(
    "/sample/vanilla",
    StaticFiles(directory=str(BASE_DIR / "vanilla"), html=True),
    name="vanilla",
)

app.mount(
    "/sample/iframe",
    StaticFiles(directory=str(BASE_DIR / "iframe"), html=True),
    name="iframe",
)

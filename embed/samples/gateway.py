"""
spo-chatbot 프레임워크 검증 샘플 게이트웨이

8종 프레임워크 샘플을 단일 포트(8280)에서 URI 기반으로 서빙한다.

실행:
    cd embed/samples
    uvicorn gateway:app --port 8280 --reload
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
# FastAPI 앱 생성
# ============================================================

app = FastAPI(title="spo-chatbot Sample Gateway")

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
        "api_url": "http://localhost:4502",
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

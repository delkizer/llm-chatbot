import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from apps.chatbot.app import create_app as create_chatbot_app
from apps.auth.router import router as auth_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LLM Chatbot 서비스 시작")
    yield
    logger.info("LLM Chatbot 서비스 종료")


chatbot_app = create_chatbot_app()

root = FastAPI(
    title="LLM Chatbot API",
    description="로컬 LLM 기반 스포츠 데이터 Q&A 챗봇",
    version="0.0.1",
    docs_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS 설정
root.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth 라우터 직접 등록 (/api/auth)
root.include_router(auth_router, prefix="/api")

# 서브앱 마운트
root.mount("/api", chatbot_app)


def custom_openapi():
    if root.openapi_schema:
        return root.openapi_schema

    root_schema = get_openapi(
        title="LLM Chatbot API",
        version="0.0.1",
        description="로컬 LLM 기반 스포츠 데이터 Q&A 챗봇",
        routes=root.routes,
    )

    # chatbot_app 스키마 병합 (/api에 마운트)
    chatbot_schema = chatbot_app.openapi()
    for path, item in chatbot_schema.get("paths", {}).items():
        new_path = f"/api{path}"
        root_schema["paths"][new_path] = item

    # components 병합
    for comp, obj in chatbot_schema.get("components", {}).items():
        root_schema.setdefault("components", {}).setdefault(comp, {}).update(obj)

    # HTTP Bearer 보안 스키마 추가
    root_schema.setdefault("components", {}).setdefault("securitySchemes", {})["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT 토큰을 입력하세요. /api/auth/login에서 발급받을 수 있습니다."
    }

    # 인증이 필요한 엔드포인트에 보안 적용
    auth_excluded_paths = [
        "/api/chat/hello",
        "/api/chat/health",
        "/api/auth/login",
        "/api/auth/logout",
    ]

    for path, path_item in root_schema.get("paths", {}).items():
        # 제외 경로 체크
        if any(path.startswith(excluded) for excluded in auth_excluded_paths):
            continue

        for method in path_item.values():
            if isinstance(method, dict) and "responses" in method:
                method["security"] = [{"bearerAuth": []}]

    root.openapi_schema = root_schema
    return root_schema


root.openapi = custom_openapi


@root.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="LLM Chatbot API - Swagger UI",
        swagger_ui_parameters={
            "persistAuthorization": True,
        },
    )


app = root

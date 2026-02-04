from fastapi import FastAPI
from apps.auth.router import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="LLM Chatbot Auth",
        description="LLM Chatbot 인증 서비스",
        version="0.0.1",
    )

    app.include_router(router)

    return app

from fastapi import FastAPI
from apps.chatbot.router import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="LLM Chatbot",
        description="로컬 LLM 기반 스포츠 데이터 Q&A 챗봇",
        version="0.0.1",
    )

    app.include_router(router)

    return app

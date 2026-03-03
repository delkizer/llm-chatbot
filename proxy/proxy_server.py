"""
Claude API Proxy Server

개발자 로컬 PC에서 실행하는 프록시 서버.
API 키를 서버에 올리지 않고, 로컬에서 주입하여 api.anthropic.com으로 중계.

사용법:
    cd proxy/
    python proxy_server.py

    # ngrok으로 외부 노출
    ngrok http 8080
"""

import os
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

# .env 로드 (proxy/.env)
load_dotenv(Path(__file__).parent / ".env")

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_API_URL = "https://api.anthropic.com"
PROXY_PORT = int(os.getenv("PROXY_PORT", "8080"))

app = FastAPI(title="Claude API Proxy", docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    """프록시 상태 확인"""
    return {
        "status": "ok",
        "api_key_set": bool(CLAUDE_API_KEY),
        "target": CLAUDE_API_URL,
    }


@app.post("/v1/messages")
async def proxy_messages(request: Request):
    """
    Claude Messages API 중계

    - 요청에 x-api-key 헤더 주입
    - stream: true → SSE 중계
    - stream: false → JSON 포워딩
    """
    if not CLAUDE_API_KEY:
        return JSONResponse(
            status_code=500,
            content={"error": "CLAUDE_API_KEY not configured"},
        )

    body = await request.body()
    body_json = await request.json()

    # 헤더 구성 (클라이언트 헤더에서 host 제거 후 API 키 주입)
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": request.headers.get("anthropic-version", "2023-06-01"),
        "content-type": "application/json",
    }

    target_url = f"{CLAUDE_API_URL}/v1/messages"
    is_stream = body_json.get("stream", False)

    if is_stream:
        return await _proxy_stream(target_url, headers, body)
    else:
        return await _proxy_json(target_url, headers, body)


async def _proxy_json(url: str, headers: dict, body: bytes) -> JSONResponse:
    """비스트리밍 JSON 포워딩"""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, headers=headers, content=body)
        return JSONResponse(
            status_code=response.status_code,
            content=response.json(),
        )


async def _proxy_stream(url: str, headers: dict, body: bytes) -> StreamingResponse:
    """SSE 스트리밍 중계"""

    async def stream_generator():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", url, headers=headers, content=body
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    print(f"Claude API Proxy starting on port {PROXY_PORT}")
    print(f"API Key configured: {bool(CLAUDE_API_KEY)}")
    print(f"Target: {CLAUDE_API_URL}")
    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT)

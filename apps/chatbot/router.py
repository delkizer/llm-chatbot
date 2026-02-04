"""
Chatbot Router

채팅 API 엔드포인트
"""

from typing import Optional
from fastapi import APIRouter, Path, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from class_config.class_env import Config
from class_lib.chat_service import ChatService
from apps.chatbot.deps import (
    get_current_payload,
    get_chat_service,
    get_user_id,
)

router = APIRouter(prefix="/chat")
config = Config()


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatRequest(BaseModel):
    """채팅 요청"""
    message: str = Field(..., description="사용자 메시지", min_length=1, max_length=4000)
    context_type: str = Field(default="badminton", description="컨텍스트 유형 (badminton, baseball 등)")
    skill_name: Optional[str] = Field(default=None, description="스킬 이름 (기본: context_type)")
    context: Optional[dict] = Field(default=None, description="추가 컨텍스트 (match_id, player_id 등)")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="생성 다양성")
    max_tokens: int = Field(default=2048, ge=1, le=4096, description="최대 생성 토큰 수")


class ChatResponse(BaseModel):
    """채팅 응답"""
    content: str = Field(..., description="AI 응답 텍스트")
    session_id: str = Field(..., description="세션 ID")
    model: str = Field(..., description="사용된 모델")
    response_time_ms: float = Field(..., description="응답 시간 (ms)")
    tokens: dict = Field(..., description="토큰 정보")
    skill_name: str = Field(..., description="사용된 스킬")
    message_count: int = Field(..., description="세션 내 총 메시지 수")


class SessionInfoResponse(BaseModel):
    """세션 정보 응답"""
    session_id: str
    user_id: str
    context_type: str
    skill_name: str
    message_count: int
    context: dict
    created_at: str
    updated_at: str


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    ollama: str
    redis: str
    skills: list[str]
    model: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/hello/{name}", tags=["Sample"])
async def say_hello(
    name: str = Path(..., description="사용자 이름")
):
    """
    샘플 엔드포인트 - 인증 불필요
    """
    return {"message": f"Hello {name}"}


@router.get("/health", tags=["Health"], response_model=HealthResponse)
async def health_check(
    service: ChatService = Depends(get_chat_service)
):
    """
    서비스 상태 확인 - 인증 불필요

    - Ollama 연결 상태
    - Redis 연결 상태
    - 사용 가능한 스킬 목록
    """
    status_info = await service.health_check()

    return HealthResponse(
        status="ok" if status_info["healthy"] else "error",
        ollama=status_info["ollama"],
        redis=status_info["redis"],
        skills=status_info["skills"],
        model=service.ollama.model
    )


@router.post("/", tags=["Chat"], response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_user_id),
    service: ChatService = Depends(get_chat_service)
):
    """
    채팅 요청 (비스트리밍)

    - 인증된 사용자만 사용 가능
    - 대화 히스토리 자동 관리
    - SKILL 기반 시스템 프롬프트 적용
    """
    try:
        result = await service.chat(
            user_id=user_id,
            message=request.message,
            context_type=request.context_type,
            skill_name=request.skill_name,
            context=request.context,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        return ChatResponse(
            content=result.content,
            session_id=result.session_id,
            model=result.model,
            response_time_ms=result.response_time_ms,
            tokens=result.tokens,
            skill_name=result.skill_name,
            message_count=result.message_count
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"채팅 처리 중 오류: {str(e)}"
        )


@router.post("/stream", tags=["Chat"])
async def chat_stream(
    request: ChatRequest,
    user_id: str = Depends(get_user_id),
    service: ChatService = Depends(get_chat_service)
):
    """
    스트리밍 채팅 요청 (SSE)

    - 인증된 사용자만 사용 가능
    - Server-Sent Events로 실시간 응답
    - Content-Type: text/event-stream
    """
    async def event_generator():
        try:
            async for chunk in service.chat_stream(
                user_id=user_id,
                message=request.message,
                context_type=request.context_type,
                skill_name=request.skill_name,
                context=request.context,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            ):
                yield {"event": "message", "data": chunk}

            # 스트림 종료 이벤트
            yield {"event": "done", "data": "[DONE]"}

        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())


@router.get("/session", tags=["Session"], response_model=SessionInfoResponse)
async def get_session_info(
    context_type: str = "badminton",
    user_id: str = Depends(get_user_id),
    service: ChatService = Depends(get_chat_service)
):
    """
    현재 세션 정보 조회

    - 세션 ID, 메시지 수, 컨텍스트 등
    """
    info = service.get_session_info(user_id, context_type)

    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="세션이 존재하지 않습니다"
        )

    return SessionInfoResponse(**info)


@router.delete("/session", tags=["Session"])
async def delete_session(
    context_type: str = "badminton",
    user_id: str = Depends(get_user_id),
    service: ChatService = Depends(get_chat_service)
):
    """
    세션 삭제 (대화 초기화)

    - 세션과 모든 대화 히스토리 삭제
    """
    deleted = service.delete_session(user_id, context_type)

    return {
        "deleted": deleted,
        "user_id": user_id,
        "context_type": context_type
    }


@router.delete("/session/messages", tags=["Session"])
async def clear_messages(
    context_type: str = "badminton",
    user_id: str = Depends(get_user_id),
    service: ChatService = Depends(get_chat_service)
):
    """
    대화 히스토리만 삭제 (세션 유지)

    - 메시지만 삭제하고 세션은 유지
    """
    cleared = service.clear_history(user_id, context_type)

    return {
        "cleared": cleared,
        "user_id": user_id,
        "context_type": context_type
    }


@router.post("/skill/reload", tags=["Admin"])
async def reload_skill(
    skill_name: Optional[str] = None,
    payload: dict = Depends(get_current_payload),
    service: ChatService = Depends(get_chat_service)
):
    """
    SKILL 캐시 새로고침 (관리자용)

    - skill_name 지정 시 해당 스킬만 새로고침
    - 미지정 시 전체 캐시 삭제
    """
    service.reload_skill(skill_name)

    return {
        "reloaded": skill_name or "all",
        "available_skills": service.skill_loader.list_skills()
    }

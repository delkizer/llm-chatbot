"""
Chatbot Dependencies

FastAPI 의존성 주입 모듈
"""

from fastapi import Depends, HTTPException, status, Request
from class_config.class_log import ConfigLogger
from class_lib.auth import Auth
from class_lib.chat_service import ChatService

# 로거 설정
logger = ConfigLogger('http_log', 365).get_logger('chatbot')

# 서비스 인스턴스 (싱글톤)
auth = Auth(logger)
_chat_service: ChatService = None


def get_chat_service() -> ChatService:
    """ChatService 싱글톤 반환"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(logger)
    return _chat_service


async def get_current_payload(request: Request):
    """현재 사용자 payload 조회 (자체 JWT 검증)"""
    token = request.cookies.get("access_token")

    if not token:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token missing"
        )

    # 자체 JWT 검증
    return auth.verify_token(token)


def get_user_id(payload: dict = Depends(get_current_payload)) -> str:
    """payload에서 user_id 추출"""
    # payload 형태에 따라 처리
    if isinstance(payload, dict):
        return payload.get("email") or payload.get("user_id") or "anonymous"
    if isinstance(payload, list) and len(payload) > 0:
        return payload[0].get("email") or payload[0].get("user_id") or "anonymous"
    return "anonymous"


def require_role(*roles):
    """역할 기반 접근 제어"""
    async def _wrapper(payload: dict = Depends(get_current_payload)):
        user_role = payload.get("role") if isinstance(payload, dict) else None

        # payload가 리스트인 경우 (btn /userinfo 응답 형태)
        if isinstance(payload, list) and len(payload) > 0:
            user_role = payload[0].get("role")

        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"허용된 역할: {roles}"
            )
        return payload
    return _wrapper

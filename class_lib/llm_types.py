"""
LLM 공통 타입 및 예외

OllamaClient, ClaudeClient가 공유하는 응답 모델과 예외 계층.
"""

from dataclasses import dataclass, field


# =============================================================================
# 공통 예외 계층
# =============================================================================

class LLMError(Exception):
    """LLM 기본 예외"""
    pass


class LLMConnectionError(LLMError):
    """연결 실패"""
    pass


class LLMTimeoutError(LLMError):
    """타임아웃"""
    pass


class LLMAPIError(LLMError):
    """API 에러 응답"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")


# =============================================================================
# 공통 응답 데이터 클래스
# =============================================================================

@dataclass
class ChatResponse:
    """채팅 응답 (메타데이터 포함)"""
    content: str
    model: str
    response_time_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    done: bool = True
    done_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "model": self.model,
            "response_time_ms": self.response_time_ms,
            "tokens": {
                "prompt": self.prompt_tokens,
                "completion": self.completion_tokens,
                "total": self.total_tokens
            },
            "done": self.done,
            "done_reason": self.done_reason
        }


@dataclass
class ModelInfo:
    """모델 정보"""
    name: str
    size: int = 0
    digest: str = ""
    modified_at: str = ""
    details: dict = field(default_factory=dict)

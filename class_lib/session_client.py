"""
Redis Session Client

채팅 세션 관리를 위한 Redis 클라이언트.
대화 히스토리, 컨텍스트 저장을 담당합니다.
"""

import json
from typing import Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from redis.sentinel import Sentinel

from class_config.class_env import Config


@dataclass
class ChatMessage:
    """채팅 메시지"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatSession:
    """채팅 세션 데이터"""
    session_id: str
    user_id: str
    context_type: str  # "badminton", "baseball", etc.
    skill_name: str = "badminton"
    messages: list[ChatMessage] = field(default_factory=list)
    context: dict = field(default_factory=dict)  # match_id, player_id 등
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def add_message(self, role: str, content: str):
        """메시지 추가"""
        self.messages.append(ChatMessage(role=role, content=content))
        self.updated_at = datetime.now().isoformat()

    def get_messages_for_llm(self, max_messages: int = 10) -> list[dict]:
        """LLM API용 메시지 목록 반환 (최근 N개)"""
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [msg.to_dict() for msg in recent]

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "context_type": self.context_type,
            "skill_name": self.skill_name,
            "messages": [asdict(msg) for msg in self.messages],
            "context": self.context,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatSession":
        messages = [ChatMessage(**msg) for msg in data.get("messages", [])]
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            context_type=data["context_type"],
            skill_name=data.get("skill_name", "badminton"),
            messages=messages,
            context=data.get("context", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )


class SessionClient:
    """
    Redis 기반 세션 클라이언트

    세션 키 형식: session:{user_id}:{context_type}
    """

    SESSION_PREFIX = "chatbot:session:"

    def __init__(self, logger, config: Config = None):
        self.logger = logger
        self.config = config or Config()

        # Redis Sentinel 설정
        self.sentinel = Sentinel(
            self.config.redis_sentinel_nodes,
            socket_timeout=3.0
        )
        self.master_name = self.config.redis_sentinel_master
        self.password = self.config.redis_password
        self.db = self.config.redis_db
        self.ttl = self.config.session_ttl

        self.logger.info("=" * 60)
        self.logger.info("SessionClient 초기화")
        self.logger.info(f"  sentinel_nodes: {self.config.redis_sentinel_nodes}")
        self.logger.info(f"  master: {self.master_name}")
        self.logger.info(f"  db: {self.db}")
        self.logger.info(f"  ttl: {self.ttl}s")
        self.logger.info("=" * 60)

    def _get_master(self):
        """Redis master 연결 반환"""
        return self.sentinel.master_for(
            self.master_name,
            password=self.password,
            db=self.db
        )

    def _make_key(self, user_id: str, context_type: str) -> str:
        """세션 키 생성"""
        return f"{self.SESSION_PREFIX}{user_id}:{context_type}"

    def ping(self) -> bool:
        """Redis 연결 테스트"""
        try:
            master = self._get_master()
            result = master.ping()
            self.logger.debug(f"Redis ping: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Redis ping failed: {e}")
            return False

    def get_session(self, user_id: str, context_type: str) -> Optional[ChatSession]:
        """세션 조회"""
        key = self._make_key(user_id, context_type)
        self.logger.info(f"[Session] GET {key}")

        try:
            master = self._get_master()
            data = master.get(key)

            if data is None:
                self.logger.info(f"[Session] NOT FOUND: {key}")
                return None

            data_str = data.decode() if isinstance(data, bytes) else data
            session = ChatSession.from_dict(json.loads(data_str))
            self.logger.info(f"[Session] FOUND: {key}, messages={len(session.messages)}")
            return session

        except Exception as e:
            self.logger.error(f"[Session] GET error: {e}")
            return None

    def save_session(self, session: ChatSession) -> bool:
        """세션 저장"""
        key = self._make_key(session.user_id, session.context_type)
        self.logger.info(f"[Session] SAVE {key}, messages={len(session.messages)}")

        try:
            master = self._get_master()
            session.updated_at = datetime.now().isoformat()
            data = json.dumps(session.to_dict(), ensure_ascii=False)
            master.setex(key, self.ttl, data)
            self.logger.info(f"[Session] SAVED: {key}, ttl={self.ttl}s")
            return True

        except Exception as e:
            self.logger.error(f"[Session] SAVE error: {e}")
            return False

    def create_session(
        self,
        user_id: str,
        context_type: str,
        skill_name: str = "badminton",
        context: dict = None
    ) -> ChatSession:
        """새 세션 생성"""
        session_id = f"{user_id}:{context_type}:{datetime.now().strftime('%Y%m%d%H%M%S')}"
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            context_type=context_type,
            skill_name=skill_name,
            context=context or {}
        )
        self.logger.info(f"[Session] CREATE: {session_id}")
        self.save_session(session)
        return session

    def get_or_create_session(
        self,
        user_id: str,
        context_type: str,
        skill_name: str = "badminton",
        context: dict = None
    ) -> ChatSession:
        """세션 조회 또는 생성"""
        session = self.get_session(user_id, context_type)
        if session:
            # 컨텍스트 업데이트
            if context:
                session.context.update(context)
                self.save_session(session)
            return session
        return self.create_session(user_id, context_type, skill_name, context)

    def delete_session(self, user_id: str, context_type: str) -> bool:
        """세션 삭제"""
        key = self._make_key(user_id, context_type)
        self.logger.info(f"[Session] DELETE {key}")

        try:
            master = self._get_master()
            result = master.delete(key) > 0
            self.logger.info(f"[Session] DELETED: {key}, success={result}")
            return result

        except Exception as e:
            self.logger.error(f"[Session] DELETE error: {e}")
            return False

    def clear_messages(self, user_id: str, context_type: str) -> bool:
        """세션의 메시지만 삭제 (세션 유지)"""
        session = self.get_session(user_id, context_type)
        if session:
            session.messages = []
            self.logger.info(f"[Session] CLEAR messages: {user_id}:{context_type}")
            return self.save_session(session)
        return False

    def get_session_info(self, user_id: str, context_type: str) -> Optional[dict]:
        """세션 정보 요약"""
        session = self.get_session(user_id, context_type)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "context_type": session.context_type,
            "skill_name": session.skill_name,
            "message_count": len(session.messages),
            "context": session.context,
            "created_at": session.created_at,
            "updated_at": session.updated_at
        }

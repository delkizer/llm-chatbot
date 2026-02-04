"""
Chat Service

LLM 채팅 비즈니스 로직을 담당합니다.
- SKILL 파일 로드
- 세션 관리 (대화 히스토리)
- OllamaClient를 통한 LLM 호출
"""

import os
from pathlib import Path
from typing import Optional, AsyncGenerator
from dataclasses import dataclass

from class_config.class_env import Config
from class_lib.ollama_client import OllamaClient, ChatResponse
from class_lib.session_client import SessionClient, ChatSession


@dataclass
class ChatResult:
    """채팅 결과"""
    content: str
    session_id: str
    model: str
    response_time_ms: float
    tokens: dict
    skill_name: str
    message_count: int

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "session_id": self.session_id,
            "model": self.model,
            "response_time_ms": self.response_time_ms,
            "tokens": self.tokens,
            "skill_name": self.skill_name,
            "message_count": self.message_count
        }


class SkillLoader:
    """SKILL 파일 로더"""

    def __init__(self, logger, skills_dir: str = None):
        self.logger = logger
        self.config = Config()

        # skills 디렉토리 경로
        if skills_dir:
            self.skills_dir = Path(skills_dir)
        else:
            base_dir = Path(self.config.project_home_path or ".")
            self.skills_dir = base_dir / "skills"

        self._cache: dict[str, str] = {}
        self.logger.info(f"SkillLoader 초기화: {self.skills_dir}")

    def load(self, skill_name: str, use_cache: bool = True) -> Optional[str]:
        """
        SKILL 파일 로드

        Args:
            skill_name: 스킬 이름 (예: "badminton")
            use_cache: 캐시 사용 여부

        Returns:
            시스템 프롬프트 문자열
        """
        # 캐시 확인
        if use_cache and skill_name in self._cache:
            self.logger.debug(f"[Skill] Cache hit: {skill_name}")
            return self._cache[skill_name]

        # 파일 경로
        skill_file = self.skills_dir / f"{skill_name}.md"
        base_file = self.skills_dir / "_base.md"

        self.logger.info(f"[Skill] Loading: {skill_name}")

        # _base.md 로드
        base_content = ""
        if base_file.exists():
            base_content = base_file.read_text(encoding="utf-8")
            self.logger.debug(f"[Skill] Base loaded: {len(base_content)} chars")

        # 스킬 파일 로드
        skill_content = ""
        if skill_file.exists():
            skill_content = skill_file.read_text(encoding="utf-8")
            self.logger.info(f"[Skill] Loaded: {skill_name}.md ({len(skill_content)} chars)")
        else:
            self.logger.warning(f"[Skill] Not found: {skill_file}")

        # 합치기 (base + skill)
        combined = ""
        if base_content and skill_content:
            combined = f"{base_content}\n\n---\n\n{skill_content}"
        elif skill_content:
            combined = skill_content
        elif base_content:
            combined = base_content
        else:
            self.logger.warning(f"[Skill] No skill content for: {skill_name}")
            return None

        # 캐시 저장
        self._cache[skill_name] = combined
        self.logger.info(f"[Skill] Combined: {len(combined)} chars")

        return combined

    def clear_cache(self, skill_name: str = None):
        """캐시 삭제"""
        if skill_name:
            self._cache.pop(skill_name, None)
            self.logger.info(f"[Skill] Cache cleared: {skill_name}")
        else:
            self._cache.clear()
            self.logger.info("[Skill] All cache cleared")

    def list_skills(self) -> list[str]:
        """사용 가능한 스킬 목록"""
        if not self.skills_dir.exists():
            return []

        skills = []
        for f in self.skills_dir.glob("*.md"):
            if not f.name.startswith("_"):
                skills.append(f.stem)

        self.logger.debug(f"[Skill] Available: {skills}")
        return skills


class ChatService:
    """
    채팅 서비스

    사용법:
        from class_lib.chat_service import ChatService
        from class_config.class_log import ConfigLogger

        logger = ConfigLogger('llm_log', 365).get_logger('chat')
        service = ChatService(logger)

        # 채팅
        result = await service.chat(
            user_id="user123",
            message="안세영 선수 분석해줘",
            context_type="badminton"
        )

        # 스트리밍 채팅
        async for chunk in service.chat_stream(
            user_id="user123",
            message="안세영 선수 분석해줘",
            context_type="badminton"
        ):
            print(chunk, end="")
    """

    def __init__(self, logger, skills_dir: str = None):
        self.logger = logger
        self.config = Config()

        # 의존성 초기화
        self.ollama = OllamaClient(logger)
        self.session = SessionClient(logger)
        self.skill_loader = SkillLoader(logger, skills_dir)

        # 설정
        self.max_history_messages = 10  # 대화 히스토리 최대 메시지 수

        self._log_init()

    def _log_init(self):
        """초기화 로그"""
        self.logger.info("=" * 60)
        self.logger.info("ChatService 초기화")
        self.logger.info(f"  ollama_model: {self.ollama.model}")
        self.logger.info(f"  max_history: {self.max_history_messages}")
        self.logger.info(f"  skills: {self.skill_loader.list_skills()}")
        self.logger.info("=" * 60)

    async def health_check(self) -> dict:
        """서비스 상태 확인"""
        ollama_ok = await self.ollama.health_check()
        redis_ok = self.session.ping()

        status = {
            "ollama": "ok" if ollama_ok else "error",
            "redis": "ok" if redis_ok else "error",
            "skills": self.skill_loader.list_skills(),
            "healthy": ollama_ok and redis_ok
        }

        self.logger.info(f"[Health] ollama={status['ollama']}, redis={status['redis']}")
        return status

    async def chat(
        self,
        user_id: str,
        message: str,
        context_type: str = "badminton",
        skill_name: str = None,
        context: dict = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> ChatResult:
        """
        채팅 요청 (비스트리밍)

        Args:
            user_id: 사용자 ID
            message: 사용자 메시지
            context_type: 컨텍스트 유형 (badminton, baseball 등)
            skill_name: 스킬 이름 (기본: context_type)
            context: 추가 컨텍스트 (match_id, player_id 등)
            temperature: 생성 다양성
            max_tokens: 최대 생성 토큰 수

        Returns:
            ChatResult: 채팅 결과
        """
        self.logger.info("=" * 60)
        self.logger.info(f"[Chat] START user={user_id}, context={context_type}")
        self.logger.info(f"[Chat] Message: {message[:100]}{'...' if len(message) > 100 else ''}")

        # 스킬 이름 결정
        skill = skill_name or context_type

        # 세션 조회/생성
        session = self.session.get_or_create_session(
            user_id=user_id,
            context_type=context_type,
            skill_name=skill,
            context=context
        )
        self.logger.info(f"[Chat] Session: {session.session_id}, history={len(session.messages)}")

        # SKILL 로드
        system_prompt = self.skill_loader.load(skill)
        if not system_prompt:
            self.logger.warning(f"[Chat] No skill found for: {skill}, using base")
            system_prompt = self.skill_loader.load("_base")

        # 사용자 메시지 추가
        session.add_message("user", message)

        # LLM 호출용 메시지 구성
        messages = session.get_messages_for_llm(self.max_history_messages)
        self.logger.info(f"[Chat] LLM messages: {len(messages)}")

        # LLM 호출
        response = await self.ollama.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # 응답 저장
        session.add_message("assistant", response.content)
        self.session.save_session(session)

        # 결과 생성
        result = ChatResult(
            content=response.content,
            session_id=session.session_id,
            model=response.model,
            response_time_ms=response.response_time_ms,
            tokens={
                "prompt": response.prompt_tokens,
                "completion": response.completion_tokens,
                "total": response.total_tokens
            },
            skill_name=skill,
            message_count=len(session.messages)
        )

        self.logger.info(
            f"[Chat] DONE: {len(response.content)} chars, "
            f"{response.total_tokens} tokens, "
            f"{response.response_time_ms:.1f}ms"
        )
        self.logger.info("=" * 60)

        return result

    async def chat_stream(
        self,
        user_id: str,
        message: str,
        context_type: str = "badminton",
        skill_name: str = None,
        context: dict = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 채팅 요청

        Args:
            (chat과 동일)

        Yields:
            str: 생성된 텍스트 청크
        """
        self.logger.info("=" * 60)
        self.logger.info(f"[ChatStream] START user={user_id}, context={context_type}")
        self.logger.info(f"[ChatStream] Message: {message[:100]}{'...' if len(message) > 100 else ''}")

        # 스킬 이름 결정
        skill = skill_name or context_type

        # 세션 조회/생성
        session = self.session.get_or_create_session(
            user_id=user_id,
            context_type=context_type,
            skill_name=skill,
            context=context
        )

        # SKILL 로드
        system_prompt = self.skill_loader.load(skill)
        if not system_prompt:
            system_prompt = self.skill_loader.load("_base")

        # 사용자 메시지 추가
        session.add_message("user", message)

        # LLM 호출용 메시지 구성
        messages = session.get_messages_for_llm(self.max_history_messages)

        # 스트리밍 응답 수집
        full_response = ""

        async for chunk in self.ollama.chat_stream(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            full_response += chunk
            yield chunk

        # 응답 저장
        session.add_message("assistant", full_response)
        self.session.save_session(session)

        self.logger.info(f"[ChatStream] DONE: {len(full_response)} chars")
        self.logger.info("=" * 60)

    def clear_history(self, user_id: str, context_type: str) -> bool:
        """대화 히스토리 삭제"""
        self.logger.info(f"[Chat] Clear history: {user_id}:{context_type}")
        return self.session.clear_messages(user_id, context_type)

    def delete_session(self, user_id: str, context_type: str) -> bool:
        """세션 삭제"""
        self.logger.info(f"[Chat] Delete session: {user_id}:{context_type}")
        return self.session.delete_session(user_id, context_type)

    def get_session_info(self, user_id: str, context_type: str) -> Optional[dict]:
        """세션 정보 조회"""
        return self.session.get_session_info(user_id, context_type)

    def reload_skill(self, skill_name: str = None):
        """SKILL 캐시 새로고침"""
        self.skill_loader.clear_cache(skill_name)
        self.logger.info(f"[Chat] Skill reloaded: {skill_name or 'all'}")

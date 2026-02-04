"""
Ollama API Client

Ollama 서버와 HTTP 통신을 담당하는 클라이언트 클래스.
개발 단계이므로 상세한 로깅을 포함합니다.
"""

import time
import json
from typing import AsyncGenerator, Optional
from dataclasses import dataclass, field

import httpx

from class_config.class_env import Config


# =============================================================================
# 예외 클래스
# =============================================================================

class OllamaError(Exception):
    """Ollama 기본 예외"""
    pass


class OllamaConnectionError(OllamaError):
    """연결 실패"""
    pass


class OllamaModelNotFoundError(OllamaError):
    """모델 없음"""
    pass


class OllamaTimeoutError(OllamaError):
    """타임아웃"""
    pass


class OllamaAPIError(OllamaError):
    """API 에러 응답"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")


# =============================================================================
# 응답 데이터 클래스
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


# =============================================================================
# Ollama Client
# =============================================================================

class OllamaClient:
    """
    Ollama API 클라이언트

    사용법:
        from class_lib.ollama_client import OllamaClient
        from class_config.class_log import ConfigLogger

        logger = ConfigLogger('llm_log', 365).get_logger('ollama')
        client = OllamaClient(logger)

        # 비스트리밍
        response = await client.chat([{"role": "user", "content": "안녕"}])

        # 스트리밍
        async for chunk in client.chat_stream([{"role": "user", "content": "안녕"}]):
            print(chunk, end="")
    """

    def __init__(self, logger):
        self.config = Config()
        self.logger = logger

        # 설정값 로드
        self.base_url = self.config.ollama_host.rstrip('/')
        self.model = self.config.ollama_model
        self.timeout = self.config.ollama_timeout
        self.debug = self.config.ollama_debug

        # 요청 카운터 (디버깅용)
        self._request_count = 0

        self._log_init()

    def _log_init(self):
        """초기화 로그"""
        self.logger.info("=" * 60)
        self.logger.info("OllamaClient 초기화")
        self.logger.info(f"  base_url: {self.base_url}")
        self.logger.info(f"  model: {self.model}")
        self.logger.info(f"  timeout: {self.timeout}s")
        self.logger.info(f"  debug: {self.debug}")
        self.logger.info("=" * 60)

    def _get_request_id(self) -> str:
        """요청 ID 생성"""
        self._request_count += 1
        return f"REQ-{self._request_count:04d}"

    def _log_request(self, req_id: str, method: str, endpoint: str, body: dict = None):
        """요청 로그"""
        self.logger.info(f"[{req_id}] >>> {method} {endpoint}")
        if self.debug and body:
            # 민감 정보 마스킹 (필요시)
            body_str = json.dumps(body, ensure_ascii=False, indent=2)
            # 너무 길면 truncate
            if len(body_str) > 1000:
                body_str = body_str[:1000] + "\n... (truncated)"
            self.logger.debug(f"[{req_id}] Request Body:\n{body_str}")

    def _log_response(self, req_id: str, status: int, elapsed_ms: float, body: dict = None):
        """응답 로그"""
        status_emoji = "OK" if 200 <= status < 300 else "ERR"
        self.logger.info(f"[{req_id}] <<< {status} {status_emoji} ({elapsed_ms:.1f}ms)")
        if self.debug and body:
            body_str = json.dumps(body, ensure_ascii=False, indent=2)
            if len(body_str) > 1000:
                body_str = body_str[:1000] + "\n... (truncated)"
            self.logger.debug(f"[{req_id}] Response Body:\n{body_str}")

    def _log_error(self, req_id: str, error: Exception, elapsed_ms: float = 0):
        """에러 로그"""
        self.logger.error(f"[{req_id}] !!! ERROR ({elapsed_ms:.1f}ms): {type(error).__name__}: {error}")

    def _log_stream_start(self, req_id: str):
        """스트리밍 시작 로그"""
        self.logger.info(f"[{req_id}] ~~~ Streaming started")

    def _log_stream_chunk(self, req_id: str, chunk_num: int, content: str):
        """스트리밍 청크 로그 (debug 모드에서만)"""
        if self.debug:
            preview = content[:50] + "..." if len(content) > 50 else content
            self.logger.debug(f"[{req_id}] chunk#{chunk_num}: {repr(preview)}")

    def _log_stream_end(self, req_id: str, total_chunks: int, elapsed_ms: float, total_content_length: int):
        """스트리밍 종료 로그"""
        self.logger.info(
            f"[{req_id}] ~~~ Streaming ended: "
            f"{total_chunks} chunks, {total_content_length} chars, {elapsed_ms:.1f}ms"
        )

    # =========================================================================
    # Public API
    # =========================================================================

    async def health_check(self) -> bool:
        """
        Ollama 서버 상태 확인

        Returns:
            bool: 서버가 정상이면 True
        """
        req_id = self._get_request_id()
        endpoint = f"{self.base_url}/api/tags"
        start_time = time.time()

        self._log_request(req_id, "GET", endpoint)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(endpoint)
                elapsed_ms = (time.time() - start_time) * 1000

                self._log_response(req_id, response.status_code, elapsed_ms)

                if response.status_code == 200:
                    self.logger.info(f"[{req_id}] Health check PASSED")
                    return True
                else:
                    self.logger.warning(f"[{req_id}] Health check FAILED: status={response.status_code}")
                    return False

        except httpx.ConnectError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            self.logger.error(f"[{req_id}] Ollama 서버에 연결할 수 없습니다: {self.base_url}")
            return False
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            return False

    async def list_models(self) -> list[ModelInfo]:
        """
        사용 가능한 모델 목록 조회

        Returns:
            list[ModelInfo]: 모델 정보 목록
        """
        req_id = self._get_request_id()
        endpoint = f"{self.base_url}/api/tags"
        start_time = time.time()

        self._log_request(req_id, "GET", endpoint)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint)
                elapsed_ms = (time.time() - start_time) * 1000

                self._log_response(req_id, response.status_code, elapsed_ms, response.json())

                if response.status_code != 200:
                    raise OllamaAPIError(response.status_code, response.text)

                data = response.json()
                models = []
                for m in data.get("models", []):
                    model_info = ModelInfo(
                        name=m.get("name", ""),
                        size=m.get("size", 0),
                        digest=m.get("digest", ""),
                        modified_at=m.get("modified_at", ""),
                        details=m.get("details", {})
                    )
                    models.append(model_info)
                    self.logger.info(f"[{req_id}] Found model: {model_info.name} ({model_info.size / 1e9:.2f}GB)")

                self.logger.info(f"[{req_id}] Total {len(models)} models available")
                return models

        except httpx.ConnectError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            raise OllamaConnectionError(f"서버 연결 실패: {self.base_url}") from e
        except httpx.TimeoutException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            raise OllamaTimeoutError(f"타임아웃 ({self.timeout}s)") from e

    async def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **options
    ) -> ChatResponse:
        """
        채팅 요청 (비스트리밍)

        Args:
            messages: 대화 메시지 목록 [{"role": "user", "content": "..."}]
            system_prompt: 시스템 프롬프트 (SKILL 파일 내용)
            model: 사용할 모델 (기본: config에서 설정한 모델)
            temperature: 생성 다양성 (0.0 ~ 1.0)
            max_tokens: 최대 생성 토큰 수
            **options: 추가 Ollama 옵션

        Returns:
            ChatResponse: 응답 객체 (content, 메타데이터 포함)
        """
        req_id = self._get_request_id()
        endpoint = f"{self.base_url}/api/chat"
        use_model = model or self.model
        start_time = time.time()

        # 요청 바디 구성
        body = {
            "model": use_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **options
            }
        }

        # 시스템 프롬프트 추가
        if system_prompt:
            body["messages"] = [{"role": "system", "content": system_prompt}] + messages
            self.logger.info(f"[{req_id}] System prompt applied ({len(system_prompt)} chars)")

        self._log_request(req_id, "POST", endpoint, body)
        self.logger.info(f"[{req_id}] Model: {use_model}, Messages: {len(messages)}, Temp: {temperature}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, json=body)
                elapsed_ms = (time.time() - start_time) * 1000

                if response.status_code == 404:
                    self._log_error(req_id, OllamaModelNotFoundError(use_model), elapsed_ms)
                    raise OllamaModelNotFoundError(f"모델을 찾을 수 없습니다: {use_model}")

                if response.status_code != 200:
                    self._log_error(req_id, OllamaAPIError(response.status_code, response.text), elapsed_ms)
                    raise OllamaAPIError(response.status_code, response.text)

                data = response.json()
                self._log_response(req_id, response.status_code, elapsed_ms, data)

                # 응답 파싱
                message = data.get("message", {})
                content = message.get("content", "")

                # 토큰 정보
                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)

                chat_response = ChatResponse(
                    content=content,
                    model=data.get("model", use_model),
                    response_time_ms=elapsed_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    done=data.get("done", True),
                    done_reason=data.get("done_reason", "")
                )

                # 결과 요약 로그
                self.logger.info(
                    f"[{req_id}] Chat completed: "
                    f"{len(content)} chars, "
                    f"{chat_response.total_tokens} tokens, "
                    f"{elapsed_ms:.1f}ms"
                )

                return chat_response

        except httpx.ConnectError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            raise OllamaConnectionError(f"서버 연결 실패: {self.base_url}") from e
        except httpx.TimeoutException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            raise OllamaTimeoutError(f"타임아웃 ({self.timeout}s)") from e
        except (OllamaModelNotFoundError, OllamaAPIError):
            raise
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            raise OllamaError(f"예상치 못한 에러: {e}") from e

    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **options
    ) -> AsyncGenerator[str, None]:
        """
        채팅 요청 (스트리밍)

        Args:
            messages: 대화 메시지 목록
            system_prompt: 시스템 프롬프트
            model: 사용할 모델
            temperature: 생성 다양성
            max_tokens: 최대 생성 토큰 수
            **options: 추가 옵션

        Yields:
            str: 생성된 텍스트 청크
        """
        req_id = self._get_request_id()
        endpoint = f"{self.base_url}/api/chat"
        use_model = model or self.model
        start_time = time.time()

        # 요청 바디 구성
        body = {
            "model": use_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **options
            }
        }

        if system_prompt:
            body["messages"] = [{"role": "system", "content": system_prompt}] + messages
            self.logger.info(f"[{req_id}] System prompt applied ({len(system_prompt)} chars)")

        self._log_request(req_id, "POST (stream)", endpoint, body)
        self.logger.info(f"[{req_id}] Model: {use_model}, Messages: {len(messages)}, Temp: {temperature}")

        chunk_count = 0
        total_content = ""

        try:
            async with httpx.AsyncClient(timeout=None) as client:  # 스트리밍은 타임아웃 없음
                async with client.stream("POST", endpoint, json=body) as response:
                    if response.status_code == 404:
                        raise OllamaModelNotFoundError(f"모델을 찾을 수 없습니다: {use_model}")

                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise OllamaAPIError(response.status_code, error_text.decode())

                    self._log_stream_start(req_id)

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            self.logger.warning(f"[{req_id}] Invalid JSON line: {line[:100]}")
                            continue

                        message = data.get("message", {})
                        content = message.get("content", "")

                        if content:
                            chunk_count += 1
                            total_content += content
                            self._log_stream_chunk(req_id, chunk_count, content)
                            yield content

                        # 스트리밍 종료
                        if data.get("done", False):
                            elapsed_ms = (time.time() - start_time) * 1000
                            self._log_stream_end(req_id, chunk_count, elapsed_ms, len(total_content))

                            # 최종 메타데이터 로그
                            prompt_tokens = data.get("prompt_eval_count", 0)
                            completion_tokens = data.get("eval_count", 0)
                            self.logger.info(
                                f"[{req_id}] Stream stats: "
                                f"prompt_tokens={prompt_tokens}, "
                                f"completion_tokens={completion_tokens}"
                            )
                            break

        except httpx.ConnectError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            raise OllamaConnectionError(f"서버 연결 실패: {self.base_url}") from e
        except (OllamaModelNotFoundError, OllamaAPIError):
            raise
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            raise OllamaError(f"스트리밍 에러: {e}") from e

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        **options
    ) -> ChatResponse:
        """
        단순 텍스트 생성 (chat 형식이 아닌 단일 프롬프트)

        Args:
            prompt: 프롬프트 텍스트
            system_prompt: 시스템 프롬프트
            model: 사용할 모델
            **options: 추가 옵션

        Returns:
            ChatResponse: 응답 객체
        """
        req_id = self._get_request_id()
        endpoint = f"{self.base_url}/api/generate"
        use_model = model or self.model
        start_time = time.time()

        body = {
            "model": use_model,
            "prompt": prompt,
            "stream": False,
            "options": options
        }

        if system_prompt:
            body["system"] = system_prompt
            self.logger.info(f"[{req_id}] System prompt applied ({len(system_prompt)} chars)")

        self._log_request(req_id, "POST", endpoint, body)
        self.logger.info(f"[{req_id}] Model: {use_model}, Prompt: {len(prompt)} chars")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, json=body)
                elapsed_ms = (time.time() - start_time) * 1000

                if response.status_code == 404:
                    raise OllamaModelNotFoundError(f"모델을 찾을 수 없습니다: {use_model}")

                if response.status_code != 200:
                    raise OllamaAPIError(response.status_code, response.text)

                data = response.json()
                self._log_response(req_id, response.status_code, elapsed_ms, data)

                content = data.get("response", "")

                chat_response = ChatResponse(
                    content=content,
                    model=data.get("model", use_model),
                    response_time_ms=elapsed_ms,
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                    done=data.get("done", True),
                    done_reason=data.get("done_reason", "")
                )

                self.logger.info(
                    f"[{req_id}] Generate completed: "
                    f"{len(content)} chars, "
                    f"{chat_response.total_tokens} tokens, "
                    f"{elapsed_ms:.1f}ms"
                )

                return chat_response

        except httpx.ConnectError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            raise OllamaConnectionError(f"서버 연결 실패: {self.base_url}") from e
        except httpx.TimeoutException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            raise OllamaTimeoutError(f"타임아웃 ({self.timeout}s)") from e
        except (OllamaModelNotFoundError, OllamaAPIError):
            raise
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(req_id, e, elapsed_ms)
            raise OllamaError(f"예상치 못한 에러: {e}") from e

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def check_model_exists(self, model_name: Optional[str] = None) -> bool:
        """
        특정 모델이 존재하는지 확인

        Args:
            model_name: 확인할 모델 이름 (기본: config 모델)

        Returns:
            bool: 모델 존재 여부
        """
        target_model = model_name or self.model
        req_id = self._get_request_id()

        self.logger.info(f"[{req_id}] Checking model exists: {target_model}")

        try:
            models = await self.list_models()
            exists = any(m.name == target_model or m.name.startswith(target_model.split(':')[0]) for m in models)

            if exists:
                self.logger.info(f"[{req_id}] Model '{target_model}' EXISTS")
            else:
                self.logger.warning(f"[{req_id}] Model '{target_model}' NOT FOUND")
                available = [m.name for m in models]
                self.logger.info(f"[{req_id}] Available models: {available}")

            return exists
        except Exception as e:
            self.logger.error(f"[{req_id}] Failed to check model: {e}")
            return False

    def get_status_summary(self) -> dict:
        """
        클라이언트 상태 요약

        Returns:
            dict: 상태 정보
        """
        return {
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "debug": self.debug,
            "request_count": self._request_count
        }

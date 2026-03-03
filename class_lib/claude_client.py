"""
Claude API Client

Claude Messages API와 HTTP 통신을 담당하는 클라이언트 클래스.
프록시 서버(proxy_server.py)를 경유하여 API 키 없이 동작합니다.
"""

import time
import json
from typing import AsyncGenerator, Optional

import httpx

from class_config.class_env import Config
from class_lib.llm_types import (
    ChatResponse,
    LLMError, LLMConnectionError, LLMTimeoutError, LLMAPIError,
)


class ClaudeClient:
    """
    Claude API 클라이언트

    프록시 서버를 경유하므로 API 키가 필요 없습니다.

    사용법:
        from class_lib.claude_client import ClaudeClient
        from class_config.class_log import ConfigLogger

        logger = ConfigLogger('llm_log', 365).get_logger('claude')
        client = ClaudeClient(logger)

        # 비스트리밍
        response = await client.chat([{"role": "user", "content": "안녕"}])

        # 스트리밍
        async for chunk in client.chat_stream([{"role": "user", "content": "안녕"}]):
            print(chunk, end="")
    """

    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(self, logger):
        self.config = Config()
        self.logger = logger

        # 설정값 로드
        self.base_url = self.config.claude_endpoint.rstrip('/')
        self.model = self.config.claude_model
        self.timeout = self.config.claude_timeout
        self.max_tokens = self.config.claude_max_tokens

        # 요청 카운터 (디버깅용)
        self._request_count = 0

        self._log_init()

    def _log_init(self):
        """초기화 로그"""
        self.logger.info("=" * 60)
        self.logger.info("ClaudeClient 초기화")
        self.logger.info(f"  base_url: {self.base_url}")
        self.logger.info(f"  model: {self.model}")
        self.logger.info(f"  timeout: {self.timeout}s")
        self.logger.info(f"  max_tokens: {self.max_tokens}")
        self.logger.info("=" * 60)

    def _get_request_id(self) -> str:
        """요청 ID 생성"""
        self._request_count += 1
        return f"REQ-{self._request_count:04d}"

    def _get_headers(self) -> dict:
        """공통 요청 헤더"""
        return {
            "content-type": "application/json",
            "anthropic-version": self.ANTHROPIC_VERSION,
        }

    def _build_body(
        self,
        messages: list[dict],
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> dict:
        """요청 바디 구성"""
        use_model = model or self.model
        use_max_tokens = max_tokens or self.max_tokens

        # system prompt는 messages가 아닌 별도 필드
        # messages에서 system role 제거
        filtered_messages = [
            m for m in messages if m.get("role") != "system"
        ]

        body = {
            "model": use_model,
            "messages": filtered_messages,
            "max_tokens": use_max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        if system_prompt:
            body["system"] = system_prompt

        return body

    # =========================================================================
    # Public API
    # =========================================================================

    async def health_check(self) -> bool:
        """
        프록시 서버 상태 확인

        Returns:
            bool: 프록시가 정상이면 True
        """
        req_id = self._get_request_id()
        endpoint = f"{self.base_url}/health"
        start_time = time.time()

        self.logger.info(f"[{req_id}] >>> GET {endpoint}")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(endpoint)
                elapsed_ms = (time.time() - start_time) * 1000

                self.logger.info(
                    f"[{req_id}] <<< {response.status_code} ({elapsed_ms:.1f}ms)"
                )

                if response.status_code == 200:
                    self.logger.info(f"[{req_id}] Health check PASSED")
                    return True
                else:
                    self.logger.warning(
                        f"[{req_id}] Health check FAILED: status={response.status_code}"
                    )
                    return False

        except httpx.ConnectError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"[{req_id}] !!! ERROR ({elapsed_ms:.1f}ms): {type(e).__name__}: {e}"
            )
            self.logger.error(
                f"[{req_id}] 프록시 서버에 연결할 수 없습니다: {self.base_url}"
            )
            return False
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"[{req_id}] !!! ERROR ({elapsed_ms:.1f}ms): {type(e).__name__}: {e}"
            )
            return False

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
            **options: 무시됨 (OllamaClient 호환용)

        Returns:
            ChatResponse: 응답 객체 (content, 메타데이터 포함)
        """
        req_id = self._get_request_id()
        endpoint = f"{self.base_url}/v1/messages"
        start_time = time.time()

        body = self._build_body(
            messages, system_prompt, model, temperature, max_tokens, stream=False
        )

        self.logger.info(f"[{req_id}] >>> POST {endpoint}")
        self.logger.info(
            f"[{req_id}] Model: {body['model']}, "
            f"Messages: {len(body['messages'])}, Temp: {temperature}"
        )
        if system_prompt:
            self.logger.info(
                f"[{req_id}] System prompt applied ({len(system_prompt)} chars)"
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint, json=body, headers=self._get_headers()
                )
                elapsed_ms = (time.time() - start_time) * 1000

                self.logger.info(
                    f"[{req_id}] <<< {response.status_code} ({elapsed_ms:.1f}ms)"
                )

                if response.status_code != 200:
                    error_body = response.json()
                    error_msg = error_body.get("error", {}).get(
                        "message", response.text
                    )
                    self.logger.error(f"[{req_id}] API Error: {error_msg}")
                    raise LLMAPIError(response.status_code, error_msg)

                data = response.json()

                # Claude 응답 파싱: content[0].text
                content_blocks = data.get("content", [])
                content = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        content += block.get("text", "")

                # 토큰 정보
                usage = data.get("usage", {})
                prompt_tokens = usage.get("input_tokens", 0)
                completion_tokens = usage.get("output_tokens", 0)

                chat_response = ChatResponse(
                    content=content,
                    model=data.get("model", body["model"]),
                    response_time_ms=elapsed_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    done=True,
                    done_reason=data.get("stop_reason", ""),
                )

                self.logger.info(
                    f"[{req_id}] Chat completed: "
                    f"{len(content)} chars, "
                    f"{chat_response.total_tokens} tokens, "
                    f"{elapsed_ms:.1f}ms"
                )

                return chat_response

        except httpx.ConnectError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"[{req_id}] !!! ERROR ({elapsed_ms:.1f}ms): {type(e).__name__}: {e}"
            )
            raise LLMConnectionError(
                f"프록시 서버 연결 실패: {self.base_url}"
            ) from e
        except httpx.TimeoutException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"[{req_id}] !!! ERROR ({elapsed_ms:.1f}ms): {type(e).__name__}: {e}"
            )
            raise LLMTimeoutError(f"타임아웃 ({self.timeout}s)") from e
        except LLMAPIError:
            raise
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"[{req_id}] !!! ERROR ({elapsed_ms:.1f}ms): {type(e).__name__}: {e}"
            )
            raise LLMError(f"예상치 못한 에러: {e}") from e

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

        Claude SSE 형식:
            event: content_block_delta
            data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"..."}}

        Args:
            messages: 대화 메시지 목록
            system_prompt: 시스템 프롬프트
            model: 사용할 모델
            temperature: 생성 다양성
            max_tokens: 최대 생성 토큰 수
            **options: 무시됨 (OllamaClient 호환용)

        Yields:
            str: 생성된 텍스트 청크
        """
        req_id = self._get_request_id()
        endpoint = f"{self.base_url}/v1/messages"
        start_time = time.time()

        body = self._build_body(
            messages, system_prompt, model, temperature, max_tokens, stream=True
        )

        self.logger.info(f"[{req_id}] >>> POST (stream) {endpoint}")
        self.logger.info(
            f"[{req_id}] Model: {body['model']}, "
            f"Messages: {len(body['messages'])}, Temp: {temperature}"
        )
        if system_prompt:
            self.logger.info(
                f"[{req_id}] System prompt applied ({len(system_prompt)} chars)"
            )

        chunk_count = 0
        total_content = ""

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST", endpoint, json=body, headers=self._get_headers()
                ) as response:
                    if response.status_code != 200:
                        error_bytes = await response.aread()
                        raise LLMAPIError(
                            response.status_code, error_bytes.decode()
                        )

                    self.logger.info(f"[{req_id}] ~~~ Streaming started")

                    event_type = ""
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue

                        # SSE 파싱
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                            continue

                        if not line.startswith("data:"):
                            continue

                        data_str = line[5:].strip()
                        if not data_str:
                            continue

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        # content_block_delta → 텍스트 추출
                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    chunk_count += 1
                                    total_content += text
                                    yield text

                        # message_stop → 스트리밍 종료
                        elif event_type == "message_stop":
                            break

                        # message_delta → 토큰 사용량 (로그용)
                        elif event_type == "message_delta":
                            usage = data.get("usage", {})
                            output_tokens = usage.get("output_tokens", 0)
                            self.logger.info(
                                f"[{req_id}] Stream stats: "
                                f"output_tokens={output_tokens}"
                            )

                    elapsed_ms = (time.time() - start_time) * 1000
                    self.logger.info(
                        f"[{req_id}] ~~~ Streaming ended: "
                        f"{chunk_count} chunks, "
                        f"{len(total_content)} chars, "
                        f"{elapsed_ms:.1f}ms"
                    )

        except httpx.ConnectError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"[{req_id}] !!! ERROR ({elapsed_ms:.1f}ms): {type(e).__name__}: {e}"
            )
            raise LLMConnectionError(
                f"프록시 서버 연결 실패: {self.base_url}"
            ) from e
        except LLMAPIError:
            raise
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"[{req_id}] !!! ERROR ({elapsed_ms:.1f}ms): {type(e).__name__}: {e}"
            )
            raise LLMError(f"스트리밍 에러: {e}") from e

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
            "max_tokens": self.max_tokens,
            "request_count": self._request_count,
        }

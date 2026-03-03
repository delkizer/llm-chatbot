"""
LLM Client Factory

LLM_PROVIDER 설정에 따라 적절한 클라이언트를 반환하는 팩토리 함수.
"""

import importlib

from class_config.class_env import Config


KNOWN_PROVIDERS = {
    "ollama": {
        "module": "class_lib.ollama_client",
        "class_name": "OllamaClient",
        "config_keys": {"model": "ollama_model", "host": "ollama_host"},
    },
    "claude": {
        "module": "class_lib.claude_client",
        "class_name": "ClaudeClient",
        "config_keys": {"model": "claude_model", "endpoint": "claude_endpoint"},
    },
}


def create_llm_client(logger):
    """
    LLM 클라이언트 생성

    LLM_PROVIDER 환경변수에 따라 OllamaClient 또는 ClaudeClient를 반환합니다.
    lazy import로 사용하지 않는 클라이언트의 import 오버헤드를 방지합니다.

    Args:
        logger: 로거 인스턴스

    Returns:
        OllamaClient | ClaudeClient: LLM 클라이언트 인스턴스
    """
    config = Config()
    provider = config.llm_provider

    if provider == "claude":
        from class_lib.claude_client import ClaudeClient
        return ClaudeClient(logger)
    else:
        from class_lib.ollama_client import OllamaClient
        return OllamaClient(logger)


def create_llm_client_for_provider(provider_name: str, logger):
    """
    지정 provider 클라이언트 생성.

    KNOWN_PROVIDERS에서 module/class_name을 가져와 importlib로 동적 로드합니다.

    Args:
        provider_name: provider 이름 (예: "ollama", "claude")
        logger: 로거 인스턴스

    Returns:
        LLM 클라이언트 인스턴스

    Raises:
        ValueError: unknown provider인 경우
    """
    if provider_name not in KNOWN_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(KNOWN_PROVIDERS.keys())}")

    info = KNOWN_PROVIDERS[provider_name]
    module = importlib.import_module(info["module"])
    cls = getattr(module, info["class_name"])
    return cls(logger)


def get_provider_config_info(provider_name: str) -> dict:
    """
    provider 설정값 반환 (health 응답용)

    Args:
        provider_name: provider 이름 (예: "ollama", "claude")

    Returns:
        dict: provider 설정값 (model, host/endpoint 등)
    """
    if provider_name not in KNOWN_PROVIDERS:
        return {}

    config = Config()
    info = KNOWN_PROVIDERS[provider_name]
    result = {}
    for key, config_attr in info["config_keys"].items():
        result[key] = getattr(config, config_attr, None)
    return result

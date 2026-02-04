#!/usr/bin/env python3
"""
OllamaClient 테스트 스크립트

사용법:
    # 가상환경 활성화 후
    cd ~/work/llm-chatbot
    python scripts/test_ollama_client.py

    # 특정 테스트만 실행
    python scripts/test_ollama_client.py --test health
    python scripts/test_ollama_client.py --test models
    python scripts/test_ollama_client.py --test chat
    python scripts/test_ollama_client.py --test stream
    python scripts/test_ollama_client.py --test all
"""

import sys
import asyncio
import argparse
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from class_config.class_log import ConfigLogger
from class_lib.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)


def create_client():
    """OllamaClient 인스턴스 생성"""
    logger = ConfigLogger('ollama_test', 7).get_logger('test')
    return OllamaClient(logger)


async def test_health_check():
    """Health Check 테스트"""
    print("\n" + "=" * 60)
    print("TEST: Health Check")
    print("=" * 60)

    client = create_client()
    result = await client.health_check()

    print(f"\nResult: {'PASS' if result else 'FAIL'}")
    return result


async def test_list_models():
    """모델 목록 조회 테스트"""
    print("\n" + "=" * 60)
    print("TEST: List Models")
    print("=" * 60)

    client = create_client()

    try:
        models = await client.list_models()
        print(f"\nFound {len(models)} models:")
        for m in models:
            size_gb = m.size / 1e9 if m.size else 0
            print(f"  - {m.name} ({size_gb:.2f}GB)")
        return True
    except OllamaConnectionError as e:
        print(f"\nConnection Error: {e}")
        return False
    except Exception as e:
        print(f"\nError: {e}")
        return False


async def test_chat():
    """채팅 테스트 (비스트리밍)"""
    print("\n" + "=" * 60)
    print("TEST: Chat (non-streaming)")
    print("=" * 60)

    client = create_client()

    messages = [
        {"role": "user", "content": "안녕하세요! 간단히 자기소개 해주세요. (3문장 이내)"}
    ]

    try:
        response = await client.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=256
        )

        print(f"\n--- Response ---")
        print(response.content)
        print(f"\n--- Metadata ---")
        print(f"  Model: {response.model}")
        print(f"  Response Time: {response.response_time_ms:.1f}ms")
        print(f"  Tokens: prompt={response.prompt_tokens}, completion={response.completion_tokens}, total={response.total_tokens}")
        return True

    except OllamaModelNotFoundError as e:
        print(f"\nModel Not Found: {e}")
        return False
    except OllamaConnectionError as e:
        print(f"\nConnection Error: {e}")
        return False
    except OllamaTimeoutError as e:
        print(f"\nTimeout: {e}")
        return False
    except Exception as e:
        print(f"\nError: {e}")
        return False


async def test_chat_with_system_prompt():
    """시스템 프롬프트 적용 채팅 테스트"""
    print("\n" + "=" * 60)
    print("TEST: Chat with System Prompt")
    print("=" * 60)

    client = create_client()

    system_prompt = """당신은 배드민턴 전문 해설가입니다.
모든 답변은 배드민턴 관점에서 해주세요.
답변은 간결하게 3문장 이내로 해주세요."""

    messages = [
        {"role": "user", "content": "안세영 선수에 대해 알려주세요."}
    ]

    try:
        response = await client.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=512
        )

        print(f"\n--- System Prompt ---")
        print(system_prompt[:100] + "...")
        print(f"\n--- Response ---")
        print(response.content)
        print(f"\n--- Metadata ---")
        print(f"  Response Time: {response.response_time_ms:.1f}ms")
        print(f"  Tokens: {response.total_tokens}")
        return True

    except Exception as e:
        print(f"\nError: {e}")
        return False


async def test_chat_stream():
    """스트리밍 채팅 테스트"""
    print("\n" + "=" * 60)
    print("TEST: Chat (streaming)")
    print("=" * 60)

    client = create_client()

    messages = [
        {"role": "user", "content": "1부터 5까지 세어주세요. 각 숫자마다 한 줄씩 출력해주세요."}
    ]

    try:
        print(f"\n--- Streaming Response ---")
        full_response = ""
        chunk_count = 0

        async for chunk in client.chat_stream(
            messages=messages,
            temperature=0.3,
            max_tokens=256
        ):
            print(chunk, end="", flush=True)
            full_response += chunk
            chunk_count += 1

        print(f"\n\n--- Stats ---")
        print(f"  Total chunks: {chunk_count}")
        print(f"  Total length: {len(full_response)} chars")
        return True

    except OllamaConnectionError as e:
        print(f"\nConnection Error: {e}")
        return False
    except Exception as e:
        print(f"\nError: {e}")
        return False


async def test_generate():
    """단순 생성 테스트"""
    print("\n" + "=" * 60)
    print("TEST: Generate")
    print("=" * 60)

    client = create_client()

    prompt = "Python에서 리스트를 정렬하는 방법을 한 줄로 설명해주세요."

    try:
        response = await client.generate(
            prompt=prompt,
            temperature=0.5,
            num_predict=128
        )

        print(f"\n--- Prompt ---")
        print(prompt)
        print(f"\n--- Response ---")
        print(response.content)
        print(f"\n--- Metadata ---")
        print(f"  Response Time: {response.response_time_ms:.1f}ms")
        return True

    except Exception as e:
        print(f"\nError: {e}")
        return False


async def test_check_model():
    """모델 존재 확인 테스트"""
    print("\n" + "=" * 60)
    print("TEST: Check Model Exists")
    print("=" * 60)

    client = create_client()

    # 현재 설정된 모델 확인
    print(f"\nChecking configured model: {client.model}")
    exists = await client.check_model_exists()
    print(f"Result: {'EXISTS' if exists else 'NOT FOUND'}")

    # 없는 모델 확인
    print(f"\nChecking non-existent model: fake-model:latest")
    exists = await client.check_model_exists("fake-model:latest")
    print(f"Result: {'EXISTS' if exists else 'NOT FOUND'} (expected: NOT FOUND)")

    return True


async def run_all_tests():
    """모든 테스트 실행"""
    results = {}

    # 1. Health Check
    results['health'] = await test_health_check()
    if not results['health']:
        print("\n[STOP] Health check failed. Ollama server may not be running.")
        return results

    # 2. List Models
    results['models'] = await test_list_models()

    # 3. Check Model
    results['check_model'] = await test_check_model()

    # 4. Chat (non-streaming)
    results['chat'] = await test_chat()

    # 5. Chat with System Prompt
    results['chat_system'] = await test_chat_with_system_prompt()

    # 6. Chat (streaming)
    results['stream'] = await test_chat_stream()

    # 7. Generate
    results['generate'] = await test_generate()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} passed")

    return results


def main():
    parser = argparse.ArgumentParser(description='OllamaClient 테스트')
    parser.add_argument(
        '--test',
        choices=['health', 'models', 'chat', 'stream', 'generate', 'check', 'system', 'all'],
        default='all',
        help='실행할 테스트 (기본: all)'
    )
    args = parser.parse_args()

    test_map = {
        'health': test_health_check,
        'models': test_list_models,
        'chat': test_chat,
        'stream': test_chat_stream,
        'generate': test_generate,
        'check': test_check_model,
        'system': test_chat_with_system_prompt,
        'all': run_all_tests
    }

    print("=" * 60)
    print("OllamaClient Test Script")
    print("=" * 60)

    asyncio.run(test_map[args.test]())


if __name__ == "__main__":
    main()

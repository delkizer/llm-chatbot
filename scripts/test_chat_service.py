#!/usr/bin/env python3
"""
ChatService 테스트 스크립트

사용법:
    cd ~/work/llm-chatbot
    source .venv/bin/activate
    python scripts/test_chat_service.py

    # 특정 테스트만
    python scripts/test_chat_service.py --test health
    python scripts/test_chat_service.py --test chat
    python scripts/test_chat_service.py --test stream
    python scripts/test_chat_service.py --test session
    python scripts/test_chat_service.py --test skill
"""

import sys
import asyncio
import argparse
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from class_config.class_log import ConfigLogger
from class_lib.chat_service import ChatService


def create_service():
    """ChatService 인스턴스 생성"""
    logger = ConfigLogger('chat_test', 7).get_logger('test')
    # skills 디렉토리 명시적 지정
    skills_dir = project_root / "skills"
    return ChatService(logger, skills_dir=str(skills_dir))


async def test_health_check():
    """Health Check 테스트"""
    print("\n" + "=" * 60)
    print("TEST: Health Check")
    print("=" * 60)

    service = create_service()
    status = await service.health_check()

    print(f"\nOllama: {status['ollama']}")
    print(f"Redis: {status['redis']}")
    print(f"Skills: {status['skills']}")
    print(f"Healthy: {status['healthy']}")

    return status['healthy']


async def test_skill_loader():
    """SKILL 로더 테스트"""
    print("\n" + "=" * 60)
    print("TEST: Skill Loader")
    print("=" * 60)

    service = create_service()

    # 스킬 목록
    skills = service.skill_loader.list_skills()
    print(f"\nAvailable skills: {skills}")

    # badminton 스킬 로드
    badminton_skill = service.skill_loader.load("badminton")
    if badminton_skill:
        print(f"\nbadminton.md loaded: {len(badminton_skill)} chars")
        print("--- Preview (first 300 chars) ---")
        print(badminton_skill[:300] + "...")
    else:
        print("\nbadminton.md NOT FOUND")
        return False

    # 캐시 테스트
    service.skill_loader.load("badminton")  # 캐시 히트
    service.skill_loader.clear_cache("badminton")
    service.skill_loader.load("badminton")  # 캐시 미스

    return True


async def test_session():
    """세션 테스트"""
    print("\n" + "=" * 60)
    print("TEST: Session Management")
    print("=" * 60)

    service = create_service()

    user_id = "test_user_001"
    context_type = "badminton"

    # 기존 세션 삭제
    service.delete_session(user_id, context_type)

    # 세션 생성
    print(f"\nCreating session for {user_id}...")
    session = service.session.get_or_create_session(
        user_id=user_id,
        context_type=context_type,
        context={"match_id": "match_123"}
    )
    print(f"Session created: {session.session_id}")

    # 메시지 추가
    session.add_message("user", "테스트 메시지 1")
    session.add_message("assistant", "테스트 응답 1")
    session.add_message("user", "테스트 메시지 2")
    service.session.save_session(session)

    # 세션 조회
    loaded_session = service.session.get_session(user_id, context_type)
    print(f"Loaded session: {loaded_session.session_id}")
    print(f"Messages: {len(loaded_session.messages)}")
    print(f"Context: {loaded_session.context}")

    # 세션 정보
    info = service.get_session_info(user_id, context_type)
    print(f"\nSession info: {info}")

    # 히스토리 삭제
    service.clear_history(user_id, context_type)
    loaded_session = service.session.get_session(user_id, context_type)
    print(f"After clear: {len(loaded_session.messages)} messages")

    # 세션 삭제
    service.delete_session(user_id, context_type)
    print("Session deleted")

    return True


async def test_chat():
    """채팅 테스트 (비스트리밍)"""
    print("\n" + "=" * 60)
    print("TEST: Chat (non-streaming)")
    print("=" * 60)

    service = create_service()

    user_id = "test_user_chat"
    context_type = "badminton"

    # 기존 세션 삭제
    service.delete_session(user_id, context_type)

    # 첫 번째 메시지
    print("\n--- First message ---")
    result1 = await service.chat(
        user_id=user_id,
        message="안녕하세요! 배드민턴에 대해 질문할게요.",
        context_type=context_type,
        temperature=0.7,
        max_tokens=256
    )

    print(f"\nResponse: {result1.content}")
    print(f"\nMetadata:")
    print(f"  Session: {result1.session_id}")
    print(f"  Model: {result1.model}")
    print(f"  Response Time: {result1.response_time_ms:.1f}ms")
    print(f"  Tokens: {result1.tokens}")
    print(f"  Message Count: {result1.message_count}")

    # 두 번째 메시지 (대화 이어가기)
    print("\n--- Second message (follow-up) ---")
    result2 = await service.chat(
        user_id=user_id,
        message="안세영 선수에 대해 간단히 설명해주세요. (3문장 이내)",
        context_type=context_type,
        temperature=0.5,
        max_tokens=512
    )

    print(f"\nResponse: {result2.content}")
    print(f"Message Count: {result2.message_count}")

    # 세션 정보 확인
    info = service.get_session_info(user_id, context_type)
    print(f"\nFinal session info: {info}")

    # 정리
    service.delete_session(user_id, context_type)

    return True


async def test_chat_stream():
    """스트리밍 채팅 테스트"""
    print("\n" + "=" * 60)
    print("TEST: Chat (streaming)")
    print("=" * 60)

    service = create_service()

    user_id = "test_user_stream"
    context_type = "badminton"

    # 기존 세션 삭제
    service.delete_session(user_id, context_type)

    print("\n--- Streaming Response ---")
    full_response = ""

    async for chunk in service.chat_stream(
        user_id=user_id,
        message="배드민턴의 기본 규칙을 3가지만 알려주세요.",
        context_type=context_type,
        temperature=0.5,
        max_tokens=512
    ):
        print(chunk, end="", flush=True)
        full_response += chunk

    print(f"\n\n--- Stats ---")
    print(f"Total length: {len(full_response)} chars")

    # 세션 확인
    info = service.get_session_info(user_id, context_type)
    print(f"Session messages: {info['message_count']}")

    # 정리
    service.delete_session(user_id, context_type)

    return True


async def test_multi_turn():
    """멀티턴 대화 테스트"""
    print("\n" + "=" * 60)
    print("TEST: Multi-turn Conversation")
    print("=" * 60)

    service = create_service()

    user_id = "test_user_multi"
    context_type = "badminton"

    # 기존 세션 삭제
    service.delete_session(user_id, context_type)

    conversations = [
        "안녕하세요",
        "배드민턴 선수 중에 한국 선수 한 명만 알려주세요",
        "그 선수의 주특기는 뭔가요?",
    ]

    for i, message in enumerate(conversations, 1):
        print(f"\n--- Turn {i} ---")
        print(f"User: {message}")

        result = await service.chat(
            user_id=user_id,
            message=message,
            context_type=context_type,
            temperature=0.5,
            max_tokens=256
        )

        print(f"Assistant: {result.content}")
        print(f"(messages in session: {result.message_count})")

    # 정리
    service.delete_session(user_id, context_type)

    return True


async def run_all_tests():
    """모든 테스트 실행"""
    results = {}

    # 1. Health Check
    results['health'] = await test_health_check()
    if not results['health']:
        print("\n[STOP] Health check failed.")
        return results

    # 2. Skill Loader
    results['skill'] = await test_skill_loader()

    # 3. Session
    results['session'] = await test_session()

    # 4. Chat
    results['chat'] = await test_chat()

    # 5. Stream
    results['stream'] = await test_chat_stream()

    # 6. Multi-turn
    results['multi_turn'] = await test_multi_turn()

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
    parser = argparse.ArgumentParser(description='ChatService 테스트')
    parser.add_argument(
        '--test',
        choices=['health', 'skill', 'session', 'chat', 'stream', 'multi', 'all'],
        default='all',
        help='실행할 테스트 (기본: all)'
    )
    args = parser.parse_args()

    test_map = {
        'health': test_health_check,
        'skill': test_skill_loader,
        'session': test_session,
        'chat': test_chat,
        'stream': test_chat_stream,
        'multi': test_multi_turn,
        'all': run_all_tests
    }

    print("=" * 60)
    print("ChatService Test Script")
    print("=" * 60)

    asyncio.run(test_map[args.test]())


if __name__ == "__main__":
    main()

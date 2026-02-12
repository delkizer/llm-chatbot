import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ─────────────────────────────────────────────
# deps 모듈 import (모듈 레벨 인스턴스 patch 필요)
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_chat_service():
    """각 테스트 전 _chat_service 싱글톤 초기화"""
    import apps.chatbot.deps as deps_module
    deps_module._chat_service = None
    yield
    deps_module._chat_service = None


class TestGetCurrentPayload:
    """get_current_payload 단위 테스트"""

    @pytest.mark.asyncio
    async def test_get_current_payload_from_cookie(self):
        """request.cookies에 access_token → auth.verify_token 호출"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "cookie-token"
        mock_request.headers.get.return_value = None

        expected_payload = {"email": "test@test.com", "role": "admin"}

        with patch(
            "apps.chatbot.deps.auth.verify_token",
            return_value=expected_payload
        ) as mock_verify:
            from apps.chatbot.deps import get_current_payload
            result = await get_current_payload(mock_request)

        mock_verify.assert_called_once_with("cookie-token")
        assert result == expected_payload

    @pytest.mark.asyncio
    async def test_get_current_payload_from_bearer(self):
        """Authorization: Bearer 헤더 → auth.verify_token 호출"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None
        mock_request.headers.get.return_value = "Bearer header-token"

        expected_payload = {"email": "test@test.com", "role": "user"}

        with patch(
            "apps.chatbot.deps.auth.verify_token",
            return_value=expected_payload
        ) as mock_verify:
            from apps.chatbot.deps import get_current_payload
            result = await get_current_payload(mock_request)

        mock_verify.assert_called_once_with("header-token")
        assert result == expected_payload

    @pytest.mark.asyncio
    async def test_get_current_payload_cookie_priority(self):
        """쿠키와 헤더 둘 다 있을 때 쿠키 우선"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "cookie-token"
        mock_request.headers.get.return_value = "Bearer header-token"

        expected_payload = {"email": "cookie@test.com"}

        with patch(
            "apps.chatbot.deps.auth.verify_token",
            return_value=expected_payload
        ) as mock_verify:
            from apps.chatbot.deps import get_current_payload
            result = await get_current_payload(mock_request)

        mock_verify.assert_called_once_with("cookie-token")
        assert result["email"] == "cookie@test.com"

    @pytest.mark.asyncio
    async def test_get_current_payload_no_token(self):
        """토큰 없음 → HTTPException 401"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None
        mock_request.headers.get.return_value = None

        from apps.chatbot.deps import get_current_payload

        with pytest.raises(HTTPException) as exc_info:
            await get_current_payload(mock_request)

        assert exc_info.value.status_code == 401
        assert "token" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_payload_invalid_token(self):
        """auth.verify_token이 예외 발생 시 전파"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "bad-token"
        mock_request.headers.get.return_value = None

        with patch(
            "apps.chatbot.deps.auth.verify_token",
            side_effect=HTTPException(
                status_code=401,
                detail="Token error: expired"
            )
        ):
            from apps.chatbot.deps import get_current_payload

            with pytest.raises(HTTPException) as exc_info:
                await get_current_payload(mock_request)

        assert exc_info.value.status_code == 401
        assert "token error" in exc_info.value.detail.lower()


class TestGetUserId:
    """get_user_id 단위 테스트"""

    def test_get_user_id_dict_with_email(self):
        """{"email": "a@b.com"} → "a@b.com"'''"""
        from apps.chatbot.deps import get_user_id
        result = get_user_id({"email": "a@b.com", "user_id": "123"})
        assert result == "a@b.com"

    def test_get_user_id_dict_with_user_id(self):
        """{"user_id": "123"} (email 없음) → "123"'''"""
        from apps.chatbot.deps import get_user_id
        result = get_user_id({"user_id": "123"})
        assert result == "123"

    def test_get_user_id_list_payload(self):
        """[{"email": "a@b.com"}] → "a@b.com"'''"""
        from apps.chatbot.deps import get_user_id
        result = get_user_id([{"email": "a@b.com"}])
        assert result == "a@b.com"

    def test_get_user_id_fallback_anonymous(self):
        """{} → "anonymous"'''"""
        from apps.chatbot.deps import get_user_id
        result = get_user_id({})
        assert result == "anonymous"

    def test_get_user_id_empty_list(self):
        """[] → "anonymous"'''"""
        from apps.chatbot.deps import get_user_id
        result = get_user_id([])
        assert result == "anonymous"


class TestRequireRole:
    """require_role 단위 테스트"""

    @pytest.mark.asyncio
    async def test_require_role_allowed(self):
        """role="admin", require_role("admin") → 통과"""
        from apps.chatbot.deps import require_role

        checker = require_role("admin")
        payload = {"email": "admin@test.com", "role": "admin"}

        result = await checker(payload=payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_require_role_denied(self):
        """role="user", require_role("admin") → HTTPException 403"""
        from apps.chatbot.deps import require_role

        checker = require_role("admin")
        payload = {"email": "user@test.com", "role": "user"}

        with pytest.raises(HTTPException) as exc_info:
            await checker(payload=payload)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_role_multiple(self):
        """require_role("admin", "staff") → "staff" 허용"""
        from apps.chatbot.deps import require_role

        checker = require_role("admin", "staff")
        payload = {"email": "staff@test.com", "role": "staff"}

        result = await checker(payload=payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_require_role_list_payload(self):
        """payload가 list인 경우 [{"role": "admin"}] 처리"""
        from apps.chatbot.deps import require_role

        checker = require_role("admin")
        payload = [{"email": "admin@test.com", "role": "admin"}]

        result = await checker(payload=payload)
        assert result == payload


class TestGetChatService:
    """get_chat_service 단위 테스트"""

    def test_get_chat_service_returns_instance(self):
        """ChatService 인스턴스 반환"""
        with patch("apps.chatbot.deps.ChatService") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance

            from apps.chatbot.deps import get_chat_service
            result = get_chat_service()

        assert result is mock_instance

    def test_get_chat_service_singleton(self):
        """두 번 호출 시 같은 인스턴스"""
        with patch("apps.chatbot.deps.ChatService") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance

            from apps.chatbot.deps import get_chat_service
            first = get_chat_service()
            second = get_chat_service()

        assert first is second
        mock_cls.assert_called_once()

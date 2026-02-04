import pytest


class TestChatEndpointAuth:
    """POST /api/chat/ 인증 테스트"""

    @pytest.mark.asyncio
    async def test_chat_without_token(self, async_client):
        """토큰 없이 요청 시 401"""
        response = await async_client.post(
            "/api/chat/",
            json={"message": "테스트 메시지"}
        )

        assert response.status_code == 401
        assert "token" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_chat_with_invalid_token(self, async_client, mock_auth_failure, auth_headers):
        """잘못된 토큰으로 요청 시 401"""
        response = await async_client.post(
            "/api/chat/",
            json={"message": "테스트 메시지"},
            headers=auth_headers
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_auth_service_unavailable(self, async_client, mock_auth_service_unavailable, auth_headers):
        """Auth 서비스 장애 시 503"""
        response = await async_client.post(
            "/api/chat/",
            json={"message": "테스트 메시지"},
            headers=auth_headers
        )

        assert response.status_code == 503


class TestChatEndpointSuccess:
    """POST /api/chat/ 성공 케이스"""

    @pytest.mark.asyncio
    async def test_chat_with_bearer_token(self, async_client, mock_auth_success, auth_headers):
        """Bearer 토큰으로 인증 성공"""
        response = await async_client.post(
            "/api/chat/",
            json={"message": "안녕하세요"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "model" in data

    @pytest.mark.asyncio
    async def test_chat_with_cookie(self, async_client, mock_auth_success, valid_token):
        """쿠키로 인증 성공"""
        async_client.cookies.set("access_token", valid_token)

        response = await async_client.post(
            "/api/chat/",
            json={"message": "안녕하세요"}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_response_format(self, async_client, mock_auth_success, auth_headers):
        """응답 형식 확인"""
        response = await async_client.post(
            "/api/chat/",
            json={"message": "테스트"},
            headers=auth_headers
        )

        data = response.json()
        assert isinstance(data["text"], str)
        assert isinstance(data["model"], str)
        assert data["model"] == "qwen2.5:7b"


class TestChatEndpointInput:
    """POST /api/chat/ 입력 테스트"""

    @pytest.mark.asyncio
    async def test_chat_with_context_type(self, async_client, mock_auth_success, auth_headers):
        """context_type 지정"""
        response = await async_client.post(
            "/api/chat/",
            json={
                "message": "경기 분석해줘",
                "context_type": "badminton"
            },
            headers=auth_headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_default_context_type(self, async_client, mock_auth_success, auth_headers):
        """context_type 기본값 (badminton)"""
        response = await async_client.post(
            "/api/chat/",
            json={"message": "테스트"},
            headers=auth_headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_missing_message_field(self, async_client, mock_auth_success, auth_headers):
        """message 필드 누락 시 422"""
        response = await async_client.post(
            "/api/chat/",
            json={"context_type": "badminton"},
            headers=auth_headers
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_invalid_json(self, async_client, mock_auth_success, auth_headers):
        """잘못된 JSON 형식"""
        response = await async_client.post(
            "/api/chat/",
            content="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )

        assert response.status_code == 422

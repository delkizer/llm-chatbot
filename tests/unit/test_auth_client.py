import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx


class TestAuthClientVerifyToken:
    """AuthClient.verify_token 단위 테스트"""

    @pytest.fixture
    def auth_client(self):
        """AuthClient 인스턴스 생성"""
        with patch("class_lib.auth_client.Config") as mock_config:
            mock_config.return_value.btn_auth_url = "http://localhost:8000/api"
            mock_config.return_value.btn_internal_api_key = "test-internal-key"

            from class_lib.auth_client import AuthClient
            mock_logger = MagicMock()
            return AuthClient(mock_logger)

    @pytest.fixture
    def mock_httpx_success(self):
        """httpx 성공 응답 Mock"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"email": "test@test.com", "role": "admin"}]

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        return mock_client

    @pytest.mark.asyncio
    async def test_verify_token_success(self, auth_client, mock_httpx_success):
        """토큰 검증 성공"""
        with patch("httpx.AsyncClient", return_value=mock_httpx_success):
            result = await auth_client.verify_token("valid-token")

        assert result[0]["email"] == "test@test.com"
        assert result[0]["role"] == "admin"

    @pytest.mark.asyncio
    async def test_verify_token_sends_internal_api_key(self, auth_client, mock_httpx_success):
        """Internal API Key 헤더 전송 확인"""
        with patch("httpx.AsyncClient", return_value=mock_httpx_success):
            await auth_client.verify_token("valid-token")

        call_kwargs = mock_httpx_success.get.call_args.kwargs
        assert "X-Internal-Api-Key" in call_kwargs.get("headers", {})
        assert call_kwargs["headers"]["X-Internal-Api-Key"] == "test-internal-key"

    @pytest.mark.asyncio
    async def test_verify_token_sends_cookie(self, auth_client, mock_httpx_success):
        """토큰을 쿠키로 전송"""
        with patch("httpx.AsyncClient", return_value=mock_httpx_success):
            await auth_client.verify_token("my-token")

        call_kwargs = mock_httpx_success.get.call_args.kwargs
        assert call_kwargs["cookies"]["access_token"] == "my-token"

    @pytest.mark.asyncio
    async def test_verify_token_unauthorized(self, auth_client):
        """401 응답 시 HTTPException 발생"""
        from fastapi import HTTPException

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await auth_client.verify_token("invalid-token")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_token_server_error(self, auth_client):
        """500 응답 시 503 HTTPException 발생"""
        from fastapi import HTTPException

        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await auth_client.verify_token("token")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_verify_token_connection_error(self, auth_client):
        """연결 오류 시 503 HTTPException 발생"""
        from fastapi import HTTPException

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await auth_client.verify_token("token")

        assert exc_info.value.status_code == 503
        assert "unavailable" in exc_info.value.detail.lower()


class TestAuthClientGetCurrentUser:
    """AuthClient.get_current_user 단위 테스트"""

    @pytest.fixture
    def auth_client(self):
        """AuthClient 인스턴스 생성"""
        with patch("class_lib.auth_client.Config") as mock_config:
            mock_config.return_value.btn_auth_url = "http://localhost:8000/api"
            mock_config.return_value.btn_internal_api_key = "test-key"

            from class_lib.auth_client import AuthClient
            mock_logger = MagicMock()
            return AuthClient(mock_logger)

    @pytest.mark.asyncio
    async def test_get_current_user_from_cookie(self, auth_client):
        """쿠키에서 토큰 추출"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "cookie-token"
        mock_request.headers.get.return_value = None

        with patch.object(auth_client, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = [{"email": "test@test.com"}]
            result = await auth_client.get_current_user(mock_request)

        mock_verify.assert_called_once_with("cookie-token")
        assert result[0]["email"] == "test@test.com"

    @pytest.mark.asyncio
    async def test_get_current_user_from_header(self, auth_client):
        """Authorization 헤더에서 토큰 추출"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None
        mock_request.headers.get.return_value = "Bearer header-token"

        with patch.object(auth_client, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = [{"email": "test@test.com"}]
            result = await auth_client.get_current_user(mock_request)

        mock_verify.assert_called_once_with("header-token")

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, auth_client):
        """토큰 없을 시 401 HTTPException"""
        from fastapi import HTTPException

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None
        mock_request.headers.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await auth_client.get_current_user(mock_request)

        assert exc_info.value.status_code == 401
        assert "token" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_user_cookie_priority(self, auth_client):
        """쿠키가 헤더보다 우선"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "cookie-token"
        mock_request.headers.get.return_value = "Bearer header-token"

        with patch.object(auth_client, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = [{"email": "test@test.com"}]
            await auth_client.get_current_user(mock_request)

        mock_verify.assert_called_once_with("cookie-token")

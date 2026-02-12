import pytest
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main_http import root as app


# ─────────────────────────────────────────────
# TestClient Fixture
# ─────────────────────────────────────────────

@pytest.fixture
def client():
    """동기 테스트 클라이언트"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client():
    """비동기 테스트 클라이언트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ─────────────────────────────────────────────
# Mock Auth Fixture (자체 JWT 검증 Mock)
# ─────────────────────────────────────────────

@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload"""
    return {
        "email": "test@example.com",
        "role": "admin",
        "type": "access",
        "exp": 9999999999,
        "iat": 1700000000
    }


@pytest.fixture
def mock_auth_success(mock_jwt_payload):
    """인증 성공 Mock"""
    with patch(
        "apps.chatbot.deps.auth.verify_token",
        return_value=mock_jwt_payload
    ):
        yield mock_jwt_payload


@pytest.fixture
def mock_auth_failure():
    """인증 실패 Mock (401)"""
    from fastapi import HTTPException, status

    with patch(
        "apps.chatbot.deps.auth.verify_token",
        side_effect=HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    ):
        yield


@pytest.fixture
def mock_auth_service_unavailable():
    """Auth 서비스 불가 Mock (503)"""
    from fastapi import HTTPException, status

    with patch(
        "apps.chatbot.deps.auth.verify_token",
        side_effect=HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable"
        )
    ):
        yield


# ─────────────────────────────────────────────
# Token Fixture
# ─────────────────────────────────────────────

@pytest.fixture
def valid_token():
    """테스트용 유효 토큰"""
    return "test-valid-token-12345"


@pytest.fixture
def invalid_token():
    """테스트용 무효 토큰"""
    return "invalid-token"


@pytest.fixture
def auth_headers(valid_token):
    """인증 헤더 (Authorization: Bearer)"""
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def auth_cookies(valid_token):
    """인증 쿠키"""
    return {"access_token": valid_token}

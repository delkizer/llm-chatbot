"""Auth JWT 서명 키 변경 단위 테스트"""

import logging
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from class_lib.auth import Auth
from class_config.class_env import Config


@pytest.fixture
def auth():
    logger = logging.getLogger("test")
    with patch("class_lib.auth.ConfigDB") as mock_db:
        mock_db.return_value.get_session_factory.return_value = MagicMock()
        a = Auth(logger)
        return a


class TestJWTSecretKey:
    """JWT가 jwt_secret_key를 사용하는지 확인"""

    def test_create_and_verify_access_token(self, auth):
        """access token 생성 + 검증"""
        token = auth.create_access_token("test@example.com", "admin")
        assert isinstance(token, str)
        assert len(token) > 0

        # 동일 키로 검증 성공
        payload = auth.verify_token(token)
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_create_and_verify_refresh_token(self, auth):
        """refresh token 생성 + 검증"""
        token = auth.create_refresh_token("test@example.com", "user")
        payload = auth.verify_token(token)
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "refresh"

    def test_uses_jwt_secret_key_property(self, auth):
        """Config.jwt_secret_key 프로퍼티 사용 확인"""
        with patch.object(Config, 'jwt_secret_key', new_callable=PropertyMock, return_value='my-test-secret'):
            token = auth.create_access_token("a@b.com", "admin")
            payload = auth.verify_token(token)
            assert payload["email"] == "a@b.com"

    def test_fallback_secret_key(self, auth):
        """jwt_secret_key가 None이면 fallback 사용"""
        with patch.object(Config, 'jwt_secret_key', new_callable=PropertyMock, return_value=None):
            token = auth.create_access_token("a@b.com", "admin")
            payload = auth.verify_token(token)
            assert payload["email"] == "a@b.com"

    def test_invalid_token(self, auth):
        """잘못된 토큰 → HTTPException"""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token("invalid-token")
        assert exc_info.value.status_code == 401

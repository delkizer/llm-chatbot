import pytest
import bcrypt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
import jwt


# ─────────────────────────────────────────────
# TestAuthTokens (토큰 생성/검증)
# ─────────────────────────────────────────────


class TestAuthTokens:
    """Auth 토큰 생성/검증 단위 테스트"""

    TEST_SECRET = "test-secret-key-12345"

    @pytest.fixture
    def auth(self):
        """Auth 인스턴스 생성 (Config, ConfigDB Mock)"""
        with patch("class_lib.auth.Config") as mock_config, \
             patch("class_lib.auth.ConfigDB") as mock_db:
            mock_config.return_value.jwt_secret_key = self.TEST_SECRET

            mock_session = MagicMock()
            mock_db.return_value.get_session_factory.return_value = lambda: mock_session

            from class_lib.auth import Auth
            mock_logger = MagicMock()
            return Auth(mock_logger)

    def test_create_access_token_success(self, auth):
        """Access Token 생성 후 디코딩하여 payload 확인"""
        token = auth.create_access_token("user@test.com", "admin")

        assert isinstance(token, str)
        assert len(token) > 0

        payload = jwt.decode(token, self.TEST_SECRET, algorithms=["HS256"])
        assert payload["email"] == "user@test.com"
        assert payload["role"] == "admin"

    def test_create_access_token_contains_claims(self, auth):
        """토큰에 email, role, type='access', exp, iat 포함 확인"""
        token = auth.create_access_token("user@test.com", "editor")

        payload = jwt.decode(token, self.TEST_SECRET, algorithms=["HS256"])
        assert payload["email"] == "user@test.com"
        assert payload["role"] == "editor"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token_success(self, auth):
        """Refresh Token 생성 확인"""
        token = auth.create_refresh_token("user@test.com", "admin")

        assert isinstance(token, str)
        assert len(token) > 0

        payload = jwt.decode(token, self.TEST_SECRET, algorithms=["HS256"])
        assert payload["email"] == "user@test.com"
        assert payload["role"] == "admin"
        assert payload["type"] == "refresh"

    def test_create_refresh_token_custom_expiry(self, auth):
        """사용자 지정 expires_days 동작 확인"""
        token_default = auth.create_refresh_token("user@test.com", "admin")
        token_custom = auth.create_refresh_token("user@test.com", "admin", expires_days=30)

        payload_default = jwt.decode(token_default, self.TEST_SECRET, algorithms=["HS256"])
        payload_custom = jwt.decode(token_custom, self.TEST_SECRET, algorithms=["HS256"])

        # custom(30일)이 default(7일)보다 만료 시간이 길어야 함
        assert payload_custom["exp"] > payload_default["exp"]

        # 만료 시간 차이가 약 23일 (30-7)
        diff_seconds = payload_custom["exp"] - payload_default["exp"]
        expected_diff = 23 * 24 * 60 * 60  # 23일 (초)
        assert abs(diff_seconds - expected_diff) < 60  # 1분 이내 오차 허용

    def test_verify_token_success(self, auth):
        """create_access_token으로 만든 토큰을 verify_token으로 검증"""
        token = auth.create_access_token("user@test.com", "admin")

        payload = auth.verify_token(token)

        assert payload["email"] == "user@test.com"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_verify_token_expired(self, auth):
        """만료된 토큰 -> HTTPException 401"""
        expired_payload = {
            "email": "user@test.com",
            "role": "admin",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=25)
        }
        expired_token = jwt.encode(expired_payload, self.TEST_SECRET, algorithm="HS256")

        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token(expired_token)

        assert exc_info.value.status_code == 401

    def test_verify_token_invalid_signature(self, auth):
        """다른 시크릿으로 만든 토큰 -> HTTPException 401"""
        wrong_secret = "wrong-secret-key"
        payload = {
            "email": "user@test.com",
            "role": "admin",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
            "iat": datetime.now(timezone.utc)
        }
        token = jwt.encode(payload, wrong_secret, algorithm="HS256")

        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token(token)

        assert exc_info.value.status_code == 401

    def test_verify_token_malformed(self, auth):
        """형식 오류 문자열 -> HTTPException 401"""
        with pytest.raises(HTTPException) as exc_info:
            auth.verify_token("not-a-valid-jwt-token")

        assert exc_info.value.status_code == 401


# ─────────────────────────────────────────────
# TestAuthenticateUser (사용자 인증)
# ─────────────────────────────────────────────


class TestAuthenticateUser:
    """Auth.authenticate_user 단위 테스트"""

    @pytest.fixture
    def mock_session(self):
        """Mock DB Session"""
        return MagicMock()

    @pytest.fixture
    def auth(self, mock_session):
        """Auth 인스턴스 생성 (DB Session Mock 주입)"""
        with patch("class_lib.auth.Config") as mock_config, \
             patch("class_lib.auth.ConfigDB") as mock_db:
            mock_config.return_value.jwt_secret_key = "test-secret"
            mock_db.return_value.get_session_factory.return_value = lambda: mock_session

            from class_lib.auth import Auth
            mock_logger = MagicMock()
            return Auth(mock_logger)

    def _hash_password(self, password: str) -> str:
        """테스트용 bcrypt 해시 생성"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def test_authenticate_user_success(self, auth, mock_session):
        """올바른 email/password -> 사용자 정보 반환"""
        password_hash = self._hash_password("correct-password")
        mock_user = {
            "user_id": 1,
            "email": "user@test.com",
            "password_hash": password_hash,
            "role": "admin",
            "is_active": True,
            "full_name": "Test User"
        }
        mock_session.execute.return_value.mappings.return_value.all.return_value = [mock_user]

        result = auth.authenticate_user("user@test.com", "correct-password")

        assert result["user_id"] == 1
        assert result["email"] == "user@test.com"
        assert result["role"] == "admin"
        assert result["full_name"] == "Test User"
        mock_session.close.assert_called_once()

    def test_authenticate_user_not_found(self, auth, mock_session):
        """존재하지 않는 email -> HTTPException 401"""
        mock_session.execute.return_value.mappings.return_value.all.return_value = []

        with pytest.raises(HTTPException) as exc_info:
            auth.authenticate_user("notfound@test.com", "any-password")

        assert exc_info.value.status_code == 401
        assert "not found" in exc_info.value.detail.lower()
        mock_session.close.assert_called_once()

    def test_authenticate_user_wrong_password(self, auth, mock_session):
        """잘못된 password -> HTTPException 401"""
        password_hash = self._hash_password("correct-password")
        mock_user = {
            "user_id": 1,
            "email": "user@test.com",
            "password_hash": password_hash,
            "role": "admin",
            "is_active": True,
            "full_name": "Test User"
        }
        mock_session.execute.return_value.mappings.return_value.all.return_value = [mock_user]

        with pytest.raises(HTTPException) as exc_info:
            auth.authenticate_user("user@test.com", "wrong-password")

        assert exc_info.value.status_code == 401
        assert "invalid password" in exc_info.value.detail.lower()
        mock_session.close.assert_called_once()

    def test_authenticate_user_inactive(self, auth, mock_session):
        """is_active=False -> HTTPException 401"""
        password_hash = self._hash_password("correct-password")
        mock_user = {
            "user_id": 2,
            "email": "inactive@test.com",
            "password_hash": password_hash,
            "role": "viewer",
            "is_active": False,
            "full_name": "Inactive User"
        }
        mock_session.execute.return_value.mappings.return_value.all.return_value = [mock_user]

        with pytest.raises(HTTPException) as exc_info:
            auth.authenticate_user("inactive@test.com", "correct-password")

        assert exc_info.value.status_code == 401
        assert "not active" in exc_info.value.detail.lower()
        mock_session.close.assert_called_once()


# ─────────────────────────────────────────────
# TestRefreshToken (DB 저장/삭제)
# ─────────────────────────────────────────────


class TestRefreshToken:
    """Auth Refresh Token DB 저장/삭제 단위 테스트"""

    @pytest.fixture
    def mock_session(self):
        """Mock DB Session"""
        return MagicMock()

    @pytest.fixture
    def auth(self, mock_session):
        """Auth 인스턴스 생성 (DB Session Mock 주입)"""
        with patch("class_lib.auth.Config") as mock_config, \
             patch("class_lib.auth.ConfigDB") as mock_db:
            mock_config.return_value.jwt_secret_key = "test-secret"
            mock_db.return_value.get_session_factory.return_value = lambda: mock_session

            from class_lib.auth import Auth
            mock_logger = MagicMock()
            return Auth(mock_logger)

    def test_save_refresh_token(self, auth, mock_session):
        """DB에 refresh_token, token_expire_at 저장 확인"""
        auth.save_refresh_token("user@test.com", "refresh-token-value", expires_days=7)

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

        # execute 호출 시 전달된 파라미터 확인
        call_args = mock_session.execute.call_args
        params = call_args[0][1]  # 두 번째 positional arg (dict)
        assert params["email"] == "user@test.com"
        assert params["refresh_token"] == "refresh-token-value"
        assert "token_expire_at" in params
        assert isinstance(params["token_expire_at"], datetime)

    def test_delete_refresh_token(self, auth, mock_session):
        """DB에서 refresh_token NULL 처리 확인"""
        auth.delete_refresh_token("user@test.com")

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

        # execute 호출 시 전달된 파라미터 확인
        call_args = mock_session.execute.call_args
        params = call_args[0][1]  # 두 번째 positional arg (dict)
        assert params["email"] == "user@test.com"

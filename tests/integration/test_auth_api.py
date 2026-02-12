import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status


# ─────────────────────────────────────────────
# 테스트용 상수
# ─────────────────────────────────────────────

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "test-password-123"
TEST_ROLE = "admin"
TEST_FULL_NAME = "Test User"
TEST_USER_ID = 1

MOCK_USER = {
    "user_id": TEST_USER_ID,
    "email": TEST_EMAIL,
    "role": TEST_ROLE,
    "full_name": TEST_FULL_NAME,
}

LOGIN_URL = "/api/auth/login"
LOGOUT_URL = "/api/auth/logout"
USERINFO_URL = "/api/auth/userinfo"


# ─────────────────────────────────────────────
# Auth Mock Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def mock_auth_login_success():
    """authenticate_user + save_refresh_token Mock (로그인 성공)"""
    with patch(
        "apps.auth.router.auth.authenticate_user",
        return_value=MOCK_USER,
    ) as mock_authenticate, patch(
        "apps.auth.router.auth.save_refresh_token",
    ) as mock_save:
        yield mock_authenticate, mock_save


@pytest.fixture
def mock_auth_login_wrong_email():
    """존재하지 않는 이메일 Mock"""
    with patch(
        "apps.auth.router.auth.authenticate_user",
        side_effect=HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        ),
    ):
        yield


@pytest.fixture
def mock_auth_login_wrong_password():
    """잘못된 비밀번호 Mock"""
    with patch(
        "apps.auth.router.auth.authenticate_user",
        side_effect=HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        ),
    ):
        yield


@pytest.fixture
def mock_auth_delete_refresh_token():
    """delete_refresh_token Mock"""
    with patch("apps.auth.router.auth.delete_refresh_token"):
        yield


@pytest.fixture
def real_access_token():
    """실제 Auth 클래스로 생성한 유효한 access_token"""
    from apps.auth.router import auth

    return auth.create_access_token(TEST_EMAIL, TEST_ROLE)


# ─────────────────────────────────────────────
# TestLoginEndpoint
# ─────────────────────────────────────────────

class TestLoginEndpoint:
    """POST /api/auth/login 테스트"""

    def test_login_success(self, client, mock_auth_login_success):
        """정상 로그인 -> 200, msg='login successful', access_token 포함"""
        response = client.post(
            LOGIN_URL,
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["msg"] == "login successful"
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_sets_cookies(self, client, mock_auth_login_success):
        """응답에 access_token, refresh_token 쿠키 설정 확인"""
        response = client.post(
            LOGIN_URL,
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )

        assert response.status_code == 200

        cookies = response.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies
        assert len(cookies["access_token"]) > 0
        assert len(cookies["refresh_token"]) > 0

    def test_login_wrong_email(self, client, mock_auth_login_wrong_email):
        """존재하지 않는 email -> 401"""
        response = client.post(
            LOGIN_URL,
            json={"email": "unknown@example.com", "password": TEST_PASSWORD},
        )

        assert response.status_code == 401
        assert "User not found" in response.json()["detail"]

    def test_login_wrong_password(self, client, mock_auth_login_wrong_password):
        """잘못된 password -> 401"""
        response = client.post(
            LOGIN_URL,
            json={"email": TEST_EMAIL, "password": "wrong-password"},
        )

        assert response.status_code == 401
        assert "Invalid password" in response.json()["detail"]

    def test_login_missing_fields(self, client):
        """email/password 누락 -> 422"""
        # email 누락
        response = client.post(LOGIN_URL, json={"password": TEST_PASSWORD})
        assert response.status_code == 422

        # password 누락
        response = client.post(LOGIN_URL, json={"email": TEST_EMAIL})
        assert response.status_code == 422

        # 빈 body
        response = client.post(LOGIN_URL, json={})
        assert response.status_code == 422


# ─────────────────────────────────────────────
# TestLogoutEndpoint
# ─────────────────────────────────────────────

class TestLogoutEndpoint:
    """POST /api/auth/logout 테스트"""

    def test_logout_success(self, client, real_access_token, mock_auth_delete_refresh_token):
        """로그아웃 -> 200 + 쿠키 삭제"""
        client.cookies.set("access_token", real_access_token)

        response = client.post(LOGOUT_URL)

        assert response.status_code == 200
        assert response.json()["msg"] == "logout successful"

    def test_logout_without_token(self, client):
        """토큰 없이도 로그아웃 성공 (에러 없음)"""
        response = client.post(LOGOUT_URL)

        assert response.status_code == 200
        assert response.json()["msg"] == "logout successful"

    def test_logout_clears_cookies(self, client, real_access_token, mock_auth_delete_refresh_token):
        """access_token, refresh_token 쿠키 삭제 확인"""
        client.cookies.set("access_token", real_access_token)
        client.cookies.set("refresh_token", "test-refresh-token")

        response = client.post(LOGOUT_URL)

        assert response.status_code == 200

        # Set-Cookie 헤더에서 삭제 확인 (max-age=0 또는 expires=과거)
        set_cookie_headers = response.headers.get_list("set-cookie")
        cookie_names_deleted = []
        for header in set_cookie_headers:
            header_lower = header.lower()
            if "max-age=0" in header_lower or 'expires=thu, 01 jan 1970' in header_lower:
                if "access_token" in header:
                    cookie_names_deleted.append("access_token")
                if "refresh_token" in header:
                    cookie_names_deleted.append("refresh_token")

        assert "access_token" in cookie_names_deleted
        assert "refresh_token" in cookie_names_deleted


# ─────────────────────────────────────────────
# TestUserinfoEndpoint
# ─────────────────────────────────────────────

class TestUserinfoEndpoint:
    """GET /api/auth/userinfo 테스트"""

    def test_userinfo_with_cookie(self, client, real_access_token):
        """access_token 쿠키 -> 200 + email, role"""
        client.cookies.set("access_token", real_access_token)

        response = client.get(USERINFO_URL)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_EMAIL
        assert data["role"] == TEST_ROLE

    def test_userinfo_with_bearer(self, client, real_access_token):
        """Authorization: Bearer -> 200"""
        response = client.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {real_access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_EMAIL
        assert data["role"] == TEST_ROLE

    def test_userinfo_no_token(self, client):
        """토큰 없음 -> 401"""
        response = client.get(USERINFO_URL)

        assert response.status_code == 401
        assert "No access token" in response.json()["detail"]

    def test_userinfo_invalid_token(self, client):
        """잘못된 토큰 -> 401"""
        client.cookies.set("access_token", "invalid-jwt-token-string")

        response = client.get(USERINFO_URL)

        assert response.status_code == 401
        assert "Token error" in response.json()["detail"]

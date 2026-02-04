import httpx
from fastapi import HTTPException, status, Request
from class_config.class_env import Config


class AuthClient:
    def __init__(self, logger):
        self.config = Config()
        self.base_url = self.config.btn_auth_url
        self.internal_api_key = self.config.btn_internal_api_key
        self.logger = logger

    async def verify_token(self, token: str) -> dict:
        """btn auth API로 토큰 검증"""
        headers = {}
        if self.internal_api_key:
            headers["X-Internal-Api-Key"] = self.internal_api_key

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/userinfo",
                    headers=headers,
                    cookies={"access_token": token},
                    timeout=10.0
                )

                if response.status_code == 401:
                    self.logger.warning(f"Token verification failed: 401 Unauthorized")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or expired token"
                    )

                if response.status_code != 200:
                    self.logger.error(f"Auth service error: {response.status_code}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Auth service unavailable"
                    )

                return response.json()

        except httpx.RequestError as e:
            self.logger.error(f"Auth service connection error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service unavailable"
            )

    async def get_current_user(self, request: Request) -> dict:
        """현재 사용자 정보 조회"""
        # 1. 쿠키에서 토큰 확인
        token = request.cookies.get("access_token")

        # 2. Authorization 헤더 확인 (Swagger UI용)
        if not token:
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No access token"
            )

        # 3. btn auth API로 검증
        user_info = await self.verify_token(token)
        return user_info

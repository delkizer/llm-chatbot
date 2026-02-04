from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from class_config.class_log import ConfigLogger
from class_lib.auth import Auth

router = APIRouter(prefix="/auth", tags=["Auth"])

logger = ConfigLogger('http_log', 365).get_logger('auth')
auth = Auth(logger)


class LoginRequest(BaseModel):
    email: str
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "your-password"
                }
            ]
        }
    }


class LoginResponse(BaseModel):
    msg: str
    access_token: str
    token_type: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    로그인 API (자체 인증)
    """
    try:
        # 사용자 인증
        user = auth.authenticate_user(request.email, request.password)

        # 토큰 생성
        access_token = auth.create_access_token(user['email'], user['role'])
        refresh_token = auth.create_refresh_token(user['email'], user['role'])

        # Refresh Token DB 저장
        auth.save_refresh_token(user['email'], refresh_token)

        # 응답 생성
        response = JSONResponse(content={
            "msg": "login successful",
            "access_token": access_token,
            "token_type": "bearer"
        })

        # 쿠키 설정
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,  # 개발환경
            samesite="lax",
            path="/",
            max_age=60 * 60 * 24  # 1일
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
            max_age=60 * 60 * 24 * 7  # 7일
        )

        logger.info(f"Login successful: {user['email']}")
        logger.info(f"Access token: {access_token}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
async def logout(request: Request):
    """
    로그아웃 API
    """
    # 쿠키에서 토큰 확인하고 DB에서 삭제
    access_token = request.cookies.get("access_token")
    if access_token:
        try:
            payload = auth.verify_token(access_token)
            email = payload.get("email")
            if email:
                auth.delete_refresh_token(email)
        except Exception:
            pass  # 토큰 검증 실패해도 로그아웃 진행

    response = JSONResponse(content={"msg": "logout successful"})
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return response


@router.get("/userinfo")
async def get_userinfo(request: Request):
    """
    현재 로그인한 사용자 정보
    """
    token = request.cookies.get("access_token")

    if not token:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access token"
        )

    payload = auth.verify_token(token)
    return {
        "email": payload.get("email"),
        "role": payload.get("role")
    }

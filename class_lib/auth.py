import bcrypt
from datetime import datetime, timedelta, timezone
from sqlalchemy.sql import text
from fastapi import HTTPException, status
from jose import jwt, JWTError

from class_config.class_env import Config
from class_config.class_db import ConfigDB


class Auth:
    """자체 인증 클래스 (외부 서비스용)"""

    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_HOURS = 24

    def __init__(self, logger):
        self.config = Config()
        self.logger = logger
        self.db = ConfigDB()
        self.session_factory = self.db.get_session_factory()

    def authenticate_user(self, email: str, password: str) -> dict:
        """사용자 인증 (DB 조회)"""
        session = self.session_factory()
        try:
            query = text("""
                SELECT user_id, email, password_hash, role, is_active, full_name
                FROM bxl.admin_users
                WHERE email = :email
            """)
            result = session.execute(query, {'email': email}).mappings().all()

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            user = result[0]

            if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid password"
                )

            if not user['is_active']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is not active"
                )

            return {
                "user_id": user['user_id'],
                "email": user['email'],
                "role": user['role'],
                "full_name": user['full_name']
            }

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"authenticate_user error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        finally:
            session.close()

    def create_access_token(self, email: str, role: str) -> str:
        """JWT Access Token 생성"""
        payload = {
            "email": email,
            "role": role,
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.JWT_EXPIRE_HOURS),
            "iat": datetime.now(timezone.utc)
        }

        # 간단한 시크릿 키 사용 (운영 환경에서는 RSA 키 사용 권장)
        secret_key = self.config.jwt_secret_key or "llm-chatbot-secret-key"
        token = jwt.encode(payload, secret_key, algorithm=self.JWT_ALGORITHM)
        return token

    def create_refresh_token(self, email: str, role: str, expires_days: int = 7) -> str:
        """JWT Refresh Token 생성"""
        payload = {
            "email": email,
            "role": role,
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=expires_days),
            "iat": datetime.now(timezone.utc)
        }

        secret_key = self.config.jwt_secret_key or "llm-chatbot-secret-key"
        token = jwt.encode(payload, secret_key, algorithm=self.JWT_ALGORITHM)
        return token

    def verify_token(self, token: str) -> dict:
        """JWT Token 검증"""
        try:
            secret_key = self.config.jwt_secret_key or "llm-chatbot-secret-key"
            payload = jwt.decode(token, secret_key, algorithms=[self.JWT_ALGORITHM])
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token error: {str(e)}"
            )

    def save_refresh_token(self, email: str, refresh_token: str, expires_days: int = 7):
        """Refresh Token DB 저장"""
        session = self.session_factory()
        try:
            query = text("""
                UPDATE bxl.admin_users
                SET refresh_token = :refresh_token,
                    token_expire_at = :token_expire_at
                WHERE email = :email
            """)
            session.execute(query, {
                'email': email,
                'refresh_token': refresh_token,
                'token_expire_at': datetime.now(timezone.utc) + timedelta(days=expires_days)
            })
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"save_refresh_token error: {e}")
            raise
        finally:
            session.close()

    def delete_refresh_token(self, email: str):
        """Refresh Token 삭제"""
        session = self.session_factory()
        try:
            query = text("""
                UPDATE bxl.admin_users
                SET refresh_token = NULL, token_expire_at = NULL
                WHERE email = :email
            """)
            session.execute(query, {'email': email})
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"delete_refresh_token error: {e}")
        finally:
            session.close()

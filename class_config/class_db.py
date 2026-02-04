from dataclasses import dataclass, field
from typing import Optional

import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from class_config.class_env import Config


@dataclass
class ConfigDB:
    config: Config = field(default_factory=Config)

    engine: Optional[sqlalchemy.engine.base.Engine] = field(default=None, init=False)
    session_factory: Optional[sessionmaker] = field(default=None, init=False)

    def _initialize_engine(self, db_url: str):
        return create_engine(
            db_url,
            pool_size=10,
            max_overflow=5,
            pool_timeout=30,
            pool_recycle=1800
        )

    def _initialize_session_factory(self, engine):
        return sessionmaker(bind=engine)

    def get_session_factory(self):
        if not self.engine:
            try:
                required_attrs = [
                    "postgres_user", "postgres_pass",
                    "postgres_host", "postgres_port",
                    "postgres_db_name_spotv"
                ]
                for attr in required_attrs:
                    if not getattr(self.config, attr, None):
                        raise AttributeError(f"Config에 {attr} 속성이 없습니다.")

                db_url = (
                    f"postgresql+psycopg2://{self.config.postgres_user}:{self.config.postgres_pass}"
                    f"@{self.config.postgres_host}:{self.config.postgres_port}/{self.config.postgres_db_name_spotv}"
                    f"?client_encoding=utf8"
                )

                self.engine = self._initialize_engine(db_url)
                self.session_factory = self._initialize_session_factory(self.engine)

                if not self.session_factory:
                    raise RuntimeError("session_factory 초기화 실패")

            except Exception as e:
                print(f"DB 연결 오류: {e}")
                raise

        return self.session_factory

    def close_connections(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None

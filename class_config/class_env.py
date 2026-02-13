import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    ENV_FILE_PATH = BASE_DIR / '.env'

    def __init__(self):
        # 기본 .env 로드
        load_dotenv(self.ENV_FILE_PATH)

        # 환경별 .env 파일 결정
        django_env = os.getenv('DJANGO_ENV', 'development')
        env_file_name = f".env.{django_env}"
        env_file_path = self.BASE_DIR / env_file_name
        load_dotenv(env_file_path, override=True)

    def _get(self, key: str, default: str = None) -> str:
        return os.getenv(key, default)

    def _get_int(self, key: str, default: int = 0) -> int:
        return int(os.getenv(key, default))

    def _get_bool(self, key: str, default: bool = False) -> bool:
        val = os.getenv(key, str(default)).lower()
        return val in ('true', '1', 'yes')

    @property
    def project_home_path(self):
        return self._get('PROJECT_HOME_PATH')

    @property
    def log_path(self):
        return self._get('LOG_PATH')

    # Ollama
    @property
    def ollama_host(self):
        return self._get('OLLAMA_HOST', 'http://localhost:11434')

    @property
    def ollama_model(self):
        return self._get('OLLAMA_MODEL', 'qwen2.5:7b')

    @property
    def ollama_timeout(self):
        return self._get_int('OLLAMA_TIMEOUT', 60)

    @property
    def ollama_debug(self):
        return self._get_bool('OLLAMA_DEBUG', True)

    # Database
    @property
    def postgres_user(self):
        return self._get('POSTGRESSQL_USER')

    @property
    def postgres_pass(self):
        return self._get('POSTGRESSQL_PASSWORD')

    @property
    def postgres_host(self):
        return self._get('POSTGRESSQL_HOST')

    @property
    def postgres_port(self):
        return self._get('POSTGRESSQL_PORT')

    @property
    def postgres_db_name_spotv(self):
        return self._get('DB_NAME_SPOTV')

    # Redis Sentinel
    @property
    def redis_sentinel_nodes(self):
        nodes_str = self._get('REDIS_SENTINEL_NODES', 'localhost:26379')
        nodes = []
        for node in nodes_str.split(','):
            host, port = node.strip().split(':')
            nodes.append((host, int(port)))
        return nodes

    @property
    def redis_sentinel_master(self):
        return self._get('REDIS_SENTINEL_MASTER', 'mymaster')

    @property
    def redis_password(self):
        pwd = self._get('REDIS_PASSWORD', '')
        return pwd if pwd else None

    @property
    def redis_db(self):
        return self._get_int('REDIS_DB', 1)

    # Session
    @property
    def session_ttl(self):
        return self._get_int('SESSION_TTL', 1800)

    # btn auth API
    @property
    def btn_auth_url(self):
        return self._get('BTN_AUTH_URL', 'http://localhost:8000/api')

    @property
    def btn_internal_api_key(self):
        return self._get('BTN_INTERNAL_API_KEY')

    @property
    def jwt_secret_key(self):
        return self._get('JWT_SECRET_KEY')

    # Data Layer
    @property
    def btn_api_base_url(self):
        return self._get('BTN_API_BASE_URL', 'http://localhost:8000')

    @property
    def btn_api_key(self):
        return self._get('BTN_API_KEY')

    @property
    def data_cache_ttl(self):
        return self._get_int('DATA_CACHE_TTL', 300)

    @property
    def api_timeout(self):
        return self._get_int('API_TIMEOUT', 10)

    @property
    def api_max_retries(self):
        return self._get_int('API_MAX_RETRIES', 3)

    @property
    def data_max_tokens(self):
        return self._get_int('DATA_MAX_TOKENS', 2000)

    @property
    def enable_data_layer(self):
        return self._get_bool('ENABLE_DATA_LAYER', False)

    # Embed Gateway
    @property
    def chatbot_api_url(self):
        return self._get('CHATBOT_API_URL', 'http://localhost:4502')

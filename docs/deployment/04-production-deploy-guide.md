# 운영 배포 가이드

> 작성일: 2026-02-13

---

## 1. 개요

EC2 테스트 서버(bxl-test-db) 배포 경험을 기반으로 정리한 운영 배포 체크리스트.

### 1.1 전제 조건

| 항목 | 요구사항 |
|------|---------|
| OS | Ubuntu 24.04 LTS |
| Python | 3.13+ (pyenv + venv) |
| Node.js | 22.x (nvm) |
| 기존 인프라 | Redis (Sentinel), PostgreSQL (btn 공유) |

### 1.2 배포 대상 서비스

| 서비스 | 포트 | systemd 유닛 | 설명 |
|--------|------|-------------|------|
| FastAPI (chatbot API) | 7002 | `llm_chatbot_http` | 챗봇 API 서버 |
| Gateway (embed 샘플) | 5174 | `chatbot_gateway` | embed 개발 페이지 + 샘플 서빙 |
| Ollama | 11434 | `ollama` | LLM 서버 (성능 이슈 참고: 05-llm-infrastructure-analysis.md) |

---

## 2. 소스 코드 배포

```bash
cd ~/work
git clone git@github.com:delkizer/llm-chatbot.git
cd llm-chatbot
```

---

## 3. Python 환경

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3.1 알려진 이슈

- `psycopg2-binary`: Python 3.13에서 빌드 에러 시 `sudo apt install libpq-dev`
- `__init__.py`는 `.gitignore`에서 의도적으로 제외. 패키지 구조는 namespace package 방식

---

## 4. 환경변수 설정

### 4.1 .env

```bash
DJANGO_ENV=production
```

### 4.2 .env.production

```bash
PROJECT_HOME_PATH=/home/ubuntu/work/llm-chatbot
LOG_PATH=/home/ubuntu/work/logs/llm-chatbot

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# Database
POSTGRESSQL_USER=postgres
POSTGRESSQL_PASSWORD=<비밀번호>
POSTGRESSQL_HOST=<DB호스트>
POSTGRESSQL_PORT=5432
DB_NAME_SPOTV=spotv

# Redis
REDIS_SENTINEL_NODES=localhost:26379
REDIS_SENTINEL_MASTER=mymaster
REDIS_PASSWORD=<비밀번호>
REDIS_DB=1

# Session
SESSION_TTL=1800

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=7002

# Auth
JWT_SECRET_KEY=<운영용 시크릿 - 32자 이상>

# btn auth API
BTN_AUTH_URL=http://<btn-server>:8000/api
BTN_INTERNAL_API_KEY=<키>

# Embed Gateway
CHATBOT_API_URL=https://chatbot.delkizer.com
```

### 4.3 Config 2단계 로드

```
.env → DJANGO_ENV 확인
.env.{DJANGO_ENV} → 환경별 설정 override 로드
```

gateway.py도 동일한 2단계 로드 패턴을 사용한다.

---

## 5. 디렉토리 준비

```bash
mkdir -p ~/work/logs/llm-chatbot
```

---

## 6. Ollama 설치 및 모델 다운로드

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b
```

GPU 유무 확인:
```bash
lspci | grep -i nvidia    # 하드웨어 확인
nvidia-smi                 # 드라이버 확인
```

> GPU 없는 인스턴스에서의 성능 한계는 `05-llm-infrastructure-analysis.md` 참조

---

## 7. embed 빌드

```bash
# embed.js 빌드
cd ~/work/llm-chatbot/embed
npm install
npm run build

# 샘플 빌드
cd ~/work/llm-chatbot/embed/samples
chmod +x manage.sh
./manage.sh install
./manage.sh build-all
```

---

## 8. systemd 서비스 등록

### 8.1 FastAPI (chatbot API)

```ini
# /etc/systemd/system/llm_chatbot_http.service
[Unit]
Description=LLM Chatbot HTTP Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/work/llm-chatbot
ExecStart=/home/ubuntu/work/llm-chatbot/venv/bin/uvicorn \
main_http:app \
--host 0.0.0.0 --port 7002
Restart=always
RestartSec=3
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

### 8.2 Gateway (embed 샘플)

```ini
# /etc/systemd/system/chatbot_gateway.service
[Unit]
Description=LLM Chatbot Embed Gateway
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/work/llm-chatbot/embed/samples
ExecStart=/home/ubuntu/work/llm-chatbot/venv/bin/uvicorn \
gateway:app \
--host 127.0.0.1 --port 5174
Restart=always
RestartSec=3
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

### 8.3 서비스 활성화

```bash
sudo systemctl daemon-reload
sudo systemctl enable llm_chatbot_http chatbot_gateway
sudo systemctl start llm_chatbot_http chatbot_gateway
```

---

## 9. nginx 설정

### 9.1 SSL 인증서 발급

```bash
sudo certbot --nginx -d chatbot.delkizer.com
```

### 9.2 nginx conf

```nginx
# /etc/nginx/sites-available/chatbot_frontend.conf

server {
    listen 443 ssl;
    server_name chatbot.delkizer.com;

    ssl_certificate /etc/letsencrypt/live/chatbot.delkizer.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chatbot.delkizer.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # API → FastAPI 챗봇 (7002)
    location /api/ {
        proxy_pass http://127.0.0.1:7002;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Cookie $http_cookie;
        proxy_pass_request_headers on;
    }

    # Swagger UI
    location /docs {
        proxy_pass http://127.0.0.1:7002;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Gateway → embed 개발 페이지 + 샘플 (5174)
    location / {
        proxy_pass http://127.0.0.1:5174;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    if ($host = chatbot.delkizer.com) {
        return 301 https://$host$request_uri;
    }

    listen 80;
    server_name chatbot.delkizer.com;
    return 404;
}
```

### 9.3 활성화

```bash
sudo ln -s /etc/nginx/sites-available/chatbot_frontend.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 10. 검증

```bash
# API 헬스
curl https://chatbot.delkizer.com/api/chat/health

# API 동작
curl https://chatbot.delkizer.com/api/chat/hello/test

# Swagger UI
# 브라우저: https://chatbot.delkizer.com/docs

# 개발 페이지 (로그인 + 챗봇)
# 브라우저: https://chatbot.delkizer.com/

# 프레임워크 샘플
# 브라우저: https://chatbot.delkizer.com/samples
```

---

## 11. 업데이트 절차

```bash
cd ~/work/llm-chatbot
git pull
sudo systemctl restart llm_chatbot_http chatbot_gateway
```

embed 변경 시:
```bash
cd ~/work/llm-chatbot/embed/samples
./manage.sh build-all
sudo systemctl restart chatbot_gateway
```

---

## 12. 포트 요약

| 포트 | 서비스 | 외부 노출 |
|------|--------|----------|
| 7002 | FastAPI (chatbot API) | nginx 경유 |
| 5174 | Gateway (embed) | nginx 경유 |
| 11434 | Ollama | 내부 전용 |
| 443 | nginx (HTTPS) | 외부 |
| 80 | nginx (HTTP → HTTPS) | 외부 |

---

## 13. 관련 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| 배포 개요 | `docs/deployment/01-deployment-overview.md` | 컨테이너 구성, 네트워크 아키텍처 |
| Docker 설계 | `docs/deployment/02-docker-design.md` | Dockerfile, docker-compose |
| CI/CD | `docs/deployment/03-cicd-pipeline.md` | GitHub Actions 파이프라인 |
| LLM 인프라 분석 | `docs/deployment/05-llm-infrastructure-analysis.md` | GPU/CPU 성능, 비용 비교 |

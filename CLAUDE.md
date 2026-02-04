# LLM Chatbot 프로젝트

> **Project Level** - 로컬 LLM 기반 스포츠 데이터 Q&A 챗봇
>
> 데이터 기획 파트 정책을 상속받습니다.

---

## 프로젝트 개요

### 목표

- 외부 LLM API 의존 없이 로컬 환경에서 AI 분석 제공
- 보안 이슈 및 추가 비용 없음
- 비개발자도 SKILL 파일(.md)로 분석 규칙 정의 가능
- 다양한 스포츠 종목으로 확장 가능한 구조

### 적용 범위

- 1차: 배드민턴 (BWF)
- 2차: BXL, 야구, 골프 등 확장

---

## 세션 시작 체크리스트

**Claude Code 세션 시작 시 반드시 수행:**

1. **Ollama 상태 확인**
   ```bash
   # Ollama 서버 상태 확인
   curl http://localhost:11434/api/tags
   ```

2. **모델 로드 확인**
   ```bash
   # 사용 가능한 모델 목록
   ollama list
   ```

3. **Redis 연결 확인**
   ```bash
   redis-cli ping
   ```

4. **가상환경 활성화**
   ```bash
   cd ~/work/llm-chatbot
   source .venv/bin/activate
   ```

---

## 참조 프로젝트 (btn)

> **"btn"이라고 하면 `~/work/btn` 폴더를 참조**

llm-chatbot은 btn 프로젝트의 디자인 패턴을 따릅니다. 구조나 패턴이 불명확할 때 btn을 참조하세요.

### btn 디자인 패턴 요약

| 구성요소 | 패턴 | 참조 파일 |
|---------|------|----------|
| 환경설정 | `Config` 클래스 + `@property` | `btn/class_config/class_env.py` |
| DB 연결 | `@dataclass` + 세션 팩토리 | `btn/class_config/class_db.py` |
| Redis | 클라이언트 클래스 + 싱글톤 | `btn/class_lib/bxl_api/redis_client.py` |
| API 앱 | `create_app()` 팩토리 함수 | `btn/apps/bwf/app.py` |
| 라우터 | `APIRouter` 분리 | `btn/apps/bwf/router.py` |
| 진입점 | 서브앱 마운트 + lifespan | `btn/main_http.py` |

### btn 핵심 패턴

```python
# 1. Config - 환경변수 로드 (@property 패턴)
class Config:
    @property
    def redis_url(self):
        return self.env('REDIS_URL')

# 2. 비즈니스 클래스 - 내부에서 Config 생성, logger만 주입
class Auth:
    def __init__(self, logger):
        self.config = Config()      # 내부에서 직접 생성
        self.db = ConfigDB()        # 내부에서 직접 생성
        self.logger = logger        # 외부에서 주입

# 3. 의존성 관리 - 모듈 레벨 인스턴스 + FastAPI Depends
# deps.py
logger = ConfigLogger('http_log', 365).get_logger('auth')
auth = Auth(logger)

def get_current_payload(request: Request):
    token = request.cookies.get("access_token")
    return auth.verify_access_token(token)

# 4. API 앱 - 팩토리 함수
def create_app() -> FastAPI:
    app = FastAPI(title="...")
    app.include_router(router)
    return app
```

---

## 기술 스택

### Backend API

| 항목 | 기술 |
|------|------|
| Framework | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy (async) |
| Validation | Pydantic |
| Auth | JWT (BWF/BXL과 동일) |

### LLM

| 항목 | 기술 |
|------|------|
| LLM Server | Ollama |
| Model | DeepSeek (또는 동급 오픈소스) |
| 호출 방식 | HTTP API (스트리밍 지원) |

### Web Component (embed)

| 항목 | 기술 |
|------|------|
| Language | TypeScript |
| Build | Vite |
| Chart | Chart.js |
| 배포 | embed.js (CDN 또는 정적 서버) |

### Infra

| 항목 | 기술 |
|------|------|
| Session | Redis |
| Database | PostgreSQL (기존 BWF/BXL DB) |
| Container | Docker |

---

## 핵심 설계 결정

### 1. 연동 방식: Web Component

BWF, BXL 등 여러 프로젝트에 동일하게 적용 가능한 구조

```html
<script src="https://chatbot.domain.com/embed.js"></script>
<spo-chatbot 
  theme="bwf"
  context-type="badminton"
  :match-id="currentMatchId"
  :token="authStore.token">
</spo-chatbot>
```

### 2. 컨텍스트 관리: 세션 기반

- Redis 기반 세션 상태 관리
- 세션 키: `session:{user_id}:{context_type}`
- 저장: 현재 경기 ID, 선수 ID, 대화 히스토리

### 3. 데이터 조회: 하이브리드

| 질문 유형 | 처리 방식 |
|----------|----------|
| 단순/자주 묻는 질문 | SQL 템플릿 사용 |
| 복잡/예측 불가 질문 | LLM 기반 Text-to-SQL |

### 4. 응답 형식: 텍스트 + 차트

```json
{
  "text": "안세영 선수는 효율적인 드롭샷으로...",
  "charts": [
    {
      "type": "bar",
      "title": "샷 유형별 득점률",
      "data": { ... }
    }
  ]
}
```

### 5. 정책 파일: 마크다운 통일

- 비개발자도 수정 가능
- 버전 관리 용이
- 경로: `skills/*.md`

---

## 경계 시스템 (Boundary System)

### ✅ Always (항상 수행)

| 항목 | 설명 |
|------|------|
| Ollama 상태 확인 | 세션 시작 시 LLM 서버 상태 확인 |
| 가상환경 활성화 | Python 작업 전 `source .venv/bin/activate` |
| 기존 패턴 확인 | btn 프로젝트의 class_config, class_lib 패턴 따름 |
| SKILL 파일 검증 | LLM 응답 품질 테스트 후 수정 |
| 코드 수정 전 분석 | 문제 정의 → 코드 흐름 분석 → 근본 원인 → 수정 방안 → 사용자 승인 |

### ⚠️ Ask First (승인 필요)

| 항목 | 설명 |
|------|------|
| SKILL 파일 수정 | 분석 규칙 변경 시 승인 |
| SQL 템플릿 추가/수정 | 쿼리 변경 시 승인 |
| 새 패키지 설치 | pip install 전 사용자 승인 |
| LLM 모델 변경 | 모델 교체 시 승인 |
| DB 스키마 접근 | Text-to-SQL용 스키마 정보 수정 시 |

### 🚫 Never (절대 금지)

| 항목 | 설명 |
|------|------|
| .env / 시크릿 커밋 | credentials, API 키, JWT 시크릿 커밋 금지 |
| pip install 임의 실행 | 패키지 임의 설치 금지 |
| 분석 없이 코드 수정 | 근본 원인 파악 없이 수정 금지 |
| Text-to-SQL 무검증 실행 | LLM 생성 SQL은 반드시 검증 후 실행 |
| 프로덕션 DB 직접 수정 | DML/DDL은 승인 후 실행 |

---

## SKILL 파일 정책

### 파일 구조

```
skills/
├── _base.md              # 공통 규칙 (모든 종목 적용)
├── badminton.md          # 배드민턴 분석 정책
├── baseball.md           # (추후 확장)
└── golf.md               # (추후 확장)
```

### SKILL 파일 형식

```markdown
# {종목} 분석 SKILL

## 역할
당신은 {종목} 경기 분석 전문가입니다.

## 분석 관점
- 관점 1
- 관점 2

## 응답 규칙
- 규칙 1
- 규칙 2

## 차트 생성 규칙
- 조건 → 차트 유형

## 차트 데이터 형식
JSON 형식으로 응답 끝에 포함
```

### 수정 절차

1. 로컬에서 SKILL 파일 수정
2. 테스트 질문으로 응답 품질 확인
3. 품질 확인 후 커밋

---

## SQL 템플릿 정책

### 파일 구조

```
queries/
├── badminton/
│   ├── match_summary.sql     # 경기 요약
│   ├── player_stats.sql      # 선수 통계
│   └── shot_distribution.sql # 샷 분포
└── baseball/                 # (추후 확장)
```

### 템플릿 형식

```sql
-- 설명: 경기 요약 조회
-- Parameters: match_id
-- 관련 질문: "경기 결과 알려줘", "누가 이겼어?"

SELECT ...
FROM ...
WHERE match_id = :match_id;
```

### 추가 절차

1. 자주 묻는 질문 패턴 분석
2. SQL 템플릿 작성
3. Query Router에 키워드 매핑 추가
4. 테스트 후 커밋

---

## 디렉토리 구조

> 단계적으로 업데이트 예정

```
llm-chatbot/
├── CLAUDE.md                 # 현재 파일
├── README.md                 # 프로젝트 개요
├── requirements.txt          # Python 의존성
├── .env.example              # 환경변수 템플릿
├── .gitignore
│
├── class_config/             # 설정 클래스
├── class_lib/                # 비즈니스 로직
├── apps/                     # API 엔드포인트
├── queries/                  # SQL 템플릿
├── skills/                   # SKILL 정책 파일
├── embed/                    # Web Component
├── docker/                   # Docker 설정
├── scripts/                  # 실행 스크립트
├── logs/                     # 로그
├── docs/                     # 문서
│
└── main_http.py              # FastAPI 진입점
```

---

## 환경 설정

### 환경변수 (.env)

```bash
# LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=deepseek-coder:6.7b

# Database (기존 BWF/BXL DB)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=spotv
DB_USER=postgres
DB_PASSWORD=

# Redis
REDIS_URL=redis://localhost:6379

# Auth (BWF/BXL과 동일)
JWT_SECRET=
JWT_ALGORITHM=HS256

# Session
SESSION_TTL=1800
```

### 개발 환경 (WSL)

```bash
# 저장소 클론
cd ~/work
git clone git@github.com:delkizer/llm-chatbot.git
cd llm-chatbot

# 가상환경 생성 (pyenv + venv)
python3 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 편집
```

### 운영 환경 (AWS EC2)

```bash
# 동일한 설치 과정
# .env 값만 운영 환경에 맞게 설정
```

---

## 관련 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| 아키텍처 | `docs/ARCHITECTURE.md` | 시스템 구조 |
| 프로젝트 구조 | `docs/PROJECT_STRUCTURE.md` | 디렉토리 상세 |
| 개발 로드맵 | `docs/ROADMAP.md` | 개발 순서 |
| SKILL 가이드 | `docs/SKILL_GUIDE.md` | SKILL 파일 작성법 |
| API 명세 | `docs/API_SPEC.md` | API 엔드포인트 |

---

## Git 저장소

| 항목 | 값 |
|------|-----|
| Repository | `delkizer/llm-chatbot` |
| URL | `git@github.com:delkizer/llm-chatbot.git` |

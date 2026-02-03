# LLM Chatbot

로컬 LLM 기반 스포츠 데이터 Q&A 챗봇

## 개요

외부 LLM API 의존 없이 로컬 환경에서 스포츠 경기 데이터를 분석하고 질의응답하는 챗봇 시스템입니다.

### 주요 특징

- **로컬 LLM**: Ollama + DeepSeek 기반, 외부 API 비용 없음
- **보안**: 데이터가 외부로 전송되지 않음
- **확장성**: 종목별 분석 규칙 정의 가능
- **범용성**: Web Component로 여러 서비스에 동일하게 적용

### 적용 범위

- 1차: 배드민턴 (BWF)
- 2차: BXL, 야구, 골프 등 확장

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | FastAPI (Python 3.11+) |
| LLM | Ollama + DeepSeek |
| Session | Redis |
| Database | PostgreSQL |
| Frontend | Web Component (TypeScript) |

## 빠른 시작

### 1. 저장소 클론

```bash
cd ~/work
git clone git@github.com:delkizer/llm-chatbot.git
cd llm-chatbot
```

### 2. 가상환경 설정

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
cp .env.example .env
# .env 파일 편집
```

### 4. Ollama 설치 및 모델 다운로드

```bash
# Ollama 설치 (Ubuntu)
curl -fsSL https://ollama.com/install.sh | sh

# 모델 다운로드
ollama pull deepseek-coder:6.7b
```

### 5. 서버 실행

```bash
python main_http.py
```

## 라이선스

Private - SPOTV 내부용

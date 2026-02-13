# LLM 인프라 분석: AWS EC2 GPU 환경의 한계와 대안

> 작성일: 2026-02-13

---

## 1. 배경

llm-chatbot 프로젝트의 핵심 목표 중 하나는 **외부 LLM API 의존 없이 로컬 환경에서 AI 분석 제공**이었다. 그러나 EC2 테스트 서버(t2.large) 배포 과정에서 CPU 전용 환경의 LLM 성능 한계가 확인되었다.

---

## 2. 테스트 결과

### 2.1 테스트 환경

| 항목 | 값 |
|------|-----|
| 인스턴스 | t2.large |
| vCPU | 2 |
| RAM | 8 GB |
| GPU | 없음 |
| OS | Ubuntu 24.04 LTS |
| Ollama | 최신 (CPU 모드) |

### 2.2 성능 측정

| 모델 | 크기 | 메모리 사용 | 첫 토큰 응답 시간 | 비고 |
|------|------|-----------|-----------------|------|
| qwen2.5:7b | ~5 GB | 61.9% (4.8 GB) | 응답 없음 (6분+ 후 중단) | 실사용 불가 |
| qwen2.5:3b | ~2 GB | - | ~8분 26초 | 실사용 불가 |

### 2.3 원인 분석

- **CPU 추론의 근본적 한계**: LLM 추론은 행렬 연산 집약 작업으로, GPU 병렬 처리에 최적화됨. CPU에서는 순차 처리로 극도로 느림
- **메모리 압박**: 7b 모델이 5 GB 점유 → 8 GB RAM에서 시스템 여유 150 MB. 스왑 미설정으로 OOM 위험
- **SKILL 프롬프트 영향**: 시스템 프롬프트(SKILL 파일)가 ~2K 토큰으로, 첫 추론 시 전체 컨텍스트 처리 부하 가중

---

## 3. AWS EC2 GPU 인스턴스 비용 분석

### 3.1 인스턴스 비교 (서울 리전, 온디맨드)

| 인스턴스 | vCPU | RAM | GPU | VRAM | 시간당 | 월 (24/7) |
|---------|------|-----|-----|------|--------|----------|
| t2.large (현재) | 2 | 8 GB | - | - | ~$0.12 | ~$87 |
| g4dn.xlarge | 4 | 16 GB | T4 x1 | 16 GB | ~$0.66 | ~$475 |
| g4dn.2xlarge | 8 | 32 GB | T4 x1 | 16 GB | ~$0.98 | ~$706 |
| g5.xlarge | 4 | 16 GB | A10G x1 | 24 GB | ~$1.19 | ~$857 |

### 3.2 스팟 인스턴스

| 인스턴스 | 온디맨드 | 스팟 (예상) | 절감율 | 리스크 |
|---------|---------|-----------|--------|--------|
| g4dn.xlarge | ~$0.66/hr | ~$0.20/hr | ~70% | 중단 가능성 |

스팟은 비용 절감 효과가 크지만, 언제든 회수될 수 있어 안정적 서비스에는 부적합.

---

## 4. 대안 비교

### 4.1 방안별 비교

| 방안 | 월 비용 | 응답 속도 | 품질 | 보안 | 운영 부담 |
|------|--------|----------|------|------|----------|
| **A. GPU EC2 (g4dn.xlarge)** | ~$475 | 빠름 | 7b 수준 | 데이터 외부 유출 없음 | 중간 |
| **B. 외부 LLM API (Claude 등)** | ~$30-50 (이용량 비례) | 빠름 | 높음 | 데이터 외부 전송 | 낮음 |
| **C. CPU EC2 + 경량 모델** | ~$87 (현재) | 매우 느림 | 낮음 | 데이터 외부 유출 없음 | 중간 |
| **D. 사내 GPU 서버** | 초기 구축비 | 빠름 | 7b+ | 데이터 외부 유출 없음 | 높음 |
| **E. 로컬 PC + 터널** | ~$0 | 빠름 | 7b 수준 | 데이터 외부 유출 없음 | 높음 (가용성 낮음) |

### 4.2 외부 LLM API 비용 시뮬레이션 (Claude Sonnet 4.5 기준)

| 일일 이용량 | 월 입력 토큰 | 월 출력 토큰 | 월 비용 (예상) |
|-----------|-----------|-----------|-------------|
| 10건/일 | ~3M | ~1.5M | ~$10-15 |
| 50건/일 | ~15M | ~7.5M | ~$30-50 |
| 200건/일 | ~60M | ~30M | ~$120-200 |

> 산출 기준: SKILL 시스템 프롬프트 ~2K tokens, 평균 대화 ~3K tokens (입력+출력)

---

## 5. 권장 방안

### 5.1 단기 (테스트/PoC)

**방안 B: 외부 LLM API 전환**

- 이용율이 낮은 현재 상황에서 가장 비용 효율적
- 기존 아키텍처 변경 최소화: `OllamaClient` → `LLMClient` 인터페이스 추상화
- SKILL 파일 체계 그대로 유지 (system prompt로 주입)
- `.env`에서 `LLM_PROVIDER=claude` / `ollama` 전환 가능

### 5.2 중장기 (이용량 증가 시)

- 일일 200건 이상 → GPU 인프라 검토 (사내 서버 또는 GPU EC2)
- 비용 분기점: 외부 API 월 $200 이상 시 GPU 인스턴스(g4dn.xlarge $475)와 비교 의미 생김

---

## 6. 아키텍처 전환 설계 (방안 B 채택 시)

### 6.1 변경 범위

```
현재:  ChatService → OllamaClient → localhost:11434 (Ollama)
변경:  ChatService → LLMClient (인터페이스)
                       ├→ OllamaClient  (로컬 개발용 유지)
                       └→ ClaudeClient  (운영용 추가)
```

### 6.2 환경변수

```bash
# LLM Provider 선택
LLM_PROVIDER=claude          # claude | ollama

# Claude API (LLM_PROVIDER=claude 일 때)
CLAUDE_API_KEY=<API 키>
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# Ollama (LLM_PROVIDER=ollama 일 때, 기존과 동일)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

### 6.3 영향 파일

| 파일 | 변경 |
|------|------|
| `class_lib/llm_client.py` | 신규 — LLMClient 인터페이스 (ABC) |
| `class_lib/ollama_client.py` | LLMClient 인터페이스 구현으로 리팩터링 |
| `class_lib/claude_client.py` | 신규 — Claude API 구현체 |
| `class_lib/chat_service.py` | LLMClient 인터페이스 사용으로 변경 |
| `class_config/class_env.py` | Claude 관련 환경변수 프로퍼티 추가 |
| `requirements.txt` | `anthropic` 패키지 추가 |

### 6.4 보안 고려사항

- 경기 데이터가 외부 API로 전송됨 → 사내 데이터 정책 확인 필요
- API 키 관리: `.env`에서 관리, `.gitignore`에 의해 제외됨
- 민감 데이터 마스킹 정책 검토

---

## 7. 결론

| 결정 사항 | 내용 |
|----------|------|
| CPU 전용 EC2에서 LLM 운영 | **불가** (7b, 3b 모두 실사용 불가능한 응답 시간) |
| GPU EC2 (g4dn.xlarge) | 월 $475 — 현재 예산 범위 초과 |
| 외부 LLM API 전환 | **권장** — 낮은 이용율에서 월 $30-50, 품질 향상 |
| 로컬 Ollama | 개발 환경 전용으로 유지 |

---

## 8. 관련 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| 배포 개요 | `docs/deployment/01-deployment-overview.md` | 환경별 설정 매트릭스 |
| 운영 배포 가이드 | `docs/deployment/04-production-deploy-guide.md` | 배포 체크리스트 |
| Ollama API 스펙 | `docs/ollama/01-ollama-api-spec.md` | 현재 LLM 연동 스펙 |

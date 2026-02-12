#!/bin/bash

# ============================================================
# spo-chatbot 프레임워크 샘플 일괄 관리 스크립트
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 샘플 목록 및 포트 정의
declare -A PORTS=(
  [vanilla]=5170
  [vue3]=5171
  [react]=5172
  [svelte]=5173
  [nextjs]=5174
  [angular]=5175
  [htmx]=5176
  [iframe]=5177
)

# PID 파일 경로
PID_FILE="$SCRIPT_DIR/.dev-pids"

# ============================================================
# 유틸리티 함수
# ============================================================

info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
  echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

header() {
  echo ""
  echo -e "${CYAN}========================================${NC}"
  echo -e "${CYAN} $1${NC}"
  echo -e "${CYAN}========================================${NC}"
  echo ""
}

# ============================================================
# install — 전체 샘플 의존성 설치
# ============================================================

cmd_install() {
  header "의존성 설치"

  # npm 기반 샘플
  for sample in vue3 react svelte nextjs angular; do
    local dir="$SCRIPT_DIR/$sample"
    if [ -f "$dir/package.json" ]; then
      info "$sample: npm install 실행 중..."
      (cd "$dir" && npm install)
      success "$sample: 설치 완료"
    else
      warn "$sample: package.json 없음, 스킵"
    fi
  done

  # pip 기반 샘플
  if [ -f "$SCRIPT_DIR/htmx/requirements.txt" ]; then
    info "htmx: pip install 실행 중..."
    (cd "$SCRIPT_DIR/htmx" && pip install -r requirements.txt)
    success "htmx: 설치 완료"
  else
    warn "htmx: requirements.txt 없음, 스킵"
  fi

  # 정적 샘플
  info "vanilla: 정적 HTML — 설치 불필요, 스킵"
  info "iframe: 정적 HTML — 설치 불필요, 스킵"

  echo ""
  success "전체 의존성 설치 완료"
}

# ============================================================
# dev — 개발 서버 실행
# ============================================================

start_sample() {
  local sample=$1
  local port=${PORTS[$sample]}
  local dir="$SCRIPT_DIR/$sample"

  case $sample in
    vanilla)
      info "vanilla: python3 -m http.server $port"
      (cd "$dir" && python3 -m http.server "$port") &
      echo "$! $sample" >> "$PID_FILE"
      ;;
    vue3|react|svelte)
      info "$sample: npm run dev (port $port)"
      (cd "$dir" && npm run dev) &
      echo "$! $sample" >> "$PID_FILE"
      ;;
    nextjs)
      info "nextjs: npm run dev (port $port)"
      (cd "$dir" && npm run dev) &
      echo "$! $sample" >> "$PID_FILE"
      ;;
    angular)
      info "angular: npm run start (port $port)"
      (cd "$dir" && npm run start) &
      echo "$! $sample" >> "$PID_FILE"
      ;;
    htmx)
      info "htmx: uvicorn server:app --port $port --reload"
      (cd "$dir" && uvicorn server:app --port "$port" --reload) &
      echo "$! $sample" >> "$PID_FILE"
      ;;
    iframe)
      info "iframe: python3 -m http.server $port"
      (cd "$dir" && python3 -m http.server "$port") &
      echo "$! $sample" >> "$PID_FILE"
      ;;
    *)
      error "알 수 없는 샘플: $sample"
      return 1
      ;;
  esac
}

cmd_dev() {
  local target=$1

  if [ -n "$target" ]; then
    # 특정 샘플만 포그라운드 실행
    header "$target 개발 서버 실행 (포그라운드)"

    local port=${PORTS[$target]}
    if [ -z "$port" ]; then
      error "알 수 없는 샘플: $target"
      echo "사용 가능: vanilla, vue3, react, svelte, nextjs, angular, htmx, iframe"
      exit 1
    fi

    local dir="$SCRIPT_DIR/$target"
    info "포트: $port"
    echo ""

    case $target in
      vanilla)
        (cd "$dir" && python3 -m http.server "$port")
        ;;
      vue3|react|svelte)
        (cd "$dir" && npm run dev)
        ;;
      nextjs)
        (cd "$dir" && npm run dev)
        ;;
      angular)
        (cd "$dir" && npm run start)
        ;;
      htmx)
        (cd "$dir" && uvicorn server:app --port "$port" --reload)
        ;;
      iframe)
        (cd "$dir" && python3 -m http.server "$port")
        ;;
    esac
  else
    # 전체 백그라운드 실행
    header "전체 샘플 개발 서버 실행 (백그라운드)"

    # 기존 PID 파일 초기화
    > "$PID_FILE"

    for sample in vanilla vue3 react svelte nextjs angular htmx iframe; do
      local dir="$SCRIPT_DIR/$sample"
      if [ -d "$dir" ]; then
        start_sample "$sample"
        success "$sample: 시작됨 (port ${PORTS[$sample]})"
      else
        warn "$sample: 디렉토리 없음, 스킵"
      fi
    done

    echo ""
    success "전체 개발 서버 시작 완료"
    echo ""
    info "포트 목록:"
    for sample in vanilla vue3 react svelte nextjs angular htmx iframe; do
      echo -e "  ${CYAN}$sample${NC}: http://localhost:${PORTS[$sample]}"
    done
    echo ""
    info "종료: ./manage.sh stop"
  fi
}

# ============================================================
# build — 빌드 가능한 샘플 빌드
# ============================================================

cmd_build() {
  header "샘플 빌드"

  for sample in vue3 react svelte angular; do
    local dir="$SCRIPT_DIR/$sample"
    if [ -f "$dir/package.json" ]; then
      info "$sample: npm run build"
      (cd "$dir" && npm run build)
      success "$sample: 빌드 완료"
    else
      warn "$sample: package.json 없음, 스킵"
    fi
  done

  # Next.js
  if [ -f "$SCRIPT_DIR/nextjs/package.json" ]; then
    info "nextjs: npm run build"
    (cd "$SCRIPT_DIR/nextjs" && npm run build)
    success "nextjs: 빌드 완료"
  fi

  info "vanilla, htmx, iframe: 빌드 불필요, 스킵"

  echo ""
  success "전체 빌드 완료"
}

# ============================================================
# clean — 빌드 산출물 및 의존성 제거
# ============================================================

cmd_clean() {
  header "클린업"

  for sample in vue3 react svelte nextjs angular; do
    local dir="$SCRIPT_DIR/$sample"
    if [ -d "$dir/node_modules" ]; then
      info "$sample: node_modules 삭제"
      rm -rf "$dir/node_modules"
      success "$sample: node_modules 삭제 완료"
    fi
    if [ -d "$dir/dist" ]; then
      rm -rf "$dir/dist"
      info "$sample: dist 삭제"
    fi
  done

  # Next.js 전용
  if [ -d "$SCRIPT_DIR/nextjs/.next" ]; then
    rm -rf "$SCRIPT_DIR/nextjs/.next"
    info "nextjs: .next 삭제"
  fi

  # HTMX (Python)
  if [ -d "$SCRIPT_DIR/htmx/__pycache__" ]; then
    rm -rf "$SCRIPT_DIR/htmx/__pycache__"
    info "htmx: __pycache__ 삭제"
  fi

  # PID 파일
  if [ -f "$PID_FILE" ]; then
    rm -f "$PID_FILE"
    info "PID 파일 삭제"
  fi

  echo ""
  success "클린업 완료"
}

# ============================================================
# serve — 게이트웨이 서버 실행 (단일 포트 8280)
# ============================================================

cmd_serve() {
  header "게이트웨이 서버 실행 (포트 8280)"

  info "http://localhost:8280/ 에서 전체 샘플 접근 가능"
  echo ""
  (cd "$SCRIPT_DIR" && uvicorn gateway:app --port 8280 --reload)
}

# ============================================================
# build-all — embed.js + 전체 샘플 빌드
# ============================================================

cmd_build_all() {
  header "전체 빌드 (embed.js + 샘플)"

  # 1. embed.js 빌드
  local embed_dir="$SCRIPT_DIR/.."
  if [ -f "$embed_dir/package.json" ]; then
    info "embed.js: npm run build"
    (cd "$embed_dir" && npm run build)
    success "embed.js: 빌드 완료"
  else
    warn "embed/package.json 없음, embed.js 빌드 스킵"
  fi

  echo ""

  # 2. 샘플 빌드
  cmd_build

  echo ""
  success "전체 빌드 완료 (embed.js + 샘플)"
}

# ============================================================
# stop — 백그라운드 프로세스 종료
# ============================================================

cmd_stop() {
  header "개발 서버 종료"

  if [ ! -f "$PID_FILE" ]; then
    warn "실행 중인 프로세스 없음 (PID 파일 없음)"
    return 0
  fi

  while IFS=' ' read -r pid sample; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null
      success "$sample (PID $pid): 종료됨"
    else
      info "$sample (PID $pid): 이미 종료됨"
    fi
  done < "$PID_FILE"

  rm -f "$PID_FILE"

  echo ""
  success "전체 개발 서버 종료 완료"
}

# ============================================================
# 사용법
# ============================================================

cmd_usage() {
  echo ""
  echo -e "${CYAN}spo-chatbot 샘플 관리 스크립트${NC}"
  echo ""
  echo "사용법:"
  echo "  ./manage.sh install          전체 샘플 의존성 설치"
  echo "  ./manage.sh dev              전체 샘플 개발 서버 실행 (백그라운드)"
  echo "  ./manage.sh dev [샘플명]     특정 샘플 개발 서버 실행 (포그라운드)"
  echo "  ./manage.sh build            빌드 가능한 샘플 빌드"
  echo "  ./manage.sh build-all        embed.js + 전체 샘플 빌드"
  echo "  ./manage.sh serve            게이트웨이 서버 실행 (포트 8280, 단일 포트)"
  echo "  ./manage.sh clean            node_modules, dist, __pycache__ 등 제거"
  echo "  ./manage.sh stop             백그라운드 개발 서버 종료"
  echo ""
  echo "개발 서버 (개별 포트):"
  echo "  vanilla (5170), vue3 (5171), react (5172), svelte (5173)"
  echo "  nextjs (5174), angular (5175), htmx (5176), iframe (5177)"
  echo ""
  echo "게이트웨이 (단일 포트):"
  echo "  http://localhost:8280/  — 전체 샘플 통합 서빙"
  echo ""
}

# ============================================================
# 메인
# ============================================================

case "${1:-}" in
  install)
    cmd_install
    ;;
  dev)
    cmd_dev "$2"
    ;;
  build)
    cmd_build
    ;;
  build-all)
    cmd_build_all
    ;;
  serve)
    cmd_serve
    ;;
  clean)
    cmd_clean
    ;;
  stop)
    cmd_stop
    ;;
  *)
    cmd_usage
    ;;
esac

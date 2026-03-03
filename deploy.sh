#!/bin/bash
# deploy.sh - LLM Chatbot 배포 스크립트
#
# 운영 환경: bxl-test-db (EC2)
# Nginx: chatbot-dev.delkizer.com → Backend(7002), Gateway(5174)
#
# 사용법: ./deploy.sh [deploy|restart|build|status|setup]

# ─────────────────────────────────────────────
# 변수 정의
# ─────────────────────────────────────────────
PROJECT_DIR="/home/ubuntu/work/llm-chatbot"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"

API_SERVICE="llm_chatbot_http"
GATEWAY_SERVICE="llm_chatbot_gateway"
API_PORT=7002
GATEWAY_PORT=5174

# ─────────────────────────────────────────────
# 색상 코드
# ─────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ─────────────────────────────────────────────
# 유틸리티 함수
# ─────────────────────────────────────────────
print_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

ensure_dirs() {
    mkdir -p "$LOG_DIR"
}

# systemd 서비스 존재 여부 확인
service_exists() {
    local service_name="$1"
    systemctl list-unit-files 2>/dev/null | grep -q "${service_name}.service"
}

# nvm 환경 로드 (npm/node PATH 확보)
load_nvm() {
    export NVM_DIR="$HOME/.nvm"
    if [ -s "$NVM_DIR/nvm.sh" ]; then
        . "$NVM_DIR/nvm.sh"
    fi
}

# ─────────────────────────────────────────────
# build_front: 프론트엔드 빌드 (embed.js)
# ─────────────────────────────────────────────
build_front() {
    echo -n "[FRONT]   Building embed.js...             "

    load_nvm

    if ! command -v npm &>/dev/null; then
        print_fail
        echo "          npm을 찾을 수 없습니다. nvm/node 설치를 확인하세요."
        return 1
    fi

    cd "$PROJECT_DIR/embed" || { print_fail; return 1; }

    # node_modules 없으면 install
    if [ ! -d "node_modules" ]; then
        npm install --silent 2>&1 | tail -1
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            print_fail
            echo "          npm install 실패"
            cd "$PROJECT_DIR"
            return 1
        fi
    fi

    # 빌드
    local build_output
    build_output=$(npm run build 2>&1)
    if [ $? -ne 0 ]; then
        print_fail
        echo "$build_output" | tail -5
        cd "$PROJECT_DIR"
        return 1
    fi

    # 결과 확인
    local dist_file="$PROJECT_DIR/embed/dist/embed.js"
    if [ -f "$dist_file" ]; then
        local file_size
        file_size=$(du -h "$dist_file" | cut -f1)
        echo -e "${GREEN}[OK]${NC} (${file_size})"
    else
        print_fail
        echo "          빌드 파일이 생성되지 않았습니다."
        cd "$PROJECT_DIR"
        return 1
    fi

    cd "$PROJECT_DIR"
    return 0
}

# ─────────────────────────────────────────────
# deploy_all: 전체 배포
# ─────────────────────────────────────────────
deploy_all() {
    echo ""
    echo "============================================"
    echo " LLM Chatbot - Deploy"
    echo "============================================"
    echo ""

    # --- git pull ---
    echo -n "[GIT]     Pulling latest...                "
    cd "$PROJECT_DIR" || { print_fail; return 1; }
    local git_output
    git_output=$(git pull origin main 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK]${NC}"
    else
        echo -e "${YELLOW}[WARN]${NC}"
        echo "          git pull 실패 (계속 진행): $git_output"
    fi

    # --- pip install ---
    echo -n "[PIP]     Installing dependencies...       "
    if [ -f "$VENV_DIR/bin/pip" ]; then
        local pip_output
        pip_output=$("$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt" 2>&1)
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}[OK]${NC}"
        else
            echo -e "${RED}[FAIL]${NC}"
            echo "          pip install 실패"
            echo "$pip_output" | tail -5
        fi
    else
        echo -e "${RED}[FAIL]${NC}"
        echo "          venv를 찾을 수 없습니다: $VENV_DIR"
    fi

    # --- 프론트엔드 빌드 ---
    build_front

    # --- API 서비스 재시작 ---
    echo -n "[API]     Restarting ${API_SERVICE}...  "
    if service_exists "$API_SERVICE"; then
        sudo systemctl restart "$API_SERVICE" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}[OK]${NC}"
        else
            echo -e "${RED}[FAIL]${NC}"
        fi
    else
        echo -e "${YELLOW}[SKIP]${NC} 서비스 미등록"
    fi

    # --- Gateway 서비스 재시작 ---
    echo -n "[GATEWAY] Restarting ${GATEWAY_SERVICE}..."
    if service_exists "$GATEWAY_SERVICE"; then
        sudo systemctl restart "$GATEWAY_SERVICE" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e " ${GREEN}[OK]${NC}"
        else
            echo -e " ${RED}[FAIL]${NC}"
        fi
    else
        echo -e " ${YELLOW}[SKIP]${NC} 서비스 미등록 (./deploy.sh setup 으로 등록)"
    fi

    echo ""
    echo "============================================"
    echo " Deploy complete"
    echo "============================================"
    echo ""

    # 배포 후 상태 확인
    check_status
}

# ─────────────────────────────────────────────
# restart_services: 서비스만 재시작 (빌드 없이)
# ─────────────────────────────────────────────
restart_services() {
    echo ""
    echo "============================================"
    echo " LLM Chatbot - Restart Services"
    echo "============================================"
    echo ""

    # --- API 서비스 재시작 ---
    echo -n "[API]     Restarting ${API_SERVICE}...  "
    if service_exists "$API_SERVICE"; then
        sudo systemctl restart "$API_SERVICE" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}[OK]${NC}"
        else
            echo -e "${RED}[FAIL]${NC}"
        fi
    else
        echo -e "${YELLOW}[SKIP]${NC} 서비스 미등록"
    fi

    # --- Gateway 서비스 재시작 ---
    echo -n "[GATEWAY] Restarting ${GATEWAY_SERVICE}..."
    if service_exists "$GATEWAY_SERVICE"; then
        sudo systemctl restart "$GATEWAY_SERVICE" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e " ${GREEN}[OK]${NC}"
        else
            echo -e " ${RED}[FAIL]${NC}"
        fi
    else
        echo -e " ${YELLOW}[SKIP]${NC} 서비스 미등록 (./deploy.sh setup 으로 등록)"
    fi

    echo ""
    echo "============================================"
    echo " Restart complete"
    echo "============================================"
}

# ─────────────────────────────────────────────
# check_status: 전체 상태 확인
# ─────────────────────────────────────────────
check_status() {
    echo ""
    echo "============================================"
    echo " LLM Chatbot Status"
    echo "============================================"
    echo ""

    # --- API 상태 ---
    echo -n "[API]     Service:   "
    if service_exists "$API_SERVICE"; then
        local api_status
        api_status=$(systemctl is-active "$API_SERVICE" 2>/dev/null)
        if [ "$api_status" = "active" ]; then
            echo -e "${GREEN}active${NC} (${API_SERVICE})"
        else
            echo -e "${RED}${api_status}${NC} (${API_SERVICE})"
        fi
    else
        echo -e "${YELLOW}not registered${NC}"
    fi

    echo -n "[API]     Port ${API_PORT}: "
    if ss -tlnp 2>/dev/null | grep -q ":${API_PORT} "; then
        echo -e "${GREEN}listening${NC}"
    else
        echo -e "${RED}not listening${NC}"
    fi

    echo -n "[API]     Health:    "
    local api_health
    api_health=$(curl -s --max-time 3 "http://localhost:${API_PORT}/api/chat/health" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$api_health" ]; then
        echo -e "${GREEN}ok${NC}"
    else
        echo -e "${RED}unreachable${NC}"
    fi

    echo ""

    # --- Gateway 상태 ---
    echo -n "[GATEWAY] Service:   "
    if service_exists "$GATEWAY_SERVICE"; then
        local gw_status
        gw_status=$(systemctl is-active "$GATEWAY_SERVICE" 2>/dev/null)
        if [ "$gw_status" = "active" ]; then
            echo -e "${GREEN}active${NC} (${GATEWAY_SERVICE})"
        else
            echo -e "${RED}${gw_status}${NC} (${GATEWAY_SERVICE})"
        fi
    else
        echo -e "${YELLOW}not registered${NC} (./deploy.sh setup 으로 등록)"
    fi

    echo -n "[GATEWAY] Port ${GATEWAY_PORT}: "
    if ss -tlnp 2>/dev/null | grep -q ":${GATEWAY_PORT} "; then
        echo -e "${GREEN}listening${NC}"
    else
        echo -e "${RED}not listening${NC}"
    fi

    echo ""

    # --- 프론트엔드 빌드 상태 ---
    echo -n "[FRONT]   embed.js:  "
    local dist_file="$PROJECT_DIR/embed/dist/embed.js"
    if [ -f "$dist_file" ]; then
        local file_size
        file_size=$(du -h "$dist_file" | cut -f1)
        local mod_time
        mod_time=$(stat -c '%Y' "$dist_file" 2>/dev/null)
        local mod_date
        mod_date=$(date -d "@$mod_time" '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
        echo -e "${GREEN}exists${NC} (${file_size}, built: ${mod_date})"
    else
        echo -e "${YELLOW}not built${NC}"
    fi

    echo ""

    # --- Nginx 상태 ---
    echo -n "[NGINX]   Service:   "
    local nginx_status
    nginx_status=$(systemctl is-active nginx 2>/dev/null)
    if [ "$nginx_status" = "active" ]; then
        echo -e "${GREEN}active${NC}"
    else
        echo -e "${RED}${nginx_status}${NC}"
    fi

    echo ""
    echo "============================================"
}

# ─────────────────────────────────────────────
# setup_gateway: Gateway systemd 서비스 생성
# ─────────────────────────────────────────────
setup_gateway() {
    echo ""
    echo "============================================"
    echo " LLM Chatbot - Setup Gateway Service"
    echo "============================================"
    echo ""

    local service_file="/etc/systemd/system/${GATEWAY_SERVICE}.service"

    # 이미 존재하는지 확인
    if [ -f "$service_file" ]; then
        print_warn "서비스 파일이 이미 존재합니다: $service_file"
        echo -n "          덮어쓰시겠습니까? (y/N): "
        read -r answer
        if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
            print_info "취소되었습니다."
            return 0
        fi
    fi

    # 서비스 파일 생성
    echo -n "[SETUP]   Creating ${GATEWAY_SERVICE}.service... "
    sudo tee "$service_file" > /dev/null <<EOF
[Unit]
Description=LLM Chatbot Embed Gateway
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/work/llm-chatbot/embed/samples
ExecStart=/home/ubuntu/work/llm-chatbot/venv/bin/uvicorn \\
    gateway:app \\
    --host 0.0.0.0 --port ${GATEWAY_PORT}
Restart=always
RestartSec=3
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK]${NC}"
    else
        echo -e "${RED}[FAIL]${NC}"
        return 1
    fi

    # daemon-reload
    echo -n "[SETUP]   Reloading systemd daemon...       "
    sudo systemctl daemon-reload 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK]${NC}"
    else
        echo -e "${RED}[FAIL]${NC}"
        return 1
    fi

    # enable
    echo -n "[SETUP]   Enabling ${GATEWAY_SERVICE}...    "
    sudo systemctl enable "$GATEWAY_SERVICE" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK]${NC}"
    else
        echo -e "${RED}[FAIL]${NC}"
        return 1
    fi

    # start
    echo -n "[SETUP]   Starting ${GATEWAY_SERVICE}...    "
    sudo systemctl start "$GATEWAY_SERVICE" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK]${NC}"
    else
        echo -e "${RED}[FAIL]${NC}"
        return 1
    fi

    echo ""
    echo "============================================"
    echo " Gateway setup complete"
    echo "============================================"
    echo ""

    # 상태 확인
    echo "[SETUP]   서비스 상태:"
    systemctl status "$GATEWAY_SERVICE" --no-pager -l 2>/dev/null | head -10
}

# ─────────────────────────────────────────────
# usage: 사용법 출력
# ─────────────────────────────────────────────
usage() {
    echo ""
    echo "============================================"
    echo " LLM Chatbot 배포 스크립트"
    echo "============================================"
    echo ""
    echo "  운영 서버: bxl-test-db (EC2)"
    echo "  도메인:    chatbot-dev.delkizer.com"
    echo "  구조:      Nginx(443) → Backend(:${API_PORT}) + Gateway(:${GATEWAY_PORT})"
    echo ""
    echo "사용법: $0 {deploy|restart|build|status|setup}"
    echo ""
    echo "  deploy    코드 업데이트 + 전체 재배포"
    echo "            git pull → pip install → embed.js 빌드 → 서비스 재시작"
    echo "            일반적인 배포 시 이 명령을 사용합니다."
    echo ""
    echo "  restart   Backend(${API_SERVICE})와 Gateway(${GATEWAY_SERVICE}) 서비스만 재시작"
    echo "            코드 변경 없이 서비스를 재기동할 때 사용합니다."
    echo ""
    echo "  build     프론트엔드(embed/dist/embed.js)만 빌드"
    echo "            Web Component 소스(embed/src/)만 수정한 경우 사용합니다."
    echo ""
    echo "  status    전체 서비스 상태 확인"
    echo "            Backend, Gateway, Nginx 서비스 + 포트 + health 체크"
    echo ""
    echo "  setup     Gateway systemd 서비스를 /etc/systemd/system에 등록 (최초 1회)"
    echo "            서버 최초 구성 시 실행합니다. Backend(${API_SERVICE})는"
    echo "            이미 등록되어 있으므로 Gateway만 생성합니다."
    echo ""
    echo "예시:"
    echo "  $0 deploy          # 일반 배포"
    echo "  $0 status          # 상태 확인"
    echo "  $0 setup           # 최초 Gateway 서비스 등록"
    echo ""
}

# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────
ensure_dirs

case "$1" in
    deploy)
        deploy_all
        ;;
    restart)
        restart_services
        ;;
    build)
        echo ""
        build_front
        echo ""
        ;;
    status)
        check_status
        ;;
    setup)
        setup_gateway
        ;;
    *)
        usage
        exit 1
        ;;
esac

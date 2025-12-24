#!/bin/bash
# CoinAnk 服务器部署脚本
# 用于在 Linux 服务器上初始化和配置项目

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then
    log_warn "不建议使用 root 用户运行此脚本"
fi

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    log_error "无法检测操作系统"
    exit 1
fi

log_info "检测到操作系统: $OS $VER"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_step "1. 更新系统包管理器"
if command -v apt-get &> /dev/null; then
    sudo apt-get update
elif command -v yum &> /dev/null; then
    sudo yum update -y
elif command -v dnf &> /dev/null; then
    sudo dnf update -y
else
    log_warn "未识别的包管理器，请手动更新系统"
fi

log_step "2. 安装系统依赖"
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        wget \
        git \
        cron \
        libnss3-dev \
        libatk-bridge2.0-dev \
        libdrm-dev \
        libxcomposite-dev \
        libxdamage-dev \
        libxrandr-dev \
        libgbm-dev \
        libxss-dev \
        libasound2-dev \
        libatspi2.0-dev \
        libgtk-3-dev
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y \
        python3 \
        python3-pip \
        curl \
        wget \
        git \
        cronie \
        nss \
        atk \
        at-spi2-atk \
        gtk3 \
        cups-libs \
        libdrm \
        libXcomposite \
        libXdamage \
        libXrandr \
        mesa-libgbm \
        libXss \
        alsa-lib
elif command -v dnf &> /dev/null; then
    # Fedora
    sudo dnf install -y \
        python3 \
        python3-pip \
        curl \
        wget \
        git \
        cronie \
        nss \
        atk \
        at-spi2-atk \
        gtk3 \
        cups-libs \
        libdrm \
        libXcomposite \
        libXdamage \
        libXrandr \
        mesa-libgbm \
        libXss \
        alsa-lib
fi

log_step "3. 检查 Python 版本"
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
log_info "Python 版本: $PYTHON_VERSION"

# 检查 Python 版本是否满足要求
if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
    log_info "Python 版本满足要求 (>= 3.8)"
else
    log_error "Python 版本过低，需要 3.8 或更高版本"
    exit 1
fi

log_step "4. 创建虚拟环境"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    log_info "虚拟环境创建成功"
else
    log_info "虚拟环境已存在"
fi

log_step "5. 激活虚拟环境并安装依赖"
source .venv/bin/activate
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    log_info "Python 依赖安装完成"
else
    log_error "requirements.txt 文件不存在"
    exit 1
fi

log_step "6. 安装 Playwright 浏览器"
playwright install chromium
playwright install-deps chromium
log_info "Playwright 浏览器安装完成"

log_step "7. 配置环境变量"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_warn "已创建 .env 文件，请编辑并填入正确的配置:"
        log_warn "  - GITHUB_TOKEN: GitHub 个人访问令牌"
        log_warn "  - NOTION_TOKEN: Notion 集成令牌"
        log_warn "  - NOTION_DB_ID: Notion 数据库 ID"
    else
        log_error ".env.example 文件不存在"
        exit 1
    fi
else
    log_info ".env 文件已存在"
fi

log_step "8. 创建必要的目录"
mkdir -p logs
mkdir -p images
log_info "目录创建完成"

log_step "9. 设置文件权限"
chmod +x run_server.sh
if [ -f "main_optimized.py" ]; then
    chmod +x main_optimized.py
fi
if [ -f "main.py" ]; then
    chmod +x main.py
fi
log_info "文件权限设置完成"

log_step "10. 测试运行"
log_info "进行快速测试..."
if python3 -c "from playwright.sync_api import sync_playwright; import pytz; import github; import notion_client; print('所有依赖导入成功')"; then
    log_info "依赖测试通过"
else
    log_error "依赖测试失败"
    exit 1
fi

log_step "11. 配置定时任务提示"
echo ""
log_info "部署完成！接下来的步骤："
echo "1. 编辑 .env 文件，填入正确的 API 令牌"
echo "2. 测试运行: ./run_server.sh"
echo "3. 配置定时任务:"
echo "   crontab -e"
echo "   添加行: 0 7 * * * $SCRIPT_DIR/run_server.sh"
echo ""
log_info "查看日志: tail -f logs/run.log"
log_info "部署脚本执行完成"
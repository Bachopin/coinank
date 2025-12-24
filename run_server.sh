#!/bin/bash
# CoinAnk 服务器部署运行脚本
# 适用于 Linux 服务器环境

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_info "切换到项目目录: $SCRIPT_DIR"

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    log_error "Python3 未安装，请先安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
log_info "Python 版本: $PYTHON_VERSION"

# 检查并创建虚拟环境
if [ ! -d ".venv" ]; then
    log_info "创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
log_info "激活虚拟环境..."
source .venv/bin/activate

# 升级 pip
log_info "升级 pip..."
pip install --upgrade pip

# 安装依赖
if [ -f "requirements.txt" ]; then
    log_info "安装 Python 依赖..."
    pip install -r requirements.txt
else
    log_error "requirements.txt 文件不存在"
    exit 1
fi

# 检查 Playwright 浏览器
log_info "检查 Playwright 浏览器..."
if ! python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright(); p.start(); p.chromium.launch(headless=True); p.stop()" 2>/dev/null; then
    log_warn "Playwright 浏览器未安装，正在安装..."
    playwright install chromium
    
    # 安装系统依赖（Ubuntu/Debian）
    if command -v apt-get &> /dev/null; then
        log_info "安装系统依赖..."
        playwright install-deps chromium
    fi
fi

# 检查环境变量文件
if [ ! -f ".env" ]; then
    log_warn ".env 文件不存在，请根据 .env.example 创建"
    if [ -f ".env.example" ]; then
        log_info "复制 .env.example 到 .env..."
        cp .env.example .env
        log_warn "请编辑 .env 文件并填入正确的配置"
    fi
fi

# 创建日志目录
mkdir -p logs

# 记录运行开始时间
echo "=== 开始运行 $(date '+%Y-%m-%d %H:%M:%S') ===" >> logs/run.log

# 运行脚本
log_info "开始执行抓取脚本..."
if [ -f "main_optimized.py" ]; then
    python3 main_optimized.py >> logs/run.log 2>&1
    EXIT_CODE=$?
else
    python3 main.py >> logs/run.log 2>&1
    EXIT_CODE=$?
fi

# 记录运行结束时间
echo "=== 运行结束 $(date '+%Y-%m-%d %H:%M:%S')，退出码: $EXIT_CODE ===" >> logs/run.log

if [ $EXIT_CODE -eq 0 ]; then
    log_info "脚本执行成功"
else
    log_error "脚本执行失败，退出码: $EXIT_CODE"
    log_info "查看日志: tail -f logs/run.log"
fi

exit $EXIT_CODE
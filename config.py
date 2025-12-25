#!/usr/bin/env python3
"""
CoinAnk 脚本配置文件
所有可配置的选项都集中在这里
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# 路径配置
# ============================================================

# 脚本所在目录
SCRIPT_DIR = Path(__file__).parent.absolute()

# 加载 .env 文件（必须在读取环境变量之前）
load_dotenv(SCRIPT_DIR / '.env')

# 日志目录
LOG_DIR = SCRIPT_DIR / 'logs'

# 锁文件（用于防重复执行）
LOCK_FILE = "daily_task.lock"

# ============================================================
# 抓取目标配置
# ============================================================

# 清算热力图 URL
HEATMAP_URL = "https://coinank.com/zh/chart/derivatives/liq-heat-map/btcusdt/1M"

# 聚合清算图 URL
AGGREGATE_URL = "https://coinank.com/zh/chart/derivatives/liq-map/binance/btcusdt/1w"

# ============================================================
# 浏览器配置
# ============================================================

# 浏览器视口大小
VIEWPORT = {'width': 1920, 'height': 1200}

# 页面渲染等待时间（毫秒）
WAIT_TIME_MS = 15000

# 页面加载超时时间（毫秒）
PAGE_TIMEOUT_MS = 90000

# 下载超时时间（毫秒）
DOWNLOAD_TIMEOUT_MS = 30000

# 浏览器启动参数
BROWSER_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-gpu',
    '--disable-web-security',
    '--disable-features=VizDisplayCompositor',
]

# 服务器环境额外参数
SERVER_BROWSER_ARGS = [
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding',
    '--single-process',
]

# User-Agent
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 相机按钮选择器
CAMERA_BUTTON_SELECTOR = ".anticon.anticon-camera"

# ============================================================
# 重试配置
# ============================================================

# 截图抓取最大重试次数
MAX_RETRIES = 3

# 重试基础等待时间（秒），实际等待 = BASE * (attempt + 1)
RETRY_WAIT_BASE_SECONDS = 5

# ============================================================
# 清理配置
# ============================================================

# GitHub 图片保留天数
GITHUB_IMAGE_RETENTION_DAYS = 30

# 本地日志保留天数
LOCAL_LOG_RETENTION_DAYS = 30

# 轮转日志保留天数
ROTATED_LOG_RETENTION_DAYS = 7

# 错误截图保留天数
ERROR_SCREENSHOT_RETENTION_DAYS = 7

# 日志文件最大大小（MB），超过则轮转
LOG_MAX_SIZE_MB = 10

# ============================================================
# 超时配置
# ============================================================

# 全局脚本超时时间（秒）- 防止脚本卡死
GLOBAL_TIMEOUT_SECONDS = 600  # 10分钟

# ============================================================
# 环境变量配置（从 .env 文件或系统环境变量读取）
# ============================================================

# GitHub 配置
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'Bachopin/coinank')

# Notion 配置
NOTION_TOKEN = os.getenv('NOTION_TOKEN', '')
NOTION_DB_ID = os.getenv('NOTION_DB_ID', '')

# 是否使用无头模式（默认 true）
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'

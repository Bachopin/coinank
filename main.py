#!/usr/bin/env python3
"""
CoinAnk 比特币清算热力图 + 聚合图抓取脚本（Mac 本地版 + 防重补跑机制）
抓取两个截图并上传到 GitHub，然后更新 Notion 页面。

功能特性：
- 自动抓取 CoinAnk 清算热力图和聚合清算图
- 上传到 GitHub 仓库并生成 raw 链接
- 同步图片链接到 Notion 数据库
- 防重复执行机制（每日只执行一次）
- 自动清理超过30天的 GitHub 旧图片
- 本地文件和日志自动清理
- 失败重试机制
"""

import logging
import os
import datetime
import sys
import platform
import time
import re
from pathlib import Path
from typing import Optional, Tuple, List

import pytz
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from github import Github, GithubException, Auth
from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError
from dotenv import load_dotenv

# 获取脚本所在目录，确保相对路径正确
SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)

# 防重补跑机制 - 锁文件
LOCK_FILE = "daily_task.lock"

# 加载本地 .env 文件
load_dotenv(SCRIPT_DIR / '.env')

# 创建日志目录
LOG_DIR = SCRIPT_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# 检测运行环境
IS_SERVER = platform.system() == 'Linux' or os.getenv('DISPLAY') is None

# 日志配置 - 服务器友好
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / 'runtime.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

logger.info(f"运行环境: {platform.system()}, 服务器模式: {IS_SERVER}")

# 配置常量（环境变量）
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'Bachopin/coinank')
NOTION_TOKEN = os.getenv('NOTION_TOKEN', '')
NOTION_DB_ID = os.getenv('NOTION_DB_ID', '')

# 验证必要的环境变量
missing_vars = []
if not GITHUB_TOKEN:
    missing_vars.append('GITHUB_TOKEN')
if not NOTION_TOKEN:
    missing_vars.append('NOTION_TOKEN')
if not NOTION_DB_ID:
    missing_vars.append('NOTION_DB_ID')

if missing_vars:
    logger.warning(f"缺少环境变量: {', '.join(missing_vars)}")
else:
    logger.info("所有必要的环境变量已配置")

# 截图 URL 与文件名模板
HEATMAP_URL = "https://coinank.com/zh/chart/derivatives/liq-heat-map/btcusdt/1M"
AGGREGATE_URL = "https://coinank.com/zh/chart/derivatives/liq-map/binance/btcusdt/1w"
VIEWPORT = {'width': 1920, 'height': 1200}
WAIT_TIME_MS = 15000  # 15秒

# GitHub 图片保留天数
GITHUB_IMAGE_RETENTION_DAYS = 30

# 浏览器配置 - 服务器优化
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
if IS_SERVER:
    BROWSER_ARGS.extend([
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--single-process',  # 服务器环境下减少进程数
    ])

# 相机按钮选择器
CAMERA_BUTTON_SELECTOR = ".anticon.anticon-camera"

def get_today_beijing() -> str:
    """返回北京时间的今日日期字符串 YYYY-MM-DD"""
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.datetime.now(tz)
    return now.strftime('%Y-%m-%d')

def check_if_done_today():
    """
    检查今日任务是否已完成
    如果已完成，直接退出脚本
    """
    today = get_today_beijing()
    lock_file_path = SCRIPT_DIR / LOCK_FILE
    
    try:
        if lock_file_path.exists():
            with open(lock_file_path, 'r', encoding='utf-8') as f:
                last_run_date = f.read().strip()
            
            if last_run_date == today:
                logger.info("✅ 今日任务已完成，无需重复执行")
                sys.exit(0)
            else:
                logger.info(f"🚀 今日尚未执行，开始运行任务... (上次执行: {last_run_date})")
        else:
            logger.info("🚀 今日尚未执行，开始运行任务... (首次运行)")
    except Exception as e:
        logger.warning(f"读取锁文件失败: {e}，继续执行任务")

def mark_as_done():
    """
    标记今日任务已完成
    将今天的日期写入锁文件
    """
    today = get_today_beijing()
    lock_file_path = SCRIPT_DIR / LOCK_FILE
    
    try:
        with open(lock_file_path, 'w', encoding='utf-8') as f:
            f.write(today)
        logger.info(f"✅ 任务完成标记已保存: {today}")
    except Exception as e:
        logger.error(f"保存任务完成标记失败: {e}")

def capture_screenshot(page_url: str, filename: str) -> bool:
    """
    使用 Playwright 访问 page_url，点击相机按钮下载截图，保存为 filename。
    返回成功与否。
    """
    logger.info(f"开始抓取截图: {page_url}")
    browser = None
    context = None
    page = None
    
    try:
        with sync_playwright() as p:
            # 服务器环境强制使用无头模式
            headless_mode = IS_SERVER or os.getenv('HEADLESS', 'true').lower() == 'true'
            
            browser = p.chromium.launch(
                headless=headless_mode,
                args=BROWSER_ARGS
            )
            
            context = browser.new_context(
                viewport=VIEWPORT,
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # 设置更长的超时时间
            page.set_default_timeout(90000)
            
            logger.info(f"访问页面: {page_url}")
            # 使用 domcontentloaded 而不是 networkidle，避免等待所有网络请求
            try:
                page.goto(page_url, timeout=90000, wait_until='domcontentloaded')
            except PlaywrightTimeout:
                logger.warning("页面加载超时，尝试继续执行...")
            
            # 等待页面基本加载完成
            try:
                page.wait_for_load_state('load', timeout=30000)
            except PlaywrightTimeout:
                logger.warning("等待 load 状态超时，继续执行...")
            
            logger.info("页面加载完成，等待图表渲染...")
            page.wait_for_timeout(WAIT_TIME_MS)

            # 定位下方图表容器（通过时间选择器文本"1d"）
            all_time_selectors = page.locator(".ant-select-selector")
            target_selector = None
            
            # 等待选择器出现
            try:
                all_time_selectors.first.wait_for(timeout=10000)
            except PlaywrightTimeout:
                logger.warning("等待时间选择器超时")
            
            selector_count = all_time_selectors.count()
            for i in range(selector_count):
                try:
                    txt = all_time_selectors.nth(i).text_content(timeout=5000)
                    if txt and txt.strip() == '1d':
                        target_selector = all_time_selectors.nth(i)
                        break
                except Exception as e:
                    logger.debug(f"检查时间选择器 {i} 时出错: {e}")
                    continue
                    
            if target_selector is None:
                logger.warning("未找到 '1d' 时间选择器，使用备用策略")
                if selector_count >= 2:
                    target_selector = all_time_selectors.nth(1)
                elif selector_count >= 1:
                    target_selector = all_time_selectors.first
                else:
                    raise Exception("未找到任何时间选择器，页面可能未正确加载")
                    
            chart_container = target_selector.locator("..").locator("..")
            logger.info("已定位下方图表容器")

            # 在容器内找到时间选择器并切换到 1w（如果是聚合图）或保持 1M（热图）
            # 根据 URL 判断需要切换的周期
            if '/liq-map/' in page_url and 'heat-map' not in page_url:
                logger.info("聚合图页面，切换到 1w 周期")
                try:
                    target_selector.click()
                    page.wait_for_timeout(1000)
                    dropdown_item = page.locator(".ant-select-dropdown .ant-select-item[title='1w']")
                    if dropdown_item.count() == 0:
                        dropdown_item = page.locator("text=1w").last
                    dropdown_item.click()
                    logger.info("已切换到 1w 周期")
                    page.wait_for_timeout(8000)
                except Exception as e:
                    logger.warning(f"切换时间周期失败: {e}")
            else:
                logger.info("热图页面，保持 1M 周期，无需切换")

            # 滚动使图表区域可见
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            page.wait_for_timeout(2000)

            # 点击相机按钮并监听下载
            with page.expect_download(timeout=30000) as download_info:
                camera_button = chart_container.locator(".anticon.anticon-camera")
                if camera_button.count() > 0:
                    camera_button.click()
                    logger.info("已点击相机按钮")
                else:
                    # 备用选择器
                    alt_selectors = [
                        '[class*="camera"]',
                        '[class*="download"]',
                        '[class*="export"]',
                        'button:has(svg.camera)',
                    ]
                    clicked = False
                    for sel in alt_selectors:
                        element = chart_container.locator(sel)
                        if element.count() > 0:
                            element.click()
                            logger.info(f"已点击备用选择器: {sel}")
                            clicked = True
                            break
                    if not clicked:
                        if page.is_visible(CAMERA_BUTTON_SELECTOR):
                            page.click(CAMERA_BUTTON_SELECTOR)
                            logger.info("已点击全局相机按钮")
                        else:
                            raise Exception("未找到可点击的相机按钮")

            download = download_info.value
            logger.info(f"下载开始: {download.suggested_filename}")
            
            # 确保文件保存在正确的目录
            file_path = SCRIPT_DIR / filename
            download.save_as(str(file_path))
            
            # 验证文件是否成功保存
            if not file_path.exists():
                raise Exception(f"文件保存失败: {file_path}")
            
            file_size = file_path.stat().st_size
            if file_size < 1000:  # 小于1KB可能是空文件或错误
                raise Exception(f"文件大小异常: {file_size} bytes")
                
            logger.info(f"截图已保存为: {file_path} ({file_size / 1024:.1f} KB)")
            
            return True
            
    except PlaywrightTimeout as e:
        logger.error(f"Playwright 超时: {e}")
        _save_error_screenshot(page, filename)
        return False
    except Exception as e:
        logger.error(f"抓取截图失败: {e}")
        _save_error_screenshot(page, filename)
        return False
    finally:
        try:
            if context:
                context.close()
            if browser:
                browser.close()
        except Exception:
            pass


def _save_error_screenshot(page: Optional[Page], filename: str):
    """保存错误时的页面截图用于调试"""
    if not page:
        return
    try:
        error_file = SCRIPT_DIR / f"error_{os.path.basename(filename)}"
        page.screenshot(path=str(error_file))
        logger.info(f"错误快照已保存: {error_file}")
    except Exception as e:
        logger.debug(f"保存错误快照失败: {e}")

def capture_screenshot_with_retry(page_url: str, filename: str, max_retries: int = 3) -> bool:
    """
    带重试机制的截图抓取
    
    Args:
        page_url: 要抓取的页面 URL
        filename: 保存的文件名
        max_retries: 最大重试次数
        
    Returns:
        是否成功
    """
    last_error = None
    for attempt in range(max_retries):
        if attempt > 0:
            wait_time = 5 * (attempt + 1)  # 递增等待时间：10秒、15秒
            logger.info(f"第 {attempt + 1} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
        
        try:
            if capture_screenshot(page_url, filename):
                return True
        except Exception as e:
            last_error = e
            logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
    
    logger.error(f"截图抓取失败，已重试 {max_retries} 次。最后错误: {last_error}")
    return False


def scrape_heatmap() -> Optional[str]:
    """
    抓取清算热力图 (1M) 并保存为本地文件，返回文件路径。
    """
    today = get_today_beijing()
    filename = f"{today}_BTC_清算热力图_1M.png"
    success = capture_screenshot_with_retry(HEATMAP_URL, filename)
    if success:
        return filename
    else:
        return None

def scrape_liquidation_map() -> Optional[str]:
    """
    抓取 CoinAnk 1W 周期清算图并保存为本地文件，返回文件路径。
    """
    today = get_today_beijing()
    filename = f"{today}_BTC_全网聚合清算_1W.png"
    success = capture_screenshot_with_retry(AGGREGATE_URL, filename)
    if success:
        return filename
    else:
        return None

def upload_to_github(file_path: str, repo_name: str, token: str) -> Optional[str]:
    """
    将文件上传到 GitHub 仓库的 images/YYYY-MM/ 目录下，返回 raw 链接。
    """
    if not token:
        logger.error("GitHub Token 未提供，跳过上传")
        return None
    try:
        # 使用新的认证方式，避免 DeprecationWarning
        auth = Auth.Token(token)
        gh = Github(auth=auth)
        repo = gh.get_repo(repo_name)
        
        # 确保文件存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
            
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # 构造仓库中的路径，按年月组织
        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.datetime.now(tz)
        year_month = now.strftime('%Y-%m')
        filename = os.path.basename(file_path)
        remote_path = f"images/{year_month}/{filename}"
        
        # 检查文件是否存在，若存在则更新
        try:
            existing = repo.get_contents(remote_path)
            repo.update_file(remote_path, f"Update {now.date()}", content, existing.sha)
            logger.info(f"已更新 GitHub 文件: {remote_path}")
        except GithubException as e:
            if e.status == 404:
                repo.create_file(remote_path, f"Add {now.date()}", content)
                logger.info(f"已创建 GitHub 文件: {remote_path}")
            else:
                raise
            
        # 生成 raw 链接
        raw_url = f"https://raw.githubusercontent.com/{repo_name}/main/{remote_path}"
        logger.info(f"Raw URL: {raw_url}")
        return raw_url
        
    except GithubException as e:
        logger.error(f"GitHub 上传失败: {e}")
        return None
    except Exception as e:
        logger.error(f"上传过程中出现未知错误: {e}")
        return None


def cleanup_old_github_images(repo_name: str, token: str, retention_days: int = 30) -> int:
    """
    清理 GitHub 仓库中超过指定天数的旧图片。
    
    Args:
        repo_name: GitHub 仓库名称
        token: GitHub Token
        retention_days: 保留天数，默认30天
        
    Returns:
        删除的文件数量
    """
    if not token:
        logger.warning("GitHub Token 未提供，跳过清理")
        return 0
        
    try:
        auth = Auth.Token(token)
        gh = Github(auth=auth)
        repo = gh.get_repo(repo_name)
        
        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.datetime.now(tz)
        cutoff_date = now - datetime.timedelta(days=retention_days)
        
        deleted_count = 0
        
        # 获取 images 目录下的所有子目录（按年月组织）
        try:
            contents = repo.get_contents("images")
        except GithubException as e:
            if e.status == 404:
                logger.info("images 目录不存在，无需清理")
                return 0
            raise
            
        for item in contents:
            if item.type != "dir":
                continue
                
            # 解析目录名（格式：YYYY-MM）
            dir_name = item.name
            try:
                dir_date = datetime.datetime.strptime(dir_name, '%Y-%m')
                dir_date = tz.localize(dir_date)
            except ValueError:
                logger.debug(f"跳过非日期格式目录: {dir_name}")
                continue
            
            # 如果整个月份都超过保留期，删除整个目录
            # 计算该月最后一天
            if dir_date.month == 12:
                next_month = dir_date.replace(year=dir_date.year + 1, month=1, day=1)
            else:
                next_month = dir_date.replace(month=dir_date.month + 1, day=1)
            last_day_of_month = next_month - datetime.timedelta(days=1)
            
            if last_day_of_month < cutoff_date:
                # 整个月份都过期了，删除目录下所有文件
                try:
                    dir_contents = repo.get_contents(f"images/{dir_name}")
                    for file_item in dir_contents:
                        if file_item.type == "file":
                            repo.delete_file(
                                file_item.path,
                                f"Auto cleanup: remove old image {file_item.name}",
                                file_item.sha
                            )
                            deleted_count += 1
                            logger.info(f"已删除过期图片: {file_item.path}")
                except GithubException as e:
                    logger.warning(f"删除目录 {dir_name} 中的文件失败: {e}")
            else:
                # 检查目录内的单个文件
                try:
                    dir_contents = repo.get_contents(f"images/{dir_name}")
                    for file_item in dir_contents:
                        if file_item.type != "file":
                            continue
                        
                        # 从文件名解析日期（格式：YYYY-MM-DD_...）
                        filename = file_item.name
                        date_match = re.match(r'^(\d{4}-\d{2}-\d{2})_', filename)
                        if date_match:
                            try:
                                file_date = datetime.datetime.strptime(date_match.group(1), '%Y-%m-%d')
                                file_date = tz.localize(file_date)
                                
                                if file_date < cutoff_date:
                                    repo.delete_file(
                                        file_item.path,
                                        f"Auto cleanup: remove old image {filename}",
                                        file_item.sha
                                    )
                                    deleted_count += 1
                                    logger.info(f"已删除过期图片: {file_item.path}")
                            except ValueError:
                                pass
                except GithubException as e:
                    logger.warning(f"处理目录 {dir_name} 失败: {e}")
        
        if deleted_count > 0:
            logger.info(f"GitHub 图片清理完成：删除了 {deleted_count} 个过期文件")
        else:
            logger.info("GitHub 图片清理完成：没有需要删除的过期文件")
            
        return deleted_count
        
    except GithubException as e:
        logger.error(f"GitHub 清理失败: {e}")
        return 0
    except Exception as e:
        logger.error(f"GitHub 清理过程中出现未知错误: {e}")
        return 0

def get_today_notion_page(notion_token: str, db_id: str) -> Optional[str]:
    """
    查询 Notion 数据库中 isToday 公式属性为 True（即今天）的页面，返回页面 ID。
    """
    if not notion_token or not db_id:
        logger.error("Notion Token 或 Database ID 未提供")
        return None
        
    try:
        notion = NotionClient(auth=notion_token)
        logger.info("正在查询 isToday 为 True 的页面...")
        response = notion.databases.query(
            database_id=db_id,
            filter={
                "property": "isToday",
                "formula": {
                    "checkbox": {
                        "equals": True
                    }
                }
            }
        )
        results = response.get('results', [])
        if len(results) == 0:
            logger.warning("未找到 isToday 为 True 的 Notion 页面")
            return None
        page = results[0]
        page_id = page['id']
        logger.info(f"找到 Notion 页面: {page_id}")
        return page_id
    except APIResponseError as e:
        logger.error(f"Notion 查询失败: {e}")
        return None
    except Exception as e:
        logger.error(f"Notion 查询过程中出现未知错误: {e}")
        return None

def update_notion_page(notion_token: str, page_id: str, heatmap_url: str, aggregate_url: str):
    """
    更新 Notion 页面的"数据图"和"清算地图"属性。
    """
    try:
        notion = NotionClient(auth=notion_token)
        properties = {}
        if heatmap_url:
            properties["数据图"] = {
                "files": [
                    {
                        "type": "external",
                        "name": "Heatmap.png",
                        "external": {"url": heatmap_url}
                    }
                ]
            }
        if aggregate_url:
            properties["清算地图"] = {
                "files": [
                    {
                        "type": "external",
                        "name": "Aggregate.png",
                        "external": {"url": aggregate_url}
                    }
                ]
            }
        if not properties:
            logger.warning("没有可更新的属性，跳过 Notion 更新")
            return
        notion.pages.update(page_id=page_id, properties=properties)
        logger.info(f"Notion 页面更新成功，属性: {list(properties.keys())}")
    except APIResponseError as e:
        logger.error(f"Notion 更新失败: {e}")
    except Exception as e:
        logger.error(f"Notion 更新过程中出现未知错误: {e}")

def sync_to_notion(heatmap_url: str, liq_map_url: str) -> bool:
    """
    同步两个图片 URL 到 Notion 数据库的今日页面。
    使用环境变量 NOTION_TOKEN 和 NOTION_DB_ID。
    返回成功与否。
    """
    if not NOTION_TOKEN or not NOTION_DB_ID:
        logger.warning("未提供 Notion Token 或 Database ID，跳过 Notion 同步")
        return False
    page_id = get_today_notion_page(NOTION_TOKEN, NOTION_DB_ID)
    if not page_id:
        logger.warning("未找到今天的 Notion 页面，跳过同步")
        return False
    try:
        update_notion_page(NOTION_TOKEN, page_id, heatmap_url, liq_map_url)
        logger.info("Notion 同步成功")
        return True
    except Exception as e:
        logger.error(f"Notion 同步失败: {e}")
        return False

def cleanup_local_files(*file_paths):
    """清理本地临时文件"""
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"已删除本地文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除本地文件失败 {file_path}: {e}")

def cleanup_old_files():
    """
    定期清理旧文件：日志、错误截图、临时文件等
    保留策略：
    - 日志文件：保留30天
    - 错误截图：保留7天  
    - 临时文件：保留1天
    """
    logger.info("开始清理旧文件...")
    
    import time
    current_time = time.time()
    
    # 清理规则
    cleanup_rules = [
        # (文件模式, 保留天数, 描述)
        ("logs/*.log", 30, "日志文件"),
        ("*.log", 30, "根目录日志文件"),
        ("logs/runtime.log.*", 7, "轮转的日志文件"),  # 轮转后的日志文件只保留7天
        ("error_*.png", 7, "错误截图"),
        ("debug*.png", 7, "调试截图"),
        ("explore*.png", 7, "探索截图"),
        ("*.tmp", 1, "临时文件"),
        ("*.temp", 1, "临时文件"),
        ("*_BTC_*.png", 1, "当日截图文件"),  # 截图文件执行完就删除，这里是保险
        ("container_text.txt", 7, "容器文本文件"),
        ("page_text.txt", 7, "页面文本文件"),
    ]
    
    total_cleaned = 0
    total_size = 0
    
    for pattern, keep_days, description in cleanup_rules:
        try:
            import glob
            files = glob.glob(pattern)
            
            for file_path in files:
                try:
                    # 检查文件年龄
                    file_age_days = (current_time - os.path.getmtime(file_path)) / (24 * 3600)
                    
                    if file_age_days > keep_days:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        total_cleaned += 1
                        total_size += file_size
                        logger.info(f"已清理 {description}: {file_path} (已存在 {file_age_days:.1f} 天)")
                        
                except Exception as e:
                    logger.debug(f"清理文件失败 {file_path}: {e}")
                    
        except Exception as e:
            logger.debug(f"处理模式 {pattern} 时出错: {e}")
    
    if total_cleaned > 0:
        size_mb = total_size / (1024 * 1024)
        logger.info(f"清理完成：删除了 {total_cleaned} 个文件，释放 {size_mb:.2f} MB 空间")
    else:
        logger.info("清理完成：没有需要清理的旧文件")

def rotate_log_if_needed():
    """
    日志轮转：如果日志文件过大，进行轮转
    """
    log_file = LOG_DIR / 'runtime.log'
    max_size_mb = 10  # 最大10MB
    
    try:
        if log_file.exists():
            size_mb = log_file.stat().st_size / (1024 * 1024)
            
            if size_mb > max_size_mb:
                # 轮转日志
                backup_file = LOG_DIR / f'runtime.log.{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
                log_file.rename(backup_file)
                logger.info(f"日志轮转：{log_file} -> {backup_file} ({size_mb:.2f}MB)")
                
                # 重新配置日志处理器
                for handler in logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                        logger.removeHandler(handler)
                
                # 添加新的文件处理器
                new_handler = logging.FileHandler(log_file, encoding='utf-8')
                new_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                logger.addHandler(new_handler)
                
    except Exception as e:
        logger.debug(f"日志轮转失败: {e}")

def main():
    """主函数"""
    # 防重补跑机制 - 检查今日是否已执行
    check_if_done_today()
    
    logger.info("=== CoinAnk 自动抓取脚本开始 ===")
    
    # 定期清理本地文件（每次运行时检查）
    try:
        cleanup_old_files()
        rotate_log_if_needed()
    except Exception as e:
        logger.warning(f"本地清理过程中出现错误: {e}")
    
    # 检查 Playwright 浏览器是否已安装
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        logger.info("Playwright 浏览器检查通过")
    except Exception as e:
        logger.error(f"Playwright 浏览器未正确安装: {e}")
        logger.error("请运行: playwright install chromium")
        return

    # 1. 抓取两个截图
    heatmap_file = scrape_heatmap()
    liq_map_file = scrape_liquidation_map()

    if not heatmap_file and not liq_map_file:
        logger.error("两个截图均抓取失败，脚本终止")
        return

    # 2. 上传到 GitHub
    heatmap_url = None
    liq_map_url = None
    if GITHUB_TOKEN:
        if heatmap_file:
            heatmap_url = upload_to_github(heatmap_file, GITHUB_REPO, GITHUB_TOKEN)
        if liq_map_file:
            liq_map_url = upload_to_github(liq_map_file, GITHUB_REPO, GITHUB_TOKEN)
    else:
        logger.warning("未提供 GitHub Token，跳过上传步骤")

    # 3. 同步到 Notion
    sync_success = False
    if heatmap_url or liq_map_url:
        sync_success = sync_to_notion(heatmap_url, liq_map_url)
    else:
        logger.warning("没有可用的图片 URL，跳过 Notion 同步")

    # 4. 清理本地临时文件
    cleanup_local_files(heatmap_file, liq_map_file)

    # 5. 清理 GitHub 上的旧图片（每次成功执行后清理）
    if sync_success and GITHUB_TOKEN:
        try:
            cleanup_old_github_images(GITHUB_REPO, GITHUB_TOKEN, GITHUB_IMAGE_RETENTION_DAYS)
        except Exception as e:
            logger.warning(f"GitHub 图片清理失败: {e}")

    # 6. 防重补跑机制 - 标记任务完成（仅在 Notion 同步成功时）
    if sync_success:
        mark_as_done()
        logger.info("🎉 今日任务执行成功并已标记完成")
    else:
        logger.warning("⚠️ 任务未完全成功，不标记为完成（下次运行可重试）")

    logger.info("=== 脚本执行完成 ===")

if __name__ == "__main__":
    main()
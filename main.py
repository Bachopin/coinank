#!/usr/bin/env python3
"""
CoinAnk 比特币清算热力图 + 聚合图自动抓取脚本 v1.0

功能特性：
- 自动抓取 CoinAnk 清算热力图和聚合清算图
- 上传到 GitHub 仓库并生成 raw 链接
- 同步图片链接到 Notion 数据库
- 防重复执行机制（每日只执行一次）
- 自动清理超过30天的 GitHub 旧图片
- 本地文件和日志自动清理
- 失败重试机制
- 全局超时保护
"""

__version__ = "1.0.0"

import logging
import os
import sys
import platform
import time
import re
import glob
import signal
import datetime
from pathlib import Path
from typing import Optional

import pytz
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from github import Github, GithubException, Auth
from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError
from dotenv import load_dotenv

# 加载配置
from config import (
    SCRIPT_DIR, LOG_DIR, LOCK_FILE,
    HEATMAP_URL, AGGREGATE_URL,
    VIEWPORT, WAIT_TIME_MS, PAGE_TIMEOUT_MS, DOWNLOAD_TIMEOUT_MS,
    BROWSER_ARGS, SERVER_BROWSER_ARGS, USER_AGENT, CAMERA_BUTTON_SELECTOR,
    MAX_RETRIES, RETRY_WAIT_BASE_SECONDS,
    ENABLE_GITHUB_CLEANUP, GITHUB_IMAGE_RETENTION_DAYS,
    LOCAL_LOG_RETENTION_DAYS, ROTATED_LOG_RETENTION_DAYS,
    ERROR_SCREENSHOT_RETENTION_DAYS, LOG_MAX_SIZE_MB,
    GLOBAL_TIMEOUT_SECONDS,
    GITHUB_TOKEN, GITHUB_REPO, NOTION_TOKEN, NOTION_DB_ID, HEADLESS,
)

# 切换到脚本目录
os.chdir(SCRIPT_DIR)

# 创建日志目录
LOG_DIR.mkdir(exist_ok=True)

# 检测运行环境
IS_SERVER = platform.system() == 'Linux' or os.getenv('DISPLAY') is None

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / 'runtime.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

logger.info(f"CoinAnk 脚本 v{__version__}")
logger.info(f"运行环境: {platform.system()}, 服务器模式: {IS_SERVER}")

# 验证环境变量
_missing_vars = []
if not GITHUB_TOKEN:
    _missing_vars.append('GITHUB_TOKEN')
if not NOTION_TOKEN:
    _missing_vars.append('NOTION_TOKEN')
if not NOTION_DB_ID:
    _missing_vars.append('NOTION_DB_ID')

if _missing_vars:
    logger.warning(f"缺少环境变量: {', '.join(_missing_vars)}")
else:
    logger.info("所有必要的环境变量已配置")


def get_today_beijing() -> str:
    """返回北京时间的今日日期字符串 YYYY-MM-DD"""
    tz = pytz.timezone('Asia/Shanghai')
    return datetime.datetime.now(tz).strftime('%Y-%m-%d')


def check_if_done_today():
    """检查今日任务是否已完成，如果已完成则退出"""
    today = get_today_beijing()
    lock_file_path = SCRIPT_DIR / LOCK_FILE
    
    try:
        if lock_file_path.exists():
            last_run_date = lock_file_path.read_text(encoding='utf-8').strip()
            if last_run_date == today:
                logger.info("✅ 今日任务已完成，无需重复执行")
                sys.exit(0)
            logger.info(f"🚀 今日尚未执行，开始运行任务... (上次执行: {last_run_date})")
        else:
            logger.info("🚀 今日尚未执行，开始运行任务... (首次运行)")
    except Exception as e:
        logger.warning(f"读取锁文件失败: {e}，继续执行任务")


def mark_as_done():
    """标记今日任务已完成"""
    today = get_today_beijing()
    try:
        (SCRIPT_DIR / LOCK_FILE).write_text(today, encoding='utf-8')
        logger.info(f"✅ 任务完成标记已保存: {today}")
    except Exception as e:
        logger.error(f"保存任务完成标记失败: {e}")


def _get_browser_args() -> list:
    """获取浏览器启动参数"""
    args = BROWSER_ARGS.copy()
    if IS_SERVER:
        args.extend(SERVER_BROWSER_ARGS)
    return args


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


def capture_screenshot(page_url: str, filename: str) -> bool:
    """使用 Playwright 访问页面并抓取截图"""
    logger.info(f"开始抓取截图: {page_url}")
    browser = None
    context = None
    page = None
    
    try:
        with sync_playwright() as p:
            headless_mode = IS_SERVER or HEADLESS
            browser = p.chromium.launch(headless=headless_mode, args=_get_browser_args())
            context = browser.new_context(viewport=VIEWPORT, user_agent=USER_AGENT)
            page = context.new_page()
            page.set_default_timeout(PAGE_TIMEOUT_MS)
            
            logger.info(f"访问页面: {page_url}")
            try:
                page.goto(page_url, timeout=PAGE_TIMEOUT_MS, wait_until='domcontentloaded')
            except PlaywrightTimeout:
                logger.warning("页面加载超时，尝试继续执行...")
            
            try:
                page.wait_for_load_state('load', timeout=30000)
            except PlaywrightTimeout:
                logger.warning("等待 load 状态超时，继续执行...")
            
            logger.info("页面加载完成，等待图表渲染...")
            page.wait_for_timeout(WAIT_TIME_MS)

            # 定位图表容器
            all_time_selectors = page.locator(".ant-select-selector")
            target_selector = None
            
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
                except Exception:
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

            # 切换时间周期（聚合图需要切换到 1w）
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

            # 滚动页面
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            page.wait_for_timeout(2000)

            # 点击相机按钮下载截图
            with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as download_info:
                camera_button = chart_container.locator(CAMERA_BUTTON_SELECTOR)
                if camera_button.count() > 0:
                    camera_button.click()
                    logger.info("已点击相机按钮")
                else:
                    alt_selectors = ['[class*="camera"]', '[class*="download"]', '[class*="export"]']
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
            
            file_path = SCRIPT_DIR / filename
            download.save_as(str(file_path))
            
            # 验证文件
            if not file_path.exists():
                raise Exception(f"文件保存失败: {file_path}")
            file_size = file_path.stat().st_size
            if file_size < 1000:
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


def capture_screenshot_with_retry(page_url: str, filename: str) -> bool:
    """带重试机制的截图抓取"""
    last_error = None
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            wait_time = RETRY_WAIT_BASE_SECONDS * (attempt + 1)
            logger.info(f"第 {attempt + 1} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
        
        try:
            if capture_screenshot(page_url, filename):
                return True
        except Exception as e:
            last_error = e
            logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
    
    logger.error(f"截图抓取失败，已重试 {MAX_RETRIES} 次。最后错误: {last_error}")
    return False


def scrape_heatmap() -> Optional[str]:
    """抓取清算热力图"""
    filename = f"{get_today_beijing()}_BTC_清算热力图_1M.png"
    return filename if capture_screenshot_with_retry(HEATMAP_URL, filename) else None


def scrape_liquidation_map() -> Optional[str]:
    """抓取聚合清算图"""
    filename = f"{get_today_beijing()}_BTC_全网聚合清算_1W.png"
    return filename if capture_screenshot_with_retry(AGGREGATE_URL, filename) else None


def upload_to_github(file_path: str) -> Optional[str]:
    """上传文件到 GitHub，返回 raw 链接"""
    if not GITHUB_TOKEN:
        logger.error("GitHub Token 未提供，跳过上传")
        return None
    
    try:
        auth = Auth.Token(GITHUB_TOKEN)
        gh = Github(auth=auth)
        repo = gh.get_repo(GITHUB_REPO)
        
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
            
        with open(file_path, 'rb') as f:
            content = f.read()
            
        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.datetime.now(tz)
        year_month = now.strftime('%Y-%m')
        filename = os.path.basename(file_path)
        remote_path = f"images/{year_month}/{filename}"
        
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
            
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{remote_path}"
        logger.info(f"Raw URL: {raw_url}")
        return raw_url
        
    except GithubException as e:
        logger.error(f"GitHub 上传失败: {e}")
        return None
    except Exception as e:
        logger.error(f"上传过程中出现未知错误: {e}")
        return None


def cleanup_old_github_images() -> int:
    """清理 GitHub 仓库中超过保留天数的旧图片"""
    if not GITHUB_TOKEN:
        logger.warning("GitHub Token 未提供，跳过清理")
        return 0
        
    try:
        auth = Auth.Token(GITHUB_TOKEN)
        gh = Github(auth=auth)
        repo = gh.get_repo(GITHUB_REPO)
        
        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.datetime.now(tz)
        cutoff_date = now - datetime.timedelta(days=GITHUB_IMAGE_RETENTION_DAYS)
        
        deleted_count = 0
        
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
                
            dir_name = item.name
            try:
                dir_date = datetime.datetime.strptime(dir_name, '%Y-%m')
                dir_date = tz.localize(dir_date)
            except ValueError:
                continue
            
            # 计算该月最后一天
            if dir_date.month == 12:
                next_month = dir_date.replace(year=dir_date.year + 1, month=1, day=1)
            else:
                next_month = dir_date.replace(month=dir_date.month + 1, day=1)
            last_day_of_month = next_month - datetime.timedelta(days=1)
            
            if last_day_of_month < cutoff_date:
                # 整个月份都过期，删除所有文件
                try:
                    dir_contents = repo.get_contents(f"images/{dir_name}")
                    for file_item in dir_contents:
                        if file_item.type == "file":
                            repo.delete_file(file_item.path, f"Auto cleanup: {file_item.name}", file_item.sha)
                            deleted_count += 1
                            logger.info(f"已删除过期图片: {file_item.path}")
                except GithubException as e:
                    logger.warning(f"删除目录 {dir_name} 中的文件失败: {e}")
            else:
                # 检查单个文件
                try:
                    dir_contents = repo.get_contents(f"images/{dir_name}")
                    for file_item in dir_contents:
                        if file_item.type != "file":
                            continue
                        date_match = re.match(r'^(\d{4}-\d{2}-\d{2})_', file_item.name)
                        if date_match:
                            try:
                                file_date = tz.localize(datetime.datetime.strptime(date_match.group(1), '%Y-%m-%d'))
                                if file_date < cutoff_date:
                                    repo.delete_file(file_item.path, f"Auto cleanup: {file_item.name}", file_item.sha)
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
        
    except Exception as e:
        logger.error(f"GitHub 清理失败: {e}")
        return 0


def get_today_notion_page() -> Optional[str]:
    """查询 Notion 数据库中今天的页面"""
    if not NOTION_TOKEN or not NOTION_DB_ID:
        logger.error("Notion Token 或 Database ID 未提供")
        return None
        
    try:
        notion = NotionClient(auth=NOTION_TOKEN)
        logger.info("正在查询 isToday 为 True 的页面...")
        response = notion.databases.query(
            database_id=NOTION_DB_ID,
            filter={"property": "isToday", "formula": {"checkbox": {"equals": True}}}
        )
        results = response.get('results', [])
        if not results:
            logger.warning("未找到 isToday 为 True 的 Notion 页面")
            return None
        page_id = results[0]['id']
        logger.info(f"找到 Notion 页面: {page_id}")
        return page_id
    except APIResponseError as e:
        logger.error(f"Notion 查询失败: {e}")
        return None
    except Exception as e:
        logger.error(f"Notion 查询过程中出现未知错误: {e}")
        return None


def update_notion_page(page_id: str, heatmap_url: str, aggregate_url: str):
    """更新 Notion 页面的图片属性"""
    try:
        notion = NotionClient(auth=NOTION_TOKEN)
        properties = {}
        if heatmap_url:
            properties["数据图"] = {"files": [{"type": "external", "name": "Heatmap.png", "external": {"url": heatmap_url}}]}
        if aggregate_url:
            properties["清算地图"] = {"files": [{"type": "external", "name": "Aggregate.png", "external": {"url": aggregate_url}}]}
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
    """同步图片 URL 到 Notion"""
    if not NOTION_TOKEN or not NOTION_DB_ID:
        logger.warning("未提供 Notion Token 或 Database ID，跳过 Notion 同步")
        return False
    page_id = get_today_notion_page()
    if not page_id:
        logger.warning("未找到今天的 Notion 页面，跳过同步")
        return False
    try:
        update_notion_page(page_id, heatmap_url, liq_map_url)
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


def cleanup_old_local_files():
    """清理本地旧文件"""
    logger.info("开始清理本地旧文件...")
    current_time = time.time()
    
    cleanup_rules = [
        ("logs/*.log", LOCAL_LOG_RETENTION_DAYS, "日志文件"),
        ("*.log", LOCAL_LOG_RETENTION_DAYS, "根目录日志文件"),
        ("logs/runtime.log.*", ROTATED_LOG_RETENTION_DAYS, "轮转日志文件"),
        ("error_*.png", ERROR_SCREENSHOT_RETENTION_DAYS, "错误截图"),
        ("debug*.png", ERROR_SCREENSHOT_RETENTION_DAYS, "调试截图"),
        ("*_BTC_*.png", 1, "当日截图文件"),
    ]
    
    total_cleaned = 0
    total_size = 0
    
    for pattern, keep_days, description in cleanup_rules:
        try:
            for file_path in glob.glob(pattern):
                try:
                    file_age_days = (current_time - os.path.getmtime(file_path)) / (24 * 3600)
                    if file_age_days > keep_days:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        total_cleaned += 1
                        total_size += file_size
                        logger.info(f"已清理 {description}: {file_path}")
                except Exception as e:
                    logger.debug(f"清理文件失败 {file_path}: {e}")
        except Exception as e:
            logger.debug(f"处理模式 {pattern} 时出错: {e}")
    
    if total_cleaned > 0:
        logger.info(f"清理完成：删除了 {total_cleaned} 个文件，释放 {total_size / 1024 / 1024:.2f} MB")
    else:
        logger.info("清理完成：没有需要清理的旧文件")


def rotate_log_if_needed():
    """日志轮转"""
    log_file = LOG_DIR / 'runtime.log'
    try:
        if log_file.exists():
            size_mb = log_file.stat().st_size / (1024 * 1024)
            if size_mb > LOG_MAX_SIZE_MB:
                backup_file = LOG_DIR / f'runtime.log.{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
                log_file.rename(backup_file)
                logger.info(f"日志轮转：{log_file} -> {backup_file} ({size_mb:.2f}MB)")
                
                for handler in logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                        logger.removeHandler(handler)
                
                new_handler = logging.FileHandler(log_file, encoding='utf-8')
                new_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                logger.addHandler(new_handler)
    except Exception as e:
        logger.debug(f"日志轮转失败: {e}")


def main():
    """主函数"""
    # 设置全局超时保护
    if platform.system() != 'Windows':
        def timeout_handler(signum, frame):
            logger.error(f"⚠️ 脚本执行超时（{GLOBAL_TIMEOUT_SECONDS}秒），强制退出")
            sys.exit(1)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(GLOBAL_TIMEOUT_SECONDS)
    
    try:
        _run_main_task()
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)


def _run_main_task():
    """实际的主任务逻辑"""
    check_if_done_today()
    
    logger.info("=== CoinAnk 自动抓取脚本开始 ===")
    
    # 清理本地旧文件
    try:
        cleanup_old_local_files()
        rotate_log_if_needed()
    except Exception as e:
        logger.warning(f"本地清理过程中出现错误: {e}")
    
    # 检查 Playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        logger.info("Playwright 浏览器检查通过")
    except Exception as e:
        logger.error(f"Playwright 浏览器未正确安装: {e}")
        logger.error("请运行: playwright install chromium")
        return

    # 1. 抓取截图
    heatmap_file = scrape_heatmap()
    liq_map_file = scrape_liquidation_map()

    if not heatmap_file and not liq_map_file:
        logger.error("两个截图均抓取失败，脚本终止")
        return

    # 2. 上传到 GitHub
    heatmap_url = upload_to_github(heatmap_file) if heatmap_file else None
    liq_map_url = upload_to_github(liq_map_file) if liq_map_file else None

    # 3. 同步到 Notion
    sync_success = False
    if heatmap_url or liq_map_url:
        sync_success = sync_to_notion(heatmap_url, liq_map_url)
    else:
        logger.warning("没有可用的图片 URL，跳过 Notion 同步")

    # 4. 清理本地临时文件
    cleanup_local_files(heatmap_file, liq_map_file)

    # 5. 清理 GitHub 旧图片（可在 config.py 中开关）
    if sync_success and GITHUB_TOKEN and ENABLE_GITHUB_CLEANUP:
        try:
            cleanup_old_github_images()
        except Exception as e:
            logger.warning(f"GitHub 图片清理失败: {e}")

    # 6. 标记任务完成
    if sync_success:
        mark_as_done()
        logger.info("🎉 今日任务执行成功并已标记完成")
    else:
        logger.warning("⚠️ 任务未完全成功，不标记为完成（下次运行可重试）")

    logger.info("=== 脚本执行完成 ===")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
CoinAnk 比特币清算热力图 + 聚合图抓取脚本（最终版）
抓取两个截图并上传到 GitHub，然后更新 Notion 页面。
"""

import logging
import os
import datetime
import sys
from typing import Optional, Tuple

import pytz
from playwright.sync_api import sync_playwright, Browser, Page
from github import Github, GithubException
from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError
from dotenv import load_dotenv

# 加载本地 .env 文件
load_dotenv()

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('runtime.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 配置常量（硬编码或环境变量）
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')  # 请设置环境变量
GITHUB_REPO = os.getenv('GITHUB_REPO', 'Bachopin/coinank')
NOTION_TOKEN = os.getenv('NOTION_TOKEN', '')
NOTION_DB_ID = os.getenv('NOTION_DB_ID', '')
logger.info(f"环境变量加载情况: GITHUB_TOKEN={'***' if GITHUB_TOKEN else '空'}, NOTION_TOKEN={'***' if NOTION_TOKEN else '空'}")

# 截图 URL 与文件名模板
HEATMAP_URL = "https://coinank.com/zh/chart/derivatives/liq-heat-map/btcusdt/1M"
AGGREGATE_URL = "https://coinank.com/zh/chart/derivatives/liq-map/binance/btcusdt/1w"
VIEWPORT = {'width': 1920, 'height': 1200}
WAIT_TIME_MS = 15000  # 15秒

# 相机按钮选择器
CAMERA_BUTTON_SELECTOR = ".anticon.anticon-camera"

def get_today_beijing() -> str:
    """返回北京时间的今日日期字符串 YYYY-MM-DD"""
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.datetime.now(tz)
    return now.strftime('%Y-%m-%d')

def capture_screenshot(page_url: str, filename: str) -> bool:
    """
    使用 Playwright 访问 page_url，点击相机按钮下载截图，保存为 filename。
    返回成功与否。
    """
    logger.info(f"开始抓取截图: {page_url}")
    try:
        with sync_playwright() as p:
            browser: Browser = p.chromium.launch(
                headless=True,  # 可视模式便于调试，cron运行时改为 True
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            page: Page = browser.new_page(viewport=VIEWPORT)
            logger.info(f"访问页面: {page_url}")
            page.goto(page_url, timeout=60000)
            logger.info("页面加载完成，等待图表渲染...")
            page.wait_for_timeout(WAIT_TIME_MS)

            # 定位下方图表容器（通过时间选择器文本“1d”）
            all_time_selectors = page.locator(".ant-select-selector")
            target_selector = None
            for i in range(all_time_selectors.count()):
                txt = all_time_selectors.nth(i).text_content().strip()
                if txt == '1d':
                    target_selector = all_time_selectors.nth(i)
                    break
            if target_selector is None:
                if all_time_selectors.count() >= 2:
                    target_selector = all_time_selectors.nth(1)
                else:
                    target_selector = all_time_selectors.first
            chart_container = target_selector.locator("..").locator("..")
            logger.info("已定位下方图表容器")

            # 在容器内找到时间选择器并切换到 1w（如果是聚合图）或保持 1M（热图）
            # 根据 URL 判断需要切换的周期
            if '/liq-map/' in page_url and 'heat-map' not in page_url:
                logger.info("聚合图页面，切换到 1w 周期")
                target_selector.click()
                page.wait_for_timeout(1000)
                dropdown_item = page.locator(".ant-select-dropdown .ant-select-item[title='1w']")
                if dropdown_item.count() == 0:
                    dropdown_item = page.locator("text=1w").last
                dropdown_item.click()
                logger.info("已切换到 1w 周期")
                page.wait_for_timeout(8000)
            else:
                logger.info("热图页面，保持 1M 周期，无需切换")

            # 滚动使图表区域可见
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            page.wait_for_timeout(2000)

            # 点击相机按钮并监听下载
            with page.expect_download() as download_info:
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
            download.save_as(filename)
            logger.info(f"截图已保存为: {filename}")
            browser.close()
            return True
    except Exception as e:
        logger.error(f"抓取截图失败: {e}")
        # 如果出错，尝试截取页面快照
        try:
            page.screenshot(path=f"error_{os.path.basename(filename)}.png")
        except:
            pass
        return False

def scrape_heatmap() -> Optional[str]:
    """
    抓取清算热力图 (1M) 并保存为本地文件，返回文件路径。
    """
    today = get_today_beijing()
    filename = f"{today}_BTC_清算热力图_1M.png"
    success = capture_screenshot(HEATMAP_URL, filename)
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
    success = capture_screenshot(AGGREGATE_URL, filename)
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
        gh = Github(token)
        repo = gh.get_repo(repo_name)
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
        except:
            repo.create_file(remote_path, f"Add {now.date()}", content)
            logger.info(f"已创建 GitHub 文件: {remote_path}")
        # 生成 raw 链接
        raw_url = f"https://raw.githubusercontent.com/{repo_name}/main/{remote_path}"
        logger.info(f"Raw URL: {raw_url}")
        return raw_url
    except GithubException as e:
        logger.error(f"GitHub 上传失败: {e}")
        return None

def get_today_notion_page(notion_token: str, db_id: str) -> Optional[str]:
    """
    查询 Notion 数据库中 Created_Date 为今天（北京时间）的页面，返回页面 ID。
    """
    try:
        notion = NotionClient(auth=notion_token)
        today = get_today_beijing()
        logger.info(f"查询 Notion 数据库，Created_Date = {today}")
        response = notion.databases.query(
            database_id=db_id,
            filter={
                "property": "Created_Date",
                "date": {
                    "equals": today
                }
            }
        )
        results = response.get('results', [])
        if len(results) == 0:
            logger.warning(f"未找到今天（{today}）的 Notion 页面")
            return None
        page = results[0]
        page_id = page['id']
        logger.info(f"找到 Notion 页面: {page_id}")
        return page_id
    except APIResponseError as e:
        logger.error(f"Notion 查询失败: {e}")
        return None

def update_notion_page(notion_token: str, page_id: str, heatmap_url: str, aggregate_url: str):
    """
    更新 Notion 页面的“数据图”和“清算地图”属性。
    """
    try:
        notion = NotionClient(auth=notion_token)
        properties = {}
        if heatmap_url:
            properties["数据图"] = {"url": heatmap_url}
        if aggregate_url:
            properties["清算地图"] = {"url": aggregate_url}
        if not properties:
            logger.warning("没有可更新的属性，跳过 Notion 更新")
            return
        notion.pages.update(page_id=page_id, properties=properties)
        logger.info(f"Notion 页面更新成功，属性: {list(properties.keys())}")
    except APIResponseError as e:
        logger.error(f"Notion 更新失败: {e}")

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

def main():
    logger.info("=== CoinAnk 自动抓取脚本开始 ===")

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
    for file_path in [heatmap_file, liq_map_file]:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"已删除本地文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除本地文件失败 {file_path}: {e}")

    logger.info("=== 脚本执行完成 ===")

if __name__ == "__main__":
    main()
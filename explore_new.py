#!/usr/bin/env python3
"""
探索 CoinAnk 清算地图页面结构，查找下方图表区域、时间选择器和相机按钮
目标网址：https://coinank.com/zh/chart/derivatives/liq-map/binance/btcusdt/1w
"""
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

URL = "https://coinank.com/zh/chart/derivatives/liq-map/binance/btcusdt/1w"
VIEWPORT = {'width': 1920, 'height': 1200}

def explore():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(URL, timeout=60000)
        logger.info("页面加载完成，等待渲染...")
        page.wait_for_timeout(10000)  # 等待10秒

        # 1. 查找包含“BTC 清算地图”或“BTC Liquidation Map”的容器
        logger.info("查找包含 'BTC 清算地图' 或 'BTC Liquidation Map' 的元素...")
        possible_texts = ["BTC 清算地图", "BTC Liquidation Map"]
        container = None
        for text in possible_texts:
            try:
                # 使用 Playwright 的文本选择器
                container = page.locator(f"text={text}").first
                if container.count() > 0:
                    logger.info(f"找到文本: '{text}'")
                    # 获取父级容器，可能是 div 或 section
                    container = container.locator("..").locator("..")  # 向上两层
                    break
            except:
                pass
        
        if container is None:
            logger.warning("未找到标题文本，尝试查找所有图表容器")
            # 打印页面所有文本以便调试
            all_text = page.text_content('body')
            with open('page_text.txt', 'w', encoding='utf-8') as f:
                f.write(all_text[:5000])
            logger.info("已保存页面部分文本到 page_text.txt")

        # 2. 查找时间选择器（可能显示为 "1d", "1w", "1M" 等）
        logger.info("查找时间选择器...")
        time_buttons = page.query_selector_all('button, .ant-select-selector, .ant-picker, [class*="time"]')
        for idx, el in enumerate(time_buttons):
            txt = el.text_content().strip()
            if txt in ['1d', '1w', '1M', '1h', '4h', '12h']:
                logger.info(f"时间选择器 {idx}: text='{txt}', class='{el.get_attribute('class')}'")

        # 3. 查找相机按钮
        logger.info("查找相机按钮...")
        camera_elements = page.query_selector_all('[class*="camera"], [class*="download"], [class*="export"], [title*="camera"], [title*="download"], [title*="export"], button:has(svg)')
        for idx, el in enumerate(camera_elements):
            cls = el.get_attribute('class') or ''
            title = el.get_attribute('title') or ''
            text = el.text_content()[:30] if el.text_content() else ''
            logger.info(f"相机按钮 {idx}: class='{cls}', title='{title}', text='{text}'")

        # 4. 截图以便查看
        page.screenshot(path='explore_new.png')
        logger.info("截图已保存为 explore_new.png")

        # 5. 获取下方图表区域的所有文本内容（如果容器存在）
        if container:
            logger.info("下方图表区域的文本内容:")
            text = container.text_content()
            with open('container_text.txt', 'w', encoding='utf-8') as f:
                f.write(text)
            logger.info(f"容器文本长度: {len(text)}")

        browser.close()

if __name__ == "__main__":
    explore()
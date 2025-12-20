#!/usr/bin/env python3
"""
CoinAnk 比特币清算热力图抓取脚本（通过官方相机按钮下载高清截图）
目标网址：https://coinank.com/zh/chart/derivatives/liq-heat-map/btcusdt/1M
使用 Playwright (sync_api) 监听下载事件
"""

import logging
import datetime
from playwright.sync_api import sync_playwright

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
URL = "https://coinank.com/zh/chart/derivatives/liq-map/binance/btcusdt/1w"
DOWNLOAD_FILENAME = f"{datetime.datetime.now().strftime('%Y-%m-%d')}_BTC_全网聚合清算_1W.png"
VIEWPORT = {'width': 1920, 'height': 1200}
WAIT_TIME_MS = 15000  # 15秒

# 最新 Chrome 用户代理
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 相机按钮选择器（根据探索结果）
CAMERA_BUTTON_SELECTOR = ".anticon.anticon-camera"

def main():
    logger.info("开始抓取比特币清算热力图（通过官方相机按钮下载）...")
    
    with sync_playwright() as p:
        # 启动浏览器，添加反检测参数
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                f'--user-agent={USER_AGENT}',
            ]
        )
        
        # 创建页面并设置视口
        page = browser.new_page(viewport=VIEWPORT)
        logger.info(f"视口设置为: {VIEWPORT}")
        
        try:
            # 导航到目标页面
            logger.info(f"正在访问: {URL}")
            page.goto(URL, timeout=60000)  # 60秒超时
            logger.info("页面加载完成，等待图表渲染...")
            
            # 强制等待15秒，确保Canvas/SVG完全渲染
            page.wait_for_timeout(WAIT_TIME_MS)
            logger.info(f"已等待 {WAIT_TIME_MS/1000} 秒")
            
            # 定位下方图表容器（通过时间选择器文本“1d”）
            logger.info("定位下方图表容器...")
            # 找到所有时间选择器
            all_time_selectors = page.locator(".ant-select-selector")
            target_selector = None
            for i in range(all_time_selectors.count()):
                txt = all_time_selectors.nth(i).text_content().strip()
                logger.info(f"时间选择器 {i}: text='{txt}'")
                if txt == '1d':
                    target_selector = all_time_selectors.nth(i)
                    break
            if target_selector is None:
                # 如果没有找到1d，假设第二个时间选择器是下方图表
                logger.warning("未找到显示为 '1d' 的时间选择器，使用第二个时间选择器")
                if all_time_selectors.count() >= 2:
                    target_selector = all_time_selectors.nth(1)
                else:
                    target_selector = all_time_selectors.first
            # 向上两层获取图表容器
            chart_container = target_selector.locator("..").locator("..")
            logger.info("已定位下方图表容器")
            
            # 打印容器文本以便调试
            container_text = chart_container.text_content()
            logger.info(f"容器文本预览: {container_text[:200]}...")
            
            # 在容器内找到当前显示为 '1d' 的时间选择器
            logger.info("查找时间选择器...")
            # 使用之前找到的目标时间选择器
            target_selector.click()
            logger.info("已点击时间选择器")
            
            # 等待下拉菜单出现
            page.wait_for_timeout(1000)
            # 选择 '1w' 选项
            logger.info("选择 '1w' 选项...")
            dropdown_item = page.locator(".ant-select-dropdown .ant-select-item[title='1w']")
            if dropdown_item.count() == 0:
                # 备用选择器：包含文本 '1w' 的项
                dropdown_item = page.locator("text=1w").last
            dropdown_item.click()
            logger.info("已切换到 1w 周期")
            
            # 等待图表刷新（5-8秒）
            logger.info("等待图表数据刷新...")
            page.wait_for_timeout(8000)
            
            # 滚动使图表区域可见（可选，确保相机按钮在视窗内）
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            logger.info("已执行滚动操作，使图表区域可见")
            
            # 等待滚动后的短暂稳定
            page.wait_for_timeout(2000)
            
            # 使用 expect_download 上下文管理器监听下载事件
            logger.info("准备点击相机按钮并监听下载...")
            with page.expect_download() as download_info:
                # 在下方图表容器内点击相机按钮
                camera_button = chart_container.locator(".anticon.anticon-camera")
                if camera_button.count() > 0:
                    camera_button.click()
                    logger.info("已点击下方图表区域的相机按钮")
                else:
                    # 如果选择器不可见，尝试其他选择器
                    logger.warning("相机按钮不可见，尝试备用选择器")
                    # 调试：打印容器文本内容
                    container_text = chart_container.text_content()
                    logger.info(f"容器文本内容（前500字符）: {container_text[:500]}")
                    # 备用选择器：包含 camera 类名的任何元素
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
                        # 如果容器内找不到，尝试全局查找（降级）
                        logger.warning("容器内未找到相机按钮，尝试全局查找")
                        if page.is_visible(CAMERA_BUTTON_SELECTOR):
                            page.click(CAMERA_BUTTON_SELECTOR)
                            logger.info("已点击全局相机按钮")
                        else:
                            raise Exception("未找到可点击的相机按钮")
            
            # 获取下载对象
            download = download_info.value
            logger.info(f"下载开始: {download.suggested_filename}")
            
            # 等待下载完成并保存到指定文件名
            download.save_as(DOWNLOAD_FILENAME)
            logger.info(f"高清截图已保存为: {DOWNLOAD_FILENAME}")
            
            # 打印最终保存路径（绝对路径）
            import os
            abs_path = os.path.abspath(DOWNLOAD_FILENAME)
            logger.info(f"文件保存路径: {abs_path}")
            
        except Exception as e:
            logger.error(f"抓取过程中出现错误: {e}")
            # 若出错，尝试截取当前页面状态
            try:
                page.screenshot(path="error_snapshot.png")
                logger.info("错误状态已保存至 error_snapshot.png")
            except:
                pass
            raise
        
        finally:
            # 关闭浏览器
            browser.close()
            logger.info("浏览器已关闭")
    
    logger.info("脚本执行完毕")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

URL = "https://coinank.com/zh/chart/derivatives/liq-map/binance/btcusdt/1w"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1920, 'height': 1200})
    page.goto(URL, timeout=60000)
    page.wait_for_timeout(10000)
    
    # 查找所有包含“BTC 清算地图”的元素
    titles = page.locator("text=BTC 清算地图")
    print(f"找到 'BTC 清算地图' 的数量: {titles.count()}")
    for i in range(titles.count()):
        print(f"  {i}: 文本: {titles.nth(i).text_content()}")
        # 获取父元素
        parent = titles.nth(i).locator("..")
        print(f"    父类: {parent.get_attribute('class')}")
    
    # 查找所有包含“BTC Liquidation Map”的元素
    titles_en = page.locator("text=BTC Liquidation Map")
    print(f"找到 'BTC Liquidation Map' 的数量: {titles_en.count()}")
    
    # 查找所有图表容器（可能具有特定类名）
    chart_containers = page.locator('[class*="chart"], [class*="graph"]')
    print(f"图表容器数量: {chart_containers.count()}")
    
    # 截图
    page.screenshot(path='debug.png')
    browser.close()
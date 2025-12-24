#!/usr/bin/env python3
"""
探索 CoinAnk 页面结构，查找相机按钮的选择器
"""
import asyncio
from playwright.sync_api import sync_playwright

URL = "https://coinank.com/zh/chart/derivatives/liq-heat-map/btcusdt/1M"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1920, 'height': 1200})
    page.goto(URL, timeout=60000)
    page.wait_for_timeout(15000)  # 等待15秒
    
    # 查找所有按钮和链接，特别是包含 camera, download, export 等关键词的
    print("=== 查找可能包含 'camera' 的元素 ===")
    camera_elements = page.query_selector_all('[class*="camera"], [class*="download"], [class*="export"], [title*="camera"], [title*="download"], [title*="export"]')
    for idx, el in enumerate(camera_elements):
        cls = el.get_attribute('class') or ''
        title = el.get_attribute('title') or ''
        text = el.text_content()[:50] if el.text_content() else ''
        print(f"{idx}: class='{cls}', title='{title}', text='{text}'")
    
    print("\n=== 查找所有 button 元素 ===")
    buttons = page.query_selector_all('button')
    for idx, btn in enumerate(buttons):
        cls = btn.get_attribute('class') or ''
        title = btn.get_attribute('title') or ''
        text = btn.text_content()[:50] if btn.text_content() else ''
        print(f"{idx}: class='{cls}', title='{title}', text='{text}'")
    
    print("\n=== 查找所有 svg 元素 ===")
    svgs = page.query_selector_all('svg')
    for idx, svg in enumerate(svgs[:10]):  # 限制数量
        cls = svg.get_attribute('class') or ''
        parent = svg.evaluate('el => el.parentNode.tagName', svg)
        print(f"{idx}: class='{cls}', parent tag: {parent}")
    
    # 截图以便查看
    page.screenshot(path='explore.png')
    print("截图已保存为 explore.png")
    
    browser.close()
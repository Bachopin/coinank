#!/usr/bin/env python3
"""
系统环境检查脚本
检查服务器环境是否满足 CoinAnk 脚本运行要求
"""

import sys
import os
import platform
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    print("🐍 检查 Python 版本...")
    version = sys.version_info
    print(f"   Python 版本: {version.major}.{version.minor}.{version.micro}")
    
    if version >= (3, 8):
        print("   ✅ Python 版本满足要求 (>= 3.8)")
        return True
    else:
        print("   ❌ Python 版本过低，需要 3.8 或更高版本")
        return False

def check_system_info():
    """检查系统信息"""
    print("💻 系统信息:")
    print(f"   操作系统: {platform.system()}")
    print(f"   系统版本: {platform.release()}")
    print(f"   架构: {platform.machine()}")
    print(f"   处理器: {platform.processor()}")
    
    # 检查内存
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
            for line in meminfo.split('\n'):
                if 'MemTotal' in line:
                    mem_kb = int(line.split()[1])
                    mem_gb = mem_kb / 1024 / 1024
                    print(f"   内存: {mem_gb:.1f} GB")
                    if mem_gb >= 2:
                        print("   ✅ 内存充足 (>= 2GB)")
                    else:
                        print("   ⚠️  内存可能不足，建议至少 2GB")
                    break
    except:
        print("   ⚠️  无法检测内存信息")

def check_required_packages():
    """检查必需的 Python 包"""
    print("📦 检查 Python 依赖包...")
    
    required_packages = [
        'playwright',
        'pytz', 
        'github',
        'notion_client',
        'python_dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'python_dotenv':
                importlib.import_module('dotenv')
            elif package == 'github':
                importlib.import_module('github')
            else:
                importlib.import_module(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (未安装)")
            missing_packages.append(package)
    
    return missing_packages

def check_playwright_browsers():
    """检查 Playwright 浏览器"""
    print("🌐 检查 Playwright 浏览器...")
    
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("   ✅ Chromium 浏览器可用")
                return True
            except Exception as e:
                print(f"   ❌ Chromium 浏览器不可用: {e}")
                print("   💡 请运行: playwright install chromium")
                return False
    except ImportError:
        print("   ❌ Playwright 未安装")
        return False

def check_environment_variables():
    """检查环境变量"""
    print("🔑 检查环境变量...")
    
    env_file = Path('.env')
    if not env_file.exists():
        print("   ❌ .env 文件不存在")
        return False
    
    required_vars = ['GITHUB_TOKEN', 'NOTION_TOKEN', 'NOTION_DB_ID']
    missing_vars = []
    
    # 读取 .env 文件
    env_vars = {}
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"   ❌ 读取 .env 文件失败: {e}")
        return False
    
    for var in required_vars:
        if var in env_vars and env_vars[var]:
            print(f"   ✅ {var} (已设置)")
        else:
            print(f"   ❌ {var} (未设置或为空)")
            missing_vars.append(var)
    
    return len(missing_vars) == 0

def check_network_connectivity():
    """检查网络连接"""
    print("🌍 检查网络连接...")
    
    test_urls = [
        'https://coinank.com',
        'https://api.github.com',
        'https://api.notion.com'
    ]
    
    for url in test_urls:
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=10)
            print(f"   ✅ {url}")
        except Exception as e:
            print(f"   ❌ {url} - {e}")

def check_file_permissions():
    """检查文件权限"""
    print("📁 检查文件权限...")
    
    script_files = ['run_server.sh', 'main.py', 'main_optimized.py']
    
    for script in script_files:
        if os.path.exists(script):
            if os.access(script, os.X_OK):
                print(f"   ✅ {script} (可执行)")
            else:
                print(f"   ⚠️  {script} (不可执行)")
                print(f"      运行: chmod +x {script}")
        else:
            print(f"   ⚠️  {script} (文件不存在)")

def check_disk_space():
    """检查磁盘空间"""
    print("💾 检查磁盘空间...")
    
    try:
        statvfs = os.statvfs('.')
        free_bytes = statvfs.f_frsize * statvfs.f_bavail
        free_gb = free_bytes / (1024**3)
        
        print(f"   可用空间: {free_gb:.1f} GB")
        
        if free_gb >= 1:
            print("   ✅ 磁盘空间充足")
        else:
            print("   ⚠️  磁盘空间不足，建议至少 1GB")
    except:
        print("   ⚠️  无法检测磁盘空间")

def main():
    print("=" * 50)
    print("🔍 CoinAnk 服务器环境检查")
    print("=" * 50)
    
    checks = [
        check_python_version(),
        len(check_required_packages()) == 0,
        check_playwright_browsers(),
        check_environment_variables(),
    ]
    
    # 信息性检查（不影响总体结果）
    check_system_info()
    check_network_connectivity()
    check_file_permissions()
    check_disk_space()
    
    print("\n" + "=" * 50)
    
    if all(checks):
        print("🎉 所有关键检查通过！环境配置正确。")
        print("💡 可以运行: ./run_server.sh")
        return 0
    else:
        print("❌ 部分检查未通过，请根据上述提示修复问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
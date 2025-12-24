# CoinAnk 服务器部署指南

## 快速部署

### 1. 上传项目到服务器
```bash
# 使用 git 克隆（推荐）
git clone <your-repo-url> coinank
cd coinank

# 或者使用 scp 上传
scp -r /local/path/coinank user@server:/path/to/coinank
```

### 2. 运行自动部署脚本
```bash
chmod +x deploy_server.sh
./deploy_server.sh
```

### 3. 配置环境变量
编辑 `.env` 文件：
```bash
nano .env
```

填入正确的配置：
- `GITHUB_TOKEN`: GitHub 个人访问令牌
- `NOTION_TOKEN`: Notion 集成令牌  
- `NOTION_DB_ID`: Notion 数据库 ID

### 4. 测试运行
```bash
./run_server.sh
```

### 5. 配置定时任务
```bash
crontab -e
```
添加：
```
0 7 * * * /path/to/coinank/run_server.sh
```

## 系统要求

### 最低配置
- **操作系统**: Ubuntu 18.04+ / CentOS 7+ / Debian 10+
- **内存**: 2GB RAM
- **存储**: 5GB 可用空间
- **网络**: 能访问外网

### 推荐配置
- **操作系统**: Ubuntu 20.04 LTS
- **内存**: 4GB RAM
- **存储**: 10GB 可用空间
- **CPU**: 2 核心

## 详细部署步骤

### 1. 系统准备
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git python3 python3-pip python3-venv
```

### 2. 安装系统依赖
```bash
# Playwright 浏览器依赖
sudo apt install -y \
    libnss3-dev \
    libatk-bridge2.0-dev \
    libdrm-dev \
    libxcomposite-dev \
    libxdamage-dev \
    libxrandr-dev \
    libgbm-dev \
    libxss-dev \
    libasound2-dev
```

### 3. 项目配置
```bash
cd coinank

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium
```

### 4. 环境变量配置
```bash
cp .env.example .env
nano .env
```

### 5. 权限设置
```bash
chmod +x *.sh *.py
mkdir -p logs
```

## 环境检查

运行系统检查脚本：
```bash
python3 check_system.py
```

这会检查：
- Python 版本
- 依赖包安装
- Playwright 浏览器
- 环境变量配置
- 网络连接
- 文件权限

## 定时任务配置

### 基本配置
```bash
crontab -e
```

添加以下内容：
```bash
# 每天早上 7:00 执行
0 7 * * * /path/to/coinank/run_server.sh

# 设置环境变量（可选）
PATH=/usr/local/bin:/usr/bin:/bin
SHELL=/bin/bash
```

### 高级配置
```bash
# 多次重试机制
0 7 * * * /path/to/coinank/run_server.sh
5 7 * * * /path/to/coinank/run_server.sh

# 错误通知
0 7 * * * /path/to/coinank/run_server.sh || echo "CoinAnk failed" | mail -s "Error" admin@example.com
```

## 监控和日志

### 查看运行日志
```bash
# 实时查看日志
tail -f logs/run.log

# 查看最近的日志
tail -n 100 logs/run.log

# 查看错误日志
grep ERROR logs/run.log
```

### 系统监控
```bash
# 查看 cron 服务状态
sudo systemctl status cron

# 查看 cron 日志
sudo tail -f /var/log/syslog | grep CRON

# 查看进程
ps aux | grep python
```

## 故障排除

### 常见问题

#### 1. Playwright 浏览器启动失败
```bash
# 重新安装浏览器
playwright install chromium
playwright install-deps chromium

# 检查系统依赖
sudo apt install -y libnss3-dev libatk-bridge2.0-dev
```

#### 2. 权限问题
```bash
# 设置正确权限
chmod +x run_server.sh
chmod +x main_optimized.py

# 检查目录权限
ls -la logs/
```

#### 3. 网络连接问题
```bash
# 测试网络连接
curl -I https://coinank.com
curl -I https://api.github.com
curl -I https://api.notion.com
```

#### 4. 环境变量问题
```bash
# 检查 .env 文件
cat .env

# 测试环境变量加载
python3 -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('GITHUB_TOKEN'))"
```

### 调试模式
临时启用调试模式：
```bash
export HEADLESS=false
./run_server.sh
```

## 安全建议

### 1. 文件权限
```bash
# 限制 .env 文件权限
chmod 600 .env

# 设置目录权限
chmod 755 .
chmod 644 *.md *.txt
chmod 755 *.sh *.py
```

### 2. 用户权限
- 不要使用 root 用户运行脚本
- 创建专用用户：
```bash
sudo useradd -m -s /bin/bash coinank
sudo su - coinank
```

### 3. 防火墙配置
```bash
# 只开放必要端口
sudo ufw enable
sudo ufw allow ssh
```

## 性能优化

### 1. 系统优化
```bash
# 增加文件描述符限制
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
```

### 2. 内存优化
在 `main_optimized.py` 中已包含：
- 单进程模式（`--single-process`）
- 禁用 GPU 加速
- 优化浏览器参数

### 3. 磁盘空间管理
```bash
# 定期清理日志
find logs/ -name "*.log" -mtime +30 -delete

# 清理临时文件
find . -name "error_*.png" -mtime +7 -delete
```

## 备份和恢复

### 备份脚本
```bash
#!/bin/bash
# backup.sh
tar -czf "coinank_backup_$(date +%Y%m%d).tar.gz" \
    --exclude='.venv' \
    --exclude='logs' \
    --exclude='*.png' \
    .
```

### 恢复
```bash
tar -xzf coinank_backup_YYYYMMDD.tar.gz
./deploy_server.sh
```

## 更新和维护

### 更新代码
```bash
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
```

### 定期维护
- 每月检查依赖更新
- 每周查看日志文件
- 每季度备份配置

## 支持

如遇问题，请检查：
1. 运行 `python3 check_system.py`
2. 查看 `logs/run.log`
3. 检查系统日志 `/var/log/syslog`
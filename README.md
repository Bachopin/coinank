# CoinAnk 清算地图自动抓取脚本 v1.0

基于 Playwright 的自动化脚本，每日自动抓取 CoinAnk 比特币清算图并同步到 Notion。

## 功能特性

- 🖼️ **双图抓取**：清算热力图（1M）+ 全网聚合清算图（1W）
- ☁️ **GitHub 存储**：自动上传截图到 GitHub 仓库
- 📝 **Notion 同步**：自动更新 Notion 数据库页面
- 🔄 **防重复执行**：每日只执行一次，失败自动重试
- 🧹 **自动清理**：GitHub 图片保留 30 天，自动清理过期文件
- ⏱️ **超时保护**：全局 10 分钟超时，防止脚本卡死
- 📊 **日志轮转**：自动管理日志文件大小

## 快速开始

### 环境要求

- Python 3.8+
- macOS / Linux

### 安装

```bash
# 克隆仓库
git clone https://github.com/Bachopin/coinank.git
cd coinank

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
playwright install chromium
```

### 配置

1. 复制环境变量模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的配置：
```env
GITHUB_TOKEN=your_github_token
GITHUB_REPO=your_username/your_repo
NOTION_TOKEN=your_notion_token
NOTION_DB_ID=your_notion_database_id
```

### 运行

```bash
python main.py
```

## 配置说明

所有配置选项集中在 `config.py` 文件中：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `VIEWPORT` | 1920x1200 | 浏览器视口大小 |
| `WAIT_TIME_MS` | 15000 | 页面渲染等待时间（毫秒） |
| `PAGE_TIMEOUT_MS` | 90000 | 页面加载超时（毫秒） |
| `MAX_RETRIES` | 3 | 截图失败最大重试次数 |
| `GITHUB_IMAGE_RETENTION_DAYS` | 30 | GitHub 图片保留天数 |
| `GLOBAL_TIMEOUT_SECONDS` | 600 | 全局脚本超时（秒） |
| `LOG_MAX_SIZE_MB` | 10 | 日志文件最大大小（MB） |

## 定时任务

### macOS Crontab 设置

每小时第 10 分钟检查执行（每日只会真正执行一次）：

```bash
crontab -e
# 添加以下行：
10 * * * * /path/to/coinank/run_daily.sh
```

### 执行逻辑

1. 每小时触发一次
2. 检查锁文件，如果今天已成功执行则跳过
3. 抓取截图 → 上传 GitHub → 同步 Notion
4. 成功后标记完成，当天不再重复执行
5. 失败则下一小时自动重试

## 项目结构

```
coinank/
├── main.py           # 主脚本
├── config.py         # 配置文件
├── run_daily.sh      # 定时任务启动脚本
├── requirements.txt  # Python 依赖
├── .env.example      # 环境变量模板
├── .env              # 环境变量（不提交）
├── logs/             # 日志目录
│   ├── runtime.log   # 运行日志
│   └── run.log       # 定时任务日志
└── images/           # 截图存储（按月份组织）
    └── 2025-12/
```

## 日志与排错

- **运行日志**：`logs/runtime.log`，保留完整运行过程，并按大小自动轮转
- **定时任务日志**：`logs/run.log`，只保留失败时的详细输出和简短运行记录
- **错误截图**：失败时自动保存 `error_*.png`

### 常见问题

1. **页面加载超时**：检查网络连接，脚本会自动重试
2. **Playwright 未安装**：运行 `playwright install chromium`
3. **权限不足**：确保 `run_daily.sh` 有执行权限 (`chmod +x run_daily.sh`)

## 资源消耗

- **已完成时**：< 1 秒，几乎无消耗
- **实际执行时**：1-2 分钟，内存峰值约 200-300MB
- **存储**：每日约 1.3MB，每月约 40MB

## 更新日志

### v1.0.0 (2025-12-25)
- 初始稳定版本
- 双图抓取（热力图 + 聚合图）
- GitHub 自动上传和清理
- Notion 自动同步
- 防重复执行机制
- 全局超时保护
- 配置文件分离

## 许可证

MIT

# CoinAnk 清算地图抓取脚本

基于 Playwright 的自动化脚本，用于从 CoinAnk 网站下载比特币清算地图的高清截图。

## 功能特性

- 自动定位页面下方的 BTC 清算地图图表（区别于上方图表）
- 将时间周期从 1d 切换为 1w（等待图表刷新）
- 通过官方“相机”按钮触发下载，获取高清 PNG 截图
- 文件按日期自动命名：`YYYY-MM-DD_BTC_全网聚合清算_1W.png`
- 提供详细的调试日志，便于排查元素定位问题

## 快速开始

### 环境要求

- Python 3.8+
- Playwright 浏览器驱动

### 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 运行脚本

```bash
python main.py
```

脚本将以非无头模式启动浏览器，自动完成以下步骤：

1. 访问 `https://coinank.com/zh/chart/derivatives/liq-map/binance/btcusdt/1w`
2. 等待页面加载和图表渲染（约15秒）
3. 定位下方图表区域（通过时间选择器“1d”识别）
4. 点击时间选择器，切换到“1w”周期
5. 等待8秒让图表数据刷新
6. 点击图表区域内的相机按钮（若容器内未找到，则尝试全局查找）
7. 监听下载事件，将截图保存为当前日期的文件

### 输出示例

```
2025-12-21 03:08:04,849 - INFO - 开始抓取比特币清算热力图（通过官方相机按钮下载）...
2025-12-21 03:08:28,017 - INFO - 已切换到 1w 周期
2025-12-21 03:08:39,769 - INFO - 高清截图已保存为: 2025-12-21_BTC_全网聚合清算_1W.png
```

## 项目结构

- `main.py` – 主脚本，包含完整的交互逻辑
- `requirements.txt` – Python 依赖清单
- `explore.py` / `explore_new.py` – 页面结构探索工具（辅助开发）
- `debug.py` – 调试脚本
- `.gitignore` – 忽略图片、缓存等文件

## 如何贡献

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/your-idea`)
3. 提交更改 (`git commit -m 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-idea`)
5. 发起 Pull Request

## 注意事项

- 脚本默认使用 `headless=False`，以便观察操作过程；若需后台运行可改为 `headless=True`
- 若页面结构发生变化，可能需要调整元素选择器
- 下载的截图保存在脚本所在目录，请确保有写入权限

## 高级功能（最终版）

- **双图抓取**：同时抓取 BTC 清算热力图（1M）和全网聚合清算图（1W）。
- **GitHub 自动上传**：将截图上传至 `Bachopin/coinank` 仓库的 `images/` 目录，并生成 raw 链接。
- **Notion 自动更新**：查询当天创建的 Notion 页面，更新“数据图”和“清算地图”属性。
- **时区感知**：使用北京时间（Asia/Shanghai）确定今日日期，确保与 Notion 数据库匹配。

### 配置说明

1. 环境变量（可选）：
   - `GITHUB_TOKEN`：GitHub 个人访问令牌，用于上传截图。
2. 硬编码配置（已在 `main.py` 中设置）：
   - `NOTION_TOKEN` 和 `NOTION_DB_ID` 已填写。
   - `GITHUB_REPO` 已设置为 `"Bachopin/coinank"`。

### 定时任务（Mac Crontab）

每日早上 7:00 自动运行：
1. 确保 `run_daily.sh` 具有可执行权限。
2. 使用 `crontab -e` 添加行：
   ```
   0 7 * * * /Users/mextrel/VSCode/Coinank/run_daily.sh
   ```
3. 详细设置请参阅 [crontab_setup.md](crontab_setup.md)。

### 依赖扩展

更新后的 `requirements.txt` 包含以下包：
- `playwright`
- `pytz`
- `PyGithub`
- `notion-client`
- `requests`

安装所有依赖：
```bash
pip install -r requirements.txt
playwright install chromium
```

### 日志与排错

- 脚本运行时日志同时输出到控制台和 `runtime.log` 文件。
- 若截图失败，会在当前目录生成 `error_*.png` 快照。
- 定时任务执行情况可通过 `runtime.log` 查看。

## 许可证

MIT
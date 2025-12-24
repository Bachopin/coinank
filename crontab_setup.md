# 设置 Mac 定时任务 (Crontab) - 防重补跑版

## 防重补跑机制说明

现在脚本已内置防重补跑机制：
- ✅ **防重复执行**：同一天内多次运行，只有第一次会执行任务
- 🔄 **自动补跑**：如果某天没开机或任务失败，第二天会自动重试
- 📝 **状态记录**：通过 `daily_task.lock` 文件记录每日执行状态

## 1. 编辑当前用户的 crontab
在终端中执行：
```bash
crontab -e
```

## 2. 添加定时任务
在打开的文件末尾添加以下行（请根据实际路径调整）：

### 基础配置（推荐）
```bash
# 每天早上 7:00 执行
0 7 * * * /Users/mextrel/VSCode/Coinank/run_daily.sh
```

### 多重保障配置（防止错过）
```bash
# 每天早上 7:00, 7:30, 8:00 执行（防重机制确保只运行一次）
0 7 * * * /Users/mextrel/VSCode/Coinank/run_daily.sh
30 7 * * * /Users/mextrel/VSCode/Coinank/run_daily.sh
0 8 * * * /Users/mextrel/VSCode/Coinank/run_daily.sh
```

### 全天候配置（最大保障）
```bash
# 每2小时执行一次（防重机制确保每天只运行一次）
0 7-23/2 * * * /Users/mextrel/VSCode/Coinank/run_daily.sh
```

## 3. 保存并退出
- 如果使用 `vim` 编辑器：按 `ESC` 键，输入 `:wq` 回车。
- 如果使用 `nano` 编辑器：按 `Ctrl+O` 保存，然后 `Ctrl+X` 退出。

## 4. 验证 crontab
运行以下命令查看已添加的任务：
```bash
crontab -l
```

## 5. 防重补跑机制工作原理

### 锁文件机制
- **文件位置**：`daily_task.lock`
- **内容**：当天日期（如 `2025-12-24`）
- **检查逻辑**：每次运行时检查锁文件日期是否为今天

### 执行流程
1. **启动检查**：读取锁文件，如果是今天日期则直接退出
2. **任务执行**：抓取截图 → 上传 GitHub → 同步 Notion
3. **成功标记**：只有 Notion 同步成功才写入今天日期到锁文件

### 日志示例
```
✅ 今日任务已完成，无需重复执行  # 重复运行时
🚀 今日尚未执行，开始运行任务...  # 首次运行时
🎉 今日任务执行成功并已标记完成  # 成功完成时
⚠️ 任务未完全成功，不标记为完成（明天可重试）  # 失败时
```

## 6. 测试和验证

### 手动测试
```bash
cd /Users/mextrel/VSCode/Coinank

# 第一次运行（应该正常执行）
./run_daily.sh

# 第二次运行（应该显示已完成并退出）
./run_daily.sh
```

### 查看状态
```bash
# 查看锁文件内容
cat daily_task.lock

# 查看运行日志
tail -f logs/run.log
```

### 重置状态（测试用）
```bash
# 删除锁文件，允许重新运行
rm daily_task.lock
```

## 7. 优势对比

### 传统方式 vs 防重补跑
| 场景 | 传统方式 | 防重补跑机制 |
|------|----------|-------------|
| 正常运行 | ✅ 执行 | ✅ 执行并标记 |
| 重复运行 | ❌ 重复执行 | ✅ 自动跳过 |
| 电脑未开机 | ❌ 错过任务 | ✅ 开机后补跑 |
| 任务失败 | ❌ 需手动重试 | ✅ 自动重试 |
| 多时段设置 | ❌ 重复执行 | ✅ 只执行一次 |

## 8. 注意事项

### Mac 睡眠模式
- 确保 Mac 在定时任务时间点是唤醒状态
- 可以设置多个时间点增加成功率
- 或者在 `系统偏好设置 > 节能` 中设置定时唤醒

### 权限问题
- 确保 `run_daily.sh` 具有可执行权限
- 确保 Python 脚本可以创建和写入锁文件

### 时区设置
- 脚本使用北京时间（Asia/Shanghai）
- Mac 系统时区不影响脚本内部时区判断

## 9. 故障排除

### 如果任务没有执行
1. 检查 cron 服务：`sudo launchctl list | grep cron`
2. 查看系统日志：`log show --predicate 'process == "cron"' --last 1h`
3. 手动运行测试：`./run_daily.sh`

### 如果重复执行
1. 检查锁文件：`cat daily_task.lock`
2. 检查日志：`tail logs/run.log`
3. 确认脚本版本是否为最新

### 清理和重置
```bash
# 清理锁文件
rm -f daily_task.lock

# 清理日志文件
rm -f logs/run.log

# 重新测试
./run_daily.sh
```

## 10. 高级配置

### 邮件通知（可选）
```bash
# 失败时发送邮件通知
0 7 * * * /Users/mextrel/VSCode/Coinank/run_daily.sh || echo "CoinAnk task failed on $(date)" | mail -s "Task Failed" your@email.com
```

### 日志轮转（可选）
```bash
# 每月清理旧日志
0 0 1 * * find /Users/mextrel/VSCode/Coinank/logs -name "*.log" -mtime +30 -delete
```

现在你可以放心设置多个时间点的 crontab，防重机制会确保每天只执行一次任务！
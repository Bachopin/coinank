# 设置 Mac 定时任务 (Crontab)

## 1. 编辑当前用户的 crontab
在终端中执行：
```bash
crontab -e
```

## 2. 添加定时任务
在打开的文件末尾添加以下行（请根据实际路径调整）：
```
0 7 * * * /Users/mextrel/VSCode/Coinank/run_daily.sh
```
这表示每天上午 7:00（系统时区）执行脚本。

如果你希望使用北京时间（UTC+8），请确保系统时区已正确设置。Mac 默认使用系统时区，crontab 也使用该时区。

## 3. 保存并退出
- 如果使用 `vim` 编辑器：按 `ESC` 键，输入 `:wq` 回车。
- 如果使用 `nano` 编辑器：按 `Ctrl+O` 保存，然后 `Ctrl+X` 退出。

## 4. 验证 crontab
运行以下命令查看已添加的任务：
```bash
crontab -l
```

## 5. 注意事项
- 确保 `run_daily.sh` 具有可执行权限（已设置）。
- 脚本中的 Python 依赖需已安装（playwright, pytz, pygithub, notion-client）。
- 建议先手动运行一次脚本以确保正常工作：
  ```bash
  cd /Users/mextrel/VSCode/Coinank
  ./run_daily.sh
  ```
- 日志文件 `runtime.log` 会记录每次运行的输出，可用于排查问题。

## 6. 调试技巧
如果任务没有执行，可以检查系统日志：
```bash
grep cron /var/log/system.log
```
或者查看邮件通知（cron 会将错误发送到用户邮箱）。

## 7. 使用环境变量
如果脚本依赖环境变量（如 `GITHUB_TOKEN`），可以在 crontab 中设置：
```
0 7 * * * export GITHUB_TOKEN=your_token_here && /Users/mextrel/VSCode/Coinank/run_daily.sh
```
或者更安全地在脚本中通过 `os.getenv` 读取。
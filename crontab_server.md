# Linux 服务器定时任务配置

## 1. 编辑 crontab
```bash
crontab -e
```

## 2. 添加定时任务
将以下内容添加到 crontab 文件中（请根据实际路径调整）：

```bash
# CoinAnk 自动抓取任务 - 每天早上 7:00 执行
0 7 * * * /path/to/coinank/run_server.sh

# 可选：每天早上 7:05 执行备份任务
5 7 * * * /path/to/coinank/run_server.sh
```

## 3. 时区设置
确保服务器时区正确设置为北京时间：
```bash
# 查看当前时区
timedatectl

# 设置为北京时间（如果需要）
sudo timedatectl set-timezone Asia/Shanghai
```

## 4. 验证 crontab
```bash
# 查看当前用户的 crontab
crontab -l

# 查看 cron 服务状态
sudo systemctl status cron     # Ubuntu/Debian
sudo systemctl status crond    # CentOS/RHEL
```

## 5. 启动 cron 服务（如果未启动）
```bash
# Ubuntu/Debian
sudo systemctl enable cron
sudo systemctl start cron

# CentOS/RHEL
sudo systemctl enable crond
sudo systemctl start crond
```

## 6. 测试定时任务
手动运行脚本测试：
```bash
cd /path/to/coinank
./run_server.sh
```

## 7. 查看日志
```bash
# 查看脚本运行日志
tail -f /path/to/coinank/logs/run.log

# 查看系统 cron 日志
sudo tail -f /var/log/cron      # CentOS/RHEL
sudo tail -f /var/log/syslog    # Ubuntu/Debian
```

## 8. 环境变量注意事项
cron 环境变量有限，确保脚本中包含必要的 PATH 设置：
```bash
# 在 crontab 中设置环境变量（可选）
PATH=/usr/local/bin:/usr/bin:/bin
SHELL=/bin/bash

0 7 * * * /path/to/coinank/run_server.sh
```

## 9. 调试技巧
如果定时任务不执行：
1. 检查脚本权限：`ls -la run_server.sh`
2. 检查脚本路径是否正确
3. 手动运行脚本测试
4. 查看系统日志：`sudo grep CRON /var/log/syslog`

## 10. 高级配置
### 错误通知
```bash
# 发送邮件通知（需要配置邮件服务）
0 7 * * * /path/to/coinank/run_server.sh || echo "CoinAnk script failed" | mail -s "CronJob Failed" admin@example.com
```

### 多次重试
```bash
# 如果失败，5分钟后重试
0 7 * * * /path/to/coinank/run_server.sh
5 7 * * * /path/to/coinank/run_server.sh
```

### 锁定机制（防止重复执行）
在 `run_server.sh` 中添加锁定机制：
```bash
# 在脚本开头添加
LOCKFILE="/tmp/coinank.lock"
if [ -f "$LOCKFILE" ]; then
    echo "脚本已在运行中，退出"
    exit 1
fi
echo $$ > "$LOCKFILE"

# 在脚本结尾添加
rm -f "$LOCKFILE"
```
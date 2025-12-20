#!/bin/bash
# CoinAnk 每日自动抓取脚本 (Crontab 调度)
# 设置 PATH 确保能找到 playwright 和 python

# 加载用户环境变量（针对 crontab 环境）
if [ -f "$HOME/.bash_profile" ]; then
    source "$HOME/.bash_profile"
elif [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc"
fi

# 添加常用路径到 PATH
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"

# 切换到脚本所在目录（项目根目录）
cd "$(dirname "$0")" || {
    echo "错误：无法切换到脚本目录" >&2
    exit 1
}

# 记录运行开始时间
echo "=== 开始运行 $(date '+%Y-%m-%d %H:%M:%S') ===" >> run.log

# 运行 Python 脚本，将 stdout 和 stderr 追加到 run.log
python3 main.py >> run.log 2>&1
EXIT_CODE=$?

# 记录运行结束时间
echo "=== 运行结束 $(date '+%Y-%m-%d %H:%M:%S')，退出码: $EXIT_CODE ===" >> run.log

# 如果出错，可在此添加通知（如发送邮件）
if [ $EXIT_CODE -ne 0 ]; then
    echo "警告：脚本执行失败，退出码: $EXIT_CODE" >&2
fi

exit $EXIT_CODE
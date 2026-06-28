#!/bin/bash
# CoinAnk 每日自动抓取脚本 (Mac 本地版 + 防重补跑机制)
# 设置 PATH 确保能找到 playwright 和 python

# 加载用户环境变量（针对 crontab 环境）
if [ -f "$HOME/.bash_profile" ]; then
    source "$HOME/.bash_profile"
elif [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc"
fi

# 添加常用路径到 PATH
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:/opt/homebrew/bin:$PATH"

# 切换到脚本所在目录（项目根目录）
cd "$(dirname "$0")" || {
    echo "错误：无法切换到脚本目录" >&2
    exit 1
}

# 检查并激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 创建日志目录
mkdir -p logs

RUN_LOG="logs/run.log"
TEMP_OUTPUT_FILE=$(mktemp)

cleanup_temp_file() {
    rm -f "$TEMP_OUTPUT_FILE"
}

trap cleanup_temp_file EXIT

# 记录运行开始时间
echo "=== 开始运行 $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$RUN_LOG"

# 运行 Python 脚本：成功时只保留简短记录，失败时把详细输出写入 run.log
if python3 main.py > "$TEMP_OUTPUT_FILE" 2>&1; then
    EXIT_CODE=0
else
    EXIT_CODE=$?
    {
        echo "--- 详细输出开始 ---"
        cat "$TEMP_OUTPUT_FILE"
        echo "--- 详细输出结束 ---"
    } >> "$RUN_LOG"
fi

# 记录运行结束时间
echo "=== 运行结束 $(date '+%Y-%m-%d %H:%M:%S')，退出码: $EXIT_CODE ===" >> "$RUN_LOG"

# 如果出错，可在此添加通知（如发送邮件）
if [ $EXIT_CODE -ne 0 ]; then
    echo "警告：脚本执行失败，退出码: $EXIT_CODE" >&2
fi

exit $EXIT_CODE
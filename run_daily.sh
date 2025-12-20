#!/bin/bash
# 每日自动运行 CoinAnk 抓取脚本

# 切换到项目目录
cd "/Users/mextrel/VSCode/Coinank" || {
    echo "错误：无法切换到项目目录" >&2
    exit 1
}

# 加载环境变量（如果存在 .env 文件）
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo "已加载 .env 文件"
else
    echo "未找到 .env 文件，依赖已有环境变量"
fi

# 激活 Python 虚拟环境（如果存在）
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "虚拟环境已激活"
else
    echo "未找到虚拟环境，使用系统 Python"
fi

# 运行主脚本，将输出追加到 runtime.log
echo "=== $(date) 开始运行 ===" >> runtime.log
python3 main.py >> runtime.log 2>&1
EXIT_CODE=$?
echo "=== $(date) 运行结束，退出码: $EXIT_CODE ===" >> runtime.log

# 如果出错，发送通知（可选）
if [ $EXIT_CODE -ne 0 ]; then
    echo "脚本执行失败，退出码: $EXIT_CODE" >&2
fi

exit $EXIT_CODE
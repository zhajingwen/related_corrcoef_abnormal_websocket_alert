#!/bin/bash
# 资源监控脚本 - 每分钟记录一次系统资源使用情况

LOG_DIR="monitoring_logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/resources_${TIMESTAMP}.log"

echo "时间,进程ID,CPU%,内存MB,线程数,文件描述符,数据库连接数" > "$LOG_FILE"

echo "✅ 资源监控已启动"
echo "📊 日志文件: $LOG_FILE"
echo "⏱️  采样间隔: 60秒"
echo ""

while true; do
    # 获取Python进程ID
    PID=$(pgrep -f "python.*main.py.*monitor")

    if [ -n "$PID" ]; then
        TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

        # CPU和内存使用
        CPU=$(ps -p $PID -o %cpu= | tr -d ' ')
        MEM_KB=$(ps -p $PID -o rss= | tr -d ' ')
        MEM_MB=$((MEM_KB / 1024))

        # 线程数
        THREADS=$(ps -M -p $PID 2>/dev/null | wc -l)
        THREADS=$((THREADS - 1))

        # 文件描述符数量
        FD_COUNT=$(lsof -p $PID 2>/dev/null | wc -l)

        # SQLite连接数
        DB_CONN=$(lsof -p $PID 2>/dev/null | grep -c "\.db$")

        echo "$TIMESTAMP,$PID,$CPU,$MEM_MB,$THREADS,$FD_COUNT,$DB_CONN" >> "$LOG_FILE"

        # 实时输出到控制台
        echo "[$TIMESTAMP] PID=$PID | CPU=${CPU}% | MEM=${MEM_MB}MB | THREADS=$THREADS | FD=$FD_COUNT | DB=$DB_CONN"
    else
        TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
        echo "$TIMESTAMP,N/A,程序未运行" >> "$LOG_FILE"
        echo "[$TIMESTAMP] ⚠️  程序未运行"
    fi

    sleep 60  # 每分钟记录一次
done

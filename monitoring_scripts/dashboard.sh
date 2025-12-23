#!/bin/bash
# 实时监控仪表盘 - 显示系统运行状态

while true; do
    clear
    echo "=========================================="
    echo "  Hyperliquid 监控系统 - 实时仪表盘"
    echo "=========================================="
    echo ""

    PID=$(cat monitoring_logs/pid.txt 2>/dev/null)

    if [ -n "$PID" ] && kill -0 $PID 2>/dev/null; then
        echo "✅ 主程序运行中 | PID: $PID"
        echo ""

        # CPU和内存
        echo "📊 资源使用:"
        ps -p $PID -o %cpu,%mem,rss,vsz,etime 2>/dev/null | tail -n 1 | \
            awk '{printf "  CPU: %s%% | 内存: %s%% | RSS: %dMB | VSZ: %dMB | 运行时间: %s\n", $1, $2, $3/1024, $4/1024, $5}'

        # 线程数
        THREADS=$(ps -M -p $PID 2>/dev/null | wc -l)
        THREADS=$((THREADS - 1))
        echo "  线程数: $THREADS"

        # 数据库连接
        DB_CONN=$(lsof -p $PID 2>/dev/null | grep -c "\.db$")
        echo "  数据库连接数: $DB_CONN"
        echo ""

        # 最新性能统计
        echo "📈 性能统计 (最近5分钟):"
        if [ -f "monitoring_logs/performance_stats.log" ]; then
            tail -n 1 monitoring_logs/performance_stats.log 2>/dev/null | \
                awk -F',' '{printf "  分析: %s币种 | 错误: %s | 平均耗时: %ss | 缓存命中率: %s%% | 告警: %s\n", $2, $3, $4, $5, $7}'
        else
            echo "  等待数据..."
        fi
        echo ""

        # 最新日志
        echo "📝 最新日志 (最后5条):"
        if [ -f "monitoring_logs/analyzer.log" ]; then
            tail -n 5 monitoring_logs/analyzer.log | sed 's/^/  /'
        else
            echo "  日志文件不存在"
        fi
        echo ""

    else
        echo "❌ 主程序未运行"
        echo ""
        echo "启动命令:"
        echo "  nohup uv run python main.py --mode=monitor --interval=1800 \\"
        echo "    > monitoring_logs/analyzer.log 2>&1 &"
        echo "  echo \$! > monitoring_logs/pid.txt"
        echo ""
    fi

    echo "=========================================="
    echo "按 Ctrl+C 退出 | 刷新间隔: 10秒"
    echo "=========================================="

    sleep 10
done

#!/bin/bash
# 停止所有监控进程并生成报告

echo "============================================"
echo "  停止监控并生成报告"
echo "============================================"
echo ""

# 1. 优雅停止主程序
echo "🛑 停止主程序..."
if [ -f "monitoring_logs/pid.txt" ]; then
    MAIN_PID=$(cat monitoring_logs/pid.txt)
    if kill -0 $MAIN_PID 2>/dev/null; then
        kill -SIGINT $MAIN_PID
        echo "   发送停止信号到 PID: $MAIN_PID"

        # 等待程序关闭（最多60秒）
        for i in {1..60}; do
            if ! kill -0 $MAIN_PID 2>/dev/null; then
                echo "✅ 主程序已优雅关闭 | 耗时: ${i}秒"
                break
            fi
            sleep 1
        done

        # 如果还未关闭，强制kill
        if kill -0 $MAIN_PID 2>/dev/null; then
            echo "⚠️ 主程序未在60秒内关闭，强制终止"
            kill -9 $MAIN_PID
        fi
    else
        echo "⚠️ 主程序已停止"
    fi
else
    echo "⚠️ 未找到主程序PID文件"
fi

# 2. 停止资源监控
echo ""
echo "🛑 停止资源监控..."
if [ -f "monitoring_logs/resource_monitor.pid" ]; then
    RESOURCE_PID=$(cat monitoring_logs/resource_monitor.pid)
    if kill -0 $RESOURCE_PID 2>/dev/null; then
        kill $RESOURCE_PID
        echo "✅ 资源监控已停止"
    fi
fi

# 3. 停止性能监控
echo ""
echo "🛑 停止性能监控..."
if [ -f "monitoring_logs/performance_monitor.pid" ]; then
    PERF_PID=$(cat monitoring_logs/performance_monitor.pid)
    if kill -0 $PERF_PID 2>/dev/null; then
        kill $PERF_PID
        echo "✅ 性能监控已停止"
    fi
fi

# 等待进程完全退出
sleep 3

# 4. 验证所有进程已停止
echo ""
echo "🔍 验证进程状态..."
RUNNING=$(ps aux | grep -E "(main.py|resource_monitor|performance_monitor)" | grep -v grep | wc -l)
if [ $RUNNING -eq 0 ]; then
    echo "✅ 所有监控进程已完全停止"
else
    echo "⚠️ 还有 $RUNNING 个进程未停止"
    ps aux | grep -E "(main.py|resource_monitor|performance_monitor)" | grep -v grep
fi

# 5. 生成分析报告
echo ""
echo "📊 生成分析报告..."

# 生成资源报告
if [ -f "monitoring_scripts/analyze_resources.py" ]; then
    uv run python monitoring_scripts/analyze_resources.py > monitoring_logs/resource_report.txt 2>&1
    echo "✅ 资源使用报告: monitoring_logs/resource_report.txt"
fi

# 生成性能报告
if [ -f "monitoring_scripts/analyze_performance.py" ]; then
    uv run python monitoring_scripts/analyze_performance.py > monitoring_logs/performance_report.txt 2>&1
    echo "✅ 性能分析报告: monitoring_logs/performance_report.txt"
fi

# 6. 显示报告摘要
echo ""
echo "============================================"
echo "  监控已停止，报告已生成"
echo "============================================"
echo ""
echo "📁 日志文件:"
echo "   - monitoring_logs/analyzer.log"
echo "   - monitoring_logs/resources_*.log"
echo "   - monitoring_logs/performance_stats.log"
echo ""
echo "📊 分析报告:"
echo "   - monitoring_logs/resource_report.txt"
echo "   - monitoring_logs/performance_report.txt"
echo ""
echo "🔍 查看报告:"
echo "   cat monitoring_logs/resource_report.txt"
echo "   cat monitoring_logs/performance_report.txt"
echo ""
echo "============================================"

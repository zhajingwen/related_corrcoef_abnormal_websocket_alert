#!/bin/bash
# 一键启动24小时监控验证

set -e  # 遇到错误立即退出

echo "============================================"
echo "  Hyperliquid 24小时监控验证 - 启动脚本"
echo "============================================"
echo ""

# 检查目录
if [ ! -d "monitoring_logs" ]; then
    mkdir -p monitoring_logs
    echo "✅ 创建监控日志目录"
fi

# 清理旧的PID文件
rm -f monitoring_logs/*.pid monitoring_logs/pid.txt
echo "✅ 清理旧的PID文件"

# 1. 启动主程序
echo ""
echo "🚀 启动主程序..."
nohup uv run python main.py \
    --mode=monitor \
    --interval=1800 \
    --timeframes=5m \
    --periods=1d,7d \
    > monitoring_logs/analyzer.log 2>&1 &

MAIN_PID=$!
echo $MAIN_PID > monitoring_logs/pid.txt
echo "✅ 主程序已启动 | PID: $MAIN_PID"

# 等待程序初始化
sleep 3

# 检查主程序是否运行
if ! kill -0 $MAIN_PID 2>/dev/null; then
    echo "❌ 主程序启动失败，请查看日志: monitoring_logs/analyzer.log"
    exit 1
fi

# 2. 启动资源监控
echo ""
echo "📊 启动资源监控..."
chmod +x monitoring_scripts/resource_monitor.sh
nohup ./monitoring_scripts/resource_monitor.sh > monitoring_logs/resource_monitor.log 2>&1 &
echo $! > monitoring_logs/resource_monitor.pid
echo "✅ 资源监控已启动 | PID: $(cat monitoring_logs/resource_monitor.pid)"

# 3. 启动性能监控
echo ""
echo "📈 启动性能监控..."
nohup uv run python monitoring_scripts/performance_monitor.py > monitoring_logs/performance_monitor.log 2>&1 &
echo $! > monitoring_logs/performance_monitor.pid
echo "✅ 性能监控已启动 | PID: $(cat monitoring_logs/performance_monitor.pid)"

# 等待所有进程初始化
sleep 2

# 4. 验证所有进程
echo ""
echo "🔍 验证进程状态..."
ALL_OK=true

if ! kill -0 $MAIN_PID 2>/dev/null; then
    echo "❌ 主程序未运行"
    ALL_OK=false
else
    echo "✅ 主程序运行正常 (PID: $MAIN_PID)"
fi

if ! kill -0 $(cat monitoring_logs/resource_monitor.pid) 2>/dev/null; then
    echo "❌ 资源监控未运行"
    ALL_OK=false
else
    echo "✅ 资源监控运行正常 (PID: $(cat monitoring_logs/resource_monitor.pid))"
fi

if ! kill -0 $(cat monitoring_logs/performance_monitor.pid) 2>/dev/null; then
    echo "❌ 性能监控未运行"
    ALL_OK=false
else
    echo "✅ 性能监控运行正常 (PID: $(cat monitoring_logs/performance_monitor.pid))"
fi

# 5. 显示启动信息
echo ""
echo "============================================"
if [ "$ALL_OK" = true ]; then
    echo "✅ 所有监控进程已成功启动"
    echo ""
    echo "📋 查看实时仪表盘:"
    echo "   ./monitoring_scripts/dashboard.sh"
    echo ""
    echo "📝 查看日志:"
    echo "   tail -f monitoring_logs/analyzer.log"
    echo ""
    echo "🛑 停止监控:"
    echo "   ./monitoring_scripts/stop_monitoring.sh"
    echo ""
    echo "⏰ 验证将运行24小时，请设置以下检查点:"
    echo "   - 4小时: 第一次检查"
    echo "   - 8小时: 第二次检查"
    echo "   - 12小时: 优雅关闭测试"
    echo "   - 16小时: 第三次检查"
    echo "   - 20小时: 第四次检查"
    echo "   - 24小时: 最终检查和报告生成"
else
    echo "❌ 部分进程启动失败，请检查日志"
fi
echo "============================================"

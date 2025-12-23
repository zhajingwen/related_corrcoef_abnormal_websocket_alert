#!/bin/bash
# macOS系统通知提醒脚本

CHECK_4H=$1
CHECK_8H=$2
CHECK_12H=$3
CHECK_16H=$4
CHECK_20H=$5
CHECK_24H=$6

echo "✅ 系统通知提醒已启动（后台运行）"
echo "   PID: $$"
echo $$ > monitoring_logs/notification_reminder.pid

# 函数：发送macOS通知
send_notification() {
    local title=$1
    local message=$2
    osascript -e "display notification \"$message\" with title \"$title\" sound name \"Glass\""
}

# 函数：等待到指定时间并发送通知
wait_and_notify() {
    local target_time=$1
    local title=$2
    local message=$3
    local command=$4

    local now=$(date +%s)
    local wait_time=$((target_time - now))

    if [ $wait_time -gt 0 ]; then
        echo "⏰ 定时通知: $title - $(date -r $target_time '+%m/%d %H:%M')"
        sleep $wait_time
        send_notification "$title" "$message"

        # 如果有命令，显示提示
        if [ -n "$command" ]; then
            sleep 5
            send_notification "建议操作" "$command"
        fi
    fi
}

# 设置各检查点通知
wait_and_notify $CHECK_4H \
    "🔔 检查点1 - 4小时" \
    "请检查监控状态：查看资源使用和性能指标" \
    "执行：./monitoring_scripts/dashboard.sh"

wait_and_notify $CHECK_8H \
    "🔔 检查点2 - 8小时" \
    "请检查监控状态：验证缓存命中率和错误率" \
    "执行：./monitoring_scripts/dashboard.sh"

wait_and_notify $CHECK_12H \
    "⭐ 检查点3 - 12小时（重要）" \
    "优雅关闭测试：发送停止信号并观察关闭过程" \
    "执行：kill -SIGINT \$(cat monitoring_logs/pid.txt)"

wait_and_notify $CHECK_16H \
    "🔔 检查点4 - 16小时" \
    "请检查监控状态：重启后运行是否正常" \
    "执行：./monitoring_scripts/dashboard.sh"

wait_and_notify $CHECK_20H \
    "🔔 检查点5 - 20小时" \
    "请检查监控状态：最后一次常规检查" \
    "执行：./monitoring_scripts/dashboard.sh"

wait_and_notify $CHECK_24H \
    "🎉 最终检查 - 24小时完成" \
    "停止监控并生成报告" \
    "执行：./monitoring_scripts/stop_monitoring.sh"

# 清理PID文件
rm -f monitoring_logs/notification_reminder.pid

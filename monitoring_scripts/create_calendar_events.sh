#!/bin/bash
# 创建macOS日历事件

CHECK_4H=$1
CHECK_8H=$2
CHECK_12H=$3
CHECK_16H=$4
CHECK_20H=$5
CHECK_24H=$6

echo "📅 创建日历事件..."

# 使用AppleScript创建日历事件
create_event() {
    local event_date=$1
    local title=$2
    local notes=$3

    local date_str=$(date -r $event_date '+%m/%d/%Y %H:%M:%S')

    osascript <<EOF
tell application "Calendar"
    tell calendar "Home"
        set newEvent to make new event with properties {summary:"$title", start date:date "$date_str", end date:date "$date_str" + 15 * minutes, description:"$notes"}
    end tell
end tell
EOF
}

create_event $CHECK_4H \
    "🔔 监控检查点1 (4小时)" \
    "检查资源使用和性能指标\n执行：cd ~/Documents/related_corrcoef_abnormal_websocket_alert && ./monitoring_scripts/dashboard.sh"

create_event $CHECK_8H \
    "🔔 监控检查点2 (8小时)" \
    "验证缓存命中率和错误率\n执行：cd ~/Documents/related_corrcoef_abnormal_websocket_alert && ./monitoring_scripts/dashboard.sh"

create_event $CHECK_12H \
    "⭐ 监控检查点3 (12小时) - 优雅关闭测试" \
    "重要：测试优雅关闭机制\n1. 执行：kill -SIGINT \$(cat monitoring_logs/pid.txt)\n2. 观察日志：tail -f monitoring_logs/analyzer.log\n3. 验证关闭：60秒内应该完成\n4. 重启：./monitoring_scripts/start_monitoring.sh"

create_event $CHECK_16H \
    "🔔 监控检查点4 (16小时)" \
    "检查重启后运行状态\n执行：cd ~/Documents/related_corrcoef_abnormal_websocket_alert && ./monitoring_scripts/dashboard.sh"

create_event $CHECK_20H \
    "🔔 监控检查点5 (20小时)" \
    "最后一次常规检查\n执行：cd ~/Documents/related_corrcoef_abnormal_websocket_alert && ./monitoring_scripts/dashboard.sh"

create_event $CHECK_24H \
    "🎉 监控最终检查 (24小时)" \
    "停止监控并生成报告\n执行：cd ~/Documents/related_corrcoef_abnormal_websocket_alert && ./monitoring_scripts/stop_monitoring.sh\n查看报告：cat monitoring_logs/resource_report.txt && cat monitoring_logs/performance_report.txt"

echo "✅ 日历事件已创建"
echo "   打开「日历」app查看所有提醒"
open -a Calendar

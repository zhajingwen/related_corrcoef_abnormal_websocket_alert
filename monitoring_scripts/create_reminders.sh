#!/bin/bash
# 创建macOS提醒事项

CHECK_4H=$1
CHECK_8H=$2
CHECK_12H=$3
CHECK_16H=$4
CHECK_20H=$5
CHECK_24H=$6

echo "📝 创建提醒事项..."

# 使用AppleScript创建提醒事项
create_reminder() {
    local due_date=$1
    local title=$2
    local notes=$3

    local date_str=$(date -r $due_date '+%m/%d/%Y %H:%M:%S')

    osascript <<EOF
tell application "Reminders"
    tell list "Reminders"
        set newReminder to make new reminder with properties {name:"$title", due date:date "$date_str", body:"$notes"}
        set remind me date of newReminder to date "$date_str"
    end tell
end tell
EOF
}

create_reminder $CHECK_4H \
    "🔔 监控检查点1 (4小时)" \
    "检查命令：cd ~/Documents/related_corrcoef_abnormal_websocket_alert && ./monitoring_scripts/dashboard.sh"

create_reminder $CHECK_8H \
    "🔔 监控检查点2 (8小时)" \
    "检查命令：cd ~/Documents/related_corrcoef_abnormal_websocket_alert && ./monitoring_scripts/dashboard.sh"

create_reminder $CHECK_12H \
    "⭐ 监控检查点3 (12小时) - 优雅关闭测试 [重要]" \
    "1. 停止：kill -SIGINT \$(cat monitoring_logs/pid.txt)\n2. 观察：tail -f monitoring_logs/analyzer.log\n3. 重启：./monitoring_scripts/start_monitoring.sh"

create_reminder $CHECK_16H \
    "🔔 监控检查点4 (16小时)" \
    "检查命令：cd ~/Documents/related_corrcoef_abnormal_websocket_alert && ./monitoring_scripts/dashboard.sh"

create_reminder $CHECK_20H \
    "🔔 监控检查点5 (20小时)" \
    "检查命令：cd ~/Documents/related_corrcoef_abnormal_websocket_alert && ./monitoring_scripts/dashboard.sh"

create_reminder $CHECK_24H \
    "🎉 监控最终检查 (24小时) [重要]" \
    "停止并生成报告：./monitoring_scripts/stop_monitoring.sh\n查看报告：cat monitoring_logs/*.txt"

echo "✅ 提醒事项已创建"
echo "   打开「提醒事项」app查看所有提醒"
open -a Reminders

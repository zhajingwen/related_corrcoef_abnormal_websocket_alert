#!/bin/bash
# 自动设置24小时监控检查点提醒脚本（macOS）

echo "============================================"
echo "  24小时监控检查点提醒设置工具"
echo "============================================"
echo ""

# 检查是否已启动监控
if [ ! -f "monitoring_logs/pid.txt" ]; then
    echo "⚠️  警告: 监控尚未启动"
    echo "   请先执行: ./monitoring_scripts/start_monitoring.sh"
    echo ""
    read -p "现在启动监控吗？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./monitoring_scripts/start_monitoring.sh
    else
        echo "❌ 已取消"
        exit 1
    fi
fi

# 获取启动时间
START_TIME=$(date +%s)
echo "✅ 监控已启动"
echo "📅 启动时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 计算各检查点时间
CHECK_4H=$((START_TIME + 4 * 3600))
CHECK_8H=$((START_TIME + 8 * 3600))
CHECK_12H=$((START_TIME + 12 * 3600))
CHECK_16H=$((START_TIME + 16 * 3600))
CHECK_20H=$((START_TIME + 20 * 3600))
CHECK_24H=$((START_TIME + 24 * 3600))

echo "⏰ 检查点时间表:"
echo "  ✅ 启动验证: $(date '+%m/%d %H:%M')"
echo "  📍 检查点1 (4小时):  $(date -r $CHECK_4H '+%m/%d %H:%M')"
echo "  📍 检查点2 (8小时):  $(date -r $CHECK_8H '+%m/%d %H:%M')"
echo "  📍 检查点3 (12小时): $(date -r $CHECK_12H '+%m/%d %H:%M') ⭐ 优雅关闭测试"
echo "  📍 检查点4 (16小时): $(date -r $CHECK_16H '+%m/%d %H:%M')"
echo "  📍 检查点5 (20小时): $(date -r $CHECK_20H '+%m/%d %H:%M')"
echo "  📍 最终检查 (24小时): $(date -r $CHECK_24H '+%m/%d %H:%M') ⭐ 生成报告"
echo ""

# 提供多种提醒设置方法
echo "============================================"
echo "  选择提醒设置方法"
echo "============================================"
echo ""
echo "1. 使用macOS系统通知 (推荐)"
echo "2. 使用macOS日历"
echo "3. 使用macOS提醒事项"
echo "4. 生成检查命令清单"
echo "5. 全部设置"
echo ""

read -p "请选择 (1-5): " -n 1 -r
echo ""
echo ""

case $REPLY in
    1)
        echo "📱 设置系统通知..."
        chmod +x monitoring_scripts/notification_reminders.sh
        ./monitoring_scripts/notification_reminders.sh $CHECK_4H $CHECK_8H $CHECK_12H $CHECK_16H $CHECK_20H $CHECK_24H &
        echo "✅ 系统通知已设置"
        ;;
    2)
        echo "📅 打开日历设置..."
        ./monitoring_scripts/create_calendar_events.sh $CHECK_4H $CHECK_8H $CHECK_12H $CHECK_16H $CHECK_20H $CHECK_24H
        ;;
    3)
        echo "📝 打开提醒事项设置..."
        ./monitoring_scripts/create_reminders.sh $CHECK_4H $CHECK_8H $CHECK_12H $CHECK_16H $CHECK_20H $CHECK_24H
        ;;
    4)
        echo "📋 生成检查命令清单..."
        ./monitoring_scripts/create_checklist.sh $CHECK_4H $CHECK_8H $CHECK_12H $CHECK_16H $CHECK_20H $CHECK_24H
        ;;
    5)
        echo "✅ 设置所有提醒..."
        ./monitoring_scripts/notification_reminders.sh $CHECK_4H $CHECK_8H $CHECK_12H $CHECK_16H $CHECK_20H $CHECK_24H &
        ./monitoring_scripts/create_calendar_events.sh $CHECK_4H $CHECK_8H $CHECK_12H $CHECK_16H $CHECK_20H $CHECK_24H
        ./monitoring_scripts/create_checklist.sh $CHECK_4H $CHECK_8H $CHECK_12H $CHECK_16H $CHECK_20H $CHECK_24H
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "============================================"
echo "✅ 提醒设置完成"
echo "============================================"
echo ""
echo "💡 提示:"
echo "  - 系统通知会自动弹出提醒"
echo "  - 检查时执行: ./monitoring_scripts/dashboard.sh"
echo "  - 查看详细清单: cat monitoring_logs/checklist.txt"
echo ""

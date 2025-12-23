#!/bin/bash
# 生成检查清单文件

CHECK_4H=$1
CHECK_8H=$2
CHECK_12H=$3
CHECK_16H=$4
CHECK_20H=$5
CHECK_24H=$6

CHECKLIST_FILE="monitoring_logs/checklist.txt"

cat > $CHECKLIST_FILE <<EOF
================================================================================
  Hyperliquid 24小时监控验证 - 检查清单
================================================================================

启动时间: $(date '+%Y-%m-%d %H:%M:%S')

================================================================================
  检查点时间表
================================================================================

✅ 启动验证 (0小时)
   时间: $(date '+%Y-%m-%d %H:%M')
   状态: 已完成
   操作: 监控已启动

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 检查点1 (4小时后)
   时间: $(date -r $CHECK_4H '+%Y-%m-%d %H:%M')
   重要性: ⭐⭐

   检查内容:
   □ 查看资源使用趋势
   □ 检查内存增长 (预期 <5%)
   □ 检查错误数量 (预期 <10个)
   □ 验证分析速度 (预期 <0.3秒)

   执行命令:
   ./monitoring_scripts/dashboard.sh

   或手动检查:
   tail -n 20 monitoring_logs/resources_*.log
   tail -n 20 monitoring_logs/performance_stats.log
   grep ERROR monitoring_logs/analyzer.log | wc -l

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 检查点2 (8小时后)
   时间: $(date -r $CHECK_8H '+%Y-%m-%d %H:%M')
   重要性: ⭐

   检查内容:
   □ 验证所有进程正常运行
   □ 检查缓存命中率 (预期 >80%)
   □ 检查是否有异常错误

   执行命令:
   ./monitoring_scripts/dashboard.sh

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⭐ 检查点3 (12小时后) - 优雅关闭测试 [最重要]
   时间: $(date -r $CHECK_12H '+%Y-%m-%d %H:%M')
   重要性: ⭐⭐⭐⭐⭐

   测试步骤:
   □ 1. 发送停止信号
      kill -SIGINT \$(cat monitoring_logs/pid.txt)

   □ 2. 观察关闭过程 (打开新终端)
      tail -f monitoring_logs/analyzer.log

      应该看到:
      - "检测到停止信号"
      - "已分析 X/224 个币种"
      - "清理资源..."
      - "数据库连接已关闭"

   □ 3. 验证关闭完成 (应在60秒内)
      for i in {1..60}; do
        if ! kill -0 \$(cat monitoring_logs/pid.txt) 2>/dev/null; then
          echo "✅ 程序已优雅关闭 | 耗时: \${i}秒"
          break
        fi
        sleep 1
      done

   □ 4. 检查资源清理
      lsof -p \$(cat monitoring_logs/pid.txt) 2>/dev/null || echo "✅ 资源已清理"

   □ 5. 重新启动继续测试
      ./monitoring_scripts/start_monitoring.sh

   预期结果:
   ✅ 60秒内优雅关闭
   ✅ 日志显示"检测到停止信号"
   ✅ 数据库连接已关闭
   ✅ 所有资源已释放

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 检查点4 (16小时后)
   时间: $(date -r $CHECK_16H '+%Y-%m-%d %H:%M')
   重要性: ⭐

   检查内容:
   □ 验证重启后程序正常运行
   □ 检查是否有新错误
   □ 查看性能是否稳定

   执行命令:
   ./monitoring_scripts/dashboard.sh

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 检查点5 (20小时后)
   时间: $(date -r $CHECK_20H '+%Y-%m-%d %H:%M')
   重要性: ⭐

   检查内容:
   □ 最后一次常规检查
   □ 查看完整性能统计

   执行命令:
   ./monitoring_scripts/dashboard.sh
   tail -n 50 monitoring_logs/performance_stats.log

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎉 最终检查 (24小时后) [重要]
   时间: $(date -r $CHECK_24H '+%Y-%m-%d %H:%M')
   重要性: ⭐⭐⭐⭐

   操作步骤:
   □ 1. 停止所有监控并生成报告
      ./monitoring_scripts/stop_monitoring.sh

   □ 2. 查看资源使用报告
      cat monitoring_logs/resource_report.txt

      预期结果:
      ✅ 内存增长 <10%
      ✅ 连接稳定 (标准差<2)
      ✅ 资源使用合理

   □ 3. 查看性能分析报告
      cat monitoring_logs/performance_report.txt

      预期结果:
      ✅ 错误率 <1%
      ✅ 平均耗时 <0.5秒
      ✅ 缓存命中率 >80%

   □ 4. 验证完成
      如果所有指标都通过，系统验证完成！

================================================================================
  成功标准
================================================================================

资源使用:
  ✅ 内存增长 <10%
  ✅ 数据库连接稳定 (标准差<2, 最大值≤10)
  ✅ 峰值内存 <1000MB
  ✅ 平均CPU <50%

性能指标:
  ✅ 错误率 <1%
  ✅ 平均分析耗时 <0.5秒/币种
  ✅ 缓存命中率 >80%
  ✅ 告警率 <10%

优雅关闭:
  ✅ 60秒内正常退出
  ✅ 资源完全清理
  ✅ 日志记录完整

================================================================================
  快速命令
================================================================================

# 查看实时仪表盘
./monitoring_scripts/dashboard.sh

# 查看主程序日志
tail -f monitoring_logs/analyzer.log

# 查看进程状态
ps -p \$(cat monitoring_logs/pid.txt) -f

# 查看资源趋势
tail -n 50 monitoring_logs/resources_*.log

# 查看性能统计
tail -n 50 monitoring_logs/performance_stats.log

# 检查错误
grep ERROR monitoring_logs/analyzer.log | tail -n 20

# 优雅停止
kill -SIGINT \$(cat monitoring_logs/pid.txt)

# 重新启动
./monitoring_scripts/start_monitoring.sh

# 完全停止并生成报告
./monitoring_scripts/stop_monitoring.sh

================================================================================
  故障处理
================================================================================

程序意外退出:
  1. 查看日志: tail -n 50 monitoring_logs/analyzer.log
  2. 重新启动: ./monitoring_scripts/start_monitoring.sh

监控脚本停止:
  1. 检查进程: ps aux | grep monitor
  2. 重启资源监控: nohup ./monitoring_scripts/resource_monitor.sh &
  3. 重启性能监控: nohup uv run python monitoring_scripts/performance_monitor.py &

磁盘空间不足:
  1. 检查大小: du -sh monitoring_logs/*
  2. 压缩日志: gzip monitoring_logs/analyzer.log

================================================================================

💡 提示: 可以随时查看本清单
   cat monitoring_logs/checklist.txt

EOF

echo "✅ 检查清单已生成: $CHECKLIST_FILE"
echo ""
echo "查看清单:"
echo "  cat $CHECKLIST_FILE"
echo ""
echo "或在检查时使用:"
echo "  less $CHECKLIST_FILE  # 按q退出"

# 24小时监控验证 - 快速入门指南

## 🚀 一键启动（最简单方式）

```bash
# 1. 进入项目目录
cd /Users/test/Documents/related_corrcoef_abnormal_websocket_alert

# 2. 一键启动所有监控
./monitoring_scripts/start_monitoring.sh

# 3. 查看实时仪表盘（可选）
./monitoring_scripts/dashboard.sh
```

就这么简单！系统会自动启动：
- ✅ 主程序（监控模式，每30分钟分析一次）
- ✅ 资源监控（每分钟记录CPU、内存、连接数等）
- ✅ 性能监控（每5分钟统计分析速度、错误率等）

---

## 📊 查看监控状态

### 方式1: 实时仪表盘（推荐）
```bash
./monitoring_scripts/dashboard.sh
```

显示内容：
```
==========================================
  Hyperliquid 监控系统 - 实时仪表盘
==========================================

✅ 主程序运行中 | PID: 12345

📊 资源使用:
  CPU: 12.3% | 内存: 2.1% | RSS: 245MB | 运行时间: 02:15:30
  线程数: 8
  数据库连接数: 3

📈 性能统计 (最近5分钟):
  分析: 45币种 | 错误: 0 | 平均耗时: 0.185s | 缓存命中率: 92.3% | 告警: 2

📝 最新日志 (最后5条):
  2025-12-23 16:30:15 - analyzer - INFO - 分析完成 | ETH/USDC:USDC | 耗时: 0.178秒
  ...
```

### 方式2: 查看原始日志
```bash
# 主程序日志（实时）
tail -f monitoring_logs/analyzer.log

# 资源监控日志
tail -f monitoring_logs/resources_*.log

# 性能统计日志
tail -f monitoring_logs/performance_stats.log
```

### 方式3: 检查进程状态
```bash
# 查看所有监控进程
ps aux | grep -E "(main.py|resource_monitor|performance_monitor)" | grep -v grep

# 查看主程序详情
ps -p $(cat monitoring_logs/pid.txt) -f
```

---

## ⏰ 24小时检查点

设置以下时间点的提醒，手动检查系统状态：

### ✅ 检查点1: 启动后4小时
```bash
# 查看资源趋势
tail -n 20 monitoring_logs/resources_*.log

# 查看性能统计
tail -n 20 monitoring_logs/performance_stats.log

# 检查错误（应该很少或没有）
grep ERROR monitoring_logs/analyzer.log | wc -l
```

**预期结果**:
- 内存增长 <5%
- 错误数 <10个
- 平均分析耗时 <0.3秒

### ✅ 检查点2: 启动后8小时
```bash
# 使用仪表盘快速检查
./monitoring_scripts/dashboard.sh
```

**预期结果**:
- 所有进程正常运行
- 缓存命中率 >80%
- 无异常错误

### ✅ 检查点3: 启动后12小时（优雅关闭测试）

**这是最重要的测试点！**

```bash
# 1. 发送停止信号
kill -SIGINT $(cat monitoring_logs/pid.txt)

# 2. 观察关闭过程（应该在60秒内完成）
tail -f monitoring_logs/analyzer.log
# 应该看到: "检测到停止信号" "清理资源" "已关闭"

# 3. 验证进程已完全退出
ps -p $(cat monitoring_logs/pid.txt) 2>/dev/null || echo "✅ 进程已退出"

# 4. 检查资源清理
lsof -p $(cat monitoring_logs/pid.txt) 2>/dev/null || echo "✅ 资源已清理"

# 5. 重新启动继续测试
./monitoring_scripts/start_monitoring.sh
```

**预期结果**:
- ✅ 程序在60秒内优雅关闭
- ✅ 日志显示"检测到停止信号"
- ✅ 数据库连接已关闭
- ✅ 所有资源已释放

### ✅ 检查点4: 启动后16小时
```bash
# 快速检查
./monitoring_scripts/dashboard.sh
```

### ✅ 检查点5: 启动后20小时
```bash
# 查看完整统计
tail -n 50 monitoring_logs/performance_stats.log
```

### ✅ 检查点6: 启动后24小时（最终检查）

**执行完整停止和分析流程！**

```bash
# 1. 停止所有监控并生成报告
./monitoring_scripts/stop_monitoring.sh

# 2. 查看资源使用报告
cat monitoring_logs/resource_report.txt

# 3. 查看性能分析报告
cat monitoring_logs/performance_report.txt
```

---

## 🛑 停止监控

### 正常停止（24小时后）
```bash
# 自动停止所有进程并生成报告
./monitoring_scripts/stop_monitoring.sh
```

这会：
1. 优雅停止主程序（最多等待60秒）
2. 停止资源监控
3. 停止性能监控
4. 自动生成分析报告
5. 显示报告摘要

### 紧急停止
```bash
# 如果需要立即停止
kill -9 $(cat monitoring_logs/pid.txt)
kill -9 $(cat monitoring_logs/resource_monitor.pid)
kill -9 $(cat monitoring_logs/performance_monitor.pid)
```

---

## 📋 成功标准

24小时监控结束后，查看报告应该显示：

### 资源使用报告（resource_report.txt）
```
✅ 验证结果:
  内存泄漏检测: ✅ 通过 (+5.2% < 10%)
  连接稳定性: ✅ 通过 (标准差: 0.8 | 最大值: 5)
  资源使用: ✅ 合理 (峰值内存: 280MB | 平均CPU: 15.3%)
```

### 性能分析报告（performance_report.txt）
```
✅ 验证结果:
  错误率检测: ✅ 通过 (0.23% | 目标: <1%)
  性能检测: ✅ 通过 (0.182s | 目标: <0.5s)
  缓存效率: ✅ 通过 (88.5% | 目标: >80%)
  告警合理性: ✅ 正常 (2.1% | 建议: <10%)
```

如果所有指标都显示 ✅，恭喜！系统已通过24小时稳定性测试！

---

## 🔍 常见问题

### Q1: 如何知道监控是否在运行？
```bash
# 方法1: 查看仪表盘
./monitoring_scripts/dashboard.sh

# 方法2: 检查进程
ps aux | grep "main.py" | grep -v grep

# 方法3: 查看日志更新时间
ls -lt monitoring_logs/
```

### Q2: 程序意外退出了怎么办？
```bash
# 1. 查看退出原因
tail -n 50 monitoring_logs/analyzer.log

# 2. 重新启动
./monitoring_scripts/start_monitoring.sh

# 3. 如果反复退出，查看系统日志
# macOS
log show --predicate 'process == "Python"' --last 1h
```

### Q3: 如何查看当前已运行多久？
```bash
# 查看主程序运行时间
ps -p $(cat monitoring_logs/pid.txt) -o etime=

# 或使用仪表盘
./monitoring_scripts/dashboard.sh
```

### Q4: 可以在监控过程中查看仪表盘吗？
```bash
# 可以！仪表盘不会影响监控，随时可以查看
./monitoring_scripts/dashboard.sh

# 按 Ctrl+C 退出仪表盘（不会停止监控）
```

### Q5: 磁盘空间不足怎么办？
```bash
# 查看日志大小
du -sh monitoring_logs/*

# 如果analyzer.log太大，可以压缩
gzip monitoring_logs/analyzer.log
# 程序会自动创建新的analyzer.log

# 或者删除旧的资源监控日志（保留最新的）
rm monitoring_logs/resources_202*.log
```

---

## 💡 优化建议

### 提高监控精度
如果想要更精细的监控，可以手动调整：

```bash
# 编辑资源监控脚本，改为每30秒记录一次
vim monitoring_scripts/resource_monitor.sh
# 将 sleep 60 改为 sleep 30

# 编辑性能监控脚本，改为每2分钟统计一次
vim monitoring_scripts/performance_monitor.py
# 将 time.sleep(300) 改为 time.sleep(120)
```

### 减少资源占用
如果监控本身占用太多资源：

```bash
# 编辑资源监控脚本，改为每5分钟记录一次
vim monitoring_scripts/resource_monitor.sh
# 将 sleep 60 改为 sleep 300

# 这样可以减少IO操作
```

---

## 📱 设置提醒

建议在手机/电脑上设置以下提醒：

```
启动后 4小时  → 检查点1
启动后 8小时  → 检查点2
启动后 12小时 → 优雅关闭测试（重要！）
启动后 16小时 → 检查点4
启动后 20小时 → 检查点5
启动后 24小时 → 最终检查和报告生成
```

---

## 🎯 快速命令参考

```bash
# 启动监控
./monitoring_scripts/start_monitoring.sh

# 查看仪表盘
./monitoring_scripts/dashboard.sh

# 查看主程序日志
tail -f monitoring_logs/analyzer.log

# 查看进程状态
ps -p $(cat monitoring_logs/pid.txt) -f

# 停止监控
./monitoring_scripts/stop_monitoring.sh

# 生成报告（如果已停止）
uv run python monitoring_scripts/analyze_resources.py
uv run python monitoring_scripts/analyze_performance.py
```

---

## ✅ 监控完成后

24小时监控完成后，你将获得：

1. **📊 资源使用报告** - 验证无内存泄漏、连接稳定
2. **📈 性能分析报告** - 验证分析速度、错误率、缓存效率
3. **📝 完整日志** - 可用于事后分析和问题排查
4. **✅ 部署信心** - 经过验证的生产环境部署准备

如果所有指标通过，就可以放心地长期运行系统了！

---

**文档版本**: v1.0
**创建时间**: 2025-12-23
**下一步**: 执行 `./monitoring_scripts/start_monitoring.sh` 开始验证！

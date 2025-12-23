# 检查点提醒设置指南

本指南教你如何设置24小时监控验证的6个检查点提醒。

---

## 🚀 方法1: 自动设置（最简单，推荐）

### 一键设置所有提醒

```bash
# 启动监控并自动设置提醒
./monitoring_scripts/start_monitoring.sh

# 然后运行提醒设置脚本
./monitoring_scripts/setup_reminders.sh
```

**会提供5种选择**:

1. **系统通知** (推荐) - 自动弹出通知，无需其他app
2. **日历** - 在macOS日历app中创建事件
3. **提醒事项** - 在macOS提醒事项app中创建任务
4. **检查清单** - 生成文本清单文件
5. **全部设置** - 同时设置上述所有方式

---

## 📱 方法2: 手动设置macOS提醒事项

### 步骤1: 打开提醒事项app
```bash
open -a Reminders
```

### 步骤2: 创建6个提醒

根据启动时间计算各检查点时间，然后手动创建：

#### 检查点1 (启动后4小时)
- **标题**: 🔔 监控检查点1 (4小时)
- **时间**: [启动时间 + 4小时]
- **提醒时间**: 检查时间前5分钟
- **备注**:
  ```
  检查命令:
  cd ~/Documents/related_corrcoef_abnormal_websocket_alert
  ./monitoring_scripts/dashboard.sh
  ```

#### 检查点2 (启动后8小时)
- **标题**: 🔔 监控检查点2 (8小时)
- **时间**: [启动时间 + 8小时]
- **提醒时间**: 检查时间前5分钟
- **备注**: 同上

#### 检查点3 (启动后12小时) ⭐ 最重要
- **标题**: ⭐ 监控检查点3 - 优雅关闭测试
- **时间**: [启动时间 + 12小时]
- **提醒时间**: 检查时间前5分钟
- **备注**:
  ```
  重要：优雅关闭测试
  1. 停止：kill -SIGINT $(cat monitoring_logs/pid.txt)
  2. 观察：tail -f monitoring_logs/analyzer.log
  3. 验证：60秒内应该完成
  4. 重启：./monitoring_scripts/start_monitoring.sh
  ```

#### 检查点4 (启动后16小时)
- **标题**: 🔔 监控检查点4 (16小时)
- **时间**: [启动时间 + 16小时]
- **备注**: 同检查点1

#### 检查点5 (启动后20小时)
- **标题**: 🔔 监控检查点5 (20小时)
- **时间**: [启动时间 + 20小时]
- **备注**: 同检查点1

#### 最终检查 (启动后24小时) ⭐ 重要
- **标题**: 🎉 监控最终检查 - 生成报告
- **时间**: [启动时间 + 24小时]
- **提醒时间**: 检查时间前5分钟
- **备注**:
  ```
  停止并生成报告:
  ./monitoring_scripts/stop_monitoring.sh

  查看报告:
  cat monitoring_logs/resource_report.txt
  cat monitoring_logs/performance_report.txt
  ```

---

## 📅 方法3: 手动设置macOS日历

### 步骤1: 打开日历app
```bash
open -a Calendar
```

### 步骤2: 创建6个日历事件

为每个检查点创建15分钟的事件，设置提前5分钟提醒。

**事件详情**参考"方法2"中的内容。

---

## ⏰ 方法4: 使用手机设置提醒

### iOS (iPhone)

1. 打开「提醒事项」app
2. 创建新提醒列表：「Hyperliquid监控」
3. 添加6个提醒，每个包含：
   - 标题
   - 时间
   - 备注（检查命令）

### Android

使用Google日历或提醒app，设置方式类似。

---

## 🔔 方法5: 使用第三方app

### 推荐app

**macOS/iOS**:
- **Due** - 持续提醒直到标记完成
- **Fantastical** - 强大的日历app
- **Things** - 任务管理app

**跨平台**:
- **Todoist** - 任务管理
- **Microsoft To Do** - 免费且强大
- **Google Calendar** - 与所有设备同步

---

## 📋 方法6: 打印或保存检查清单

### 生成检查清单文件

监控启动后会自动生成检查清单：

```bash
# 查看检查清单
cat monitoring_logs/checklist.txt

# 或使用less分页查看
less monitoring_logs/checklist.txt  # 按q退出

# 打印清单（如果有打印机）
lpr monitoring_logs/checklist.txt
```

### 将清单发送到手机

```bash
# 方法1: 通过AirDrop发送
# 在Finder中右键点击 monitoring_logs/checklist.txt → 共享 → AirDrop

# 方法2: 通过邮件发送给自己
# 在Finder中右键点击 monitoring_logs/checklist.txt → 共享 → 邮件
```

---

## 📊 时间计算示例

假设在 **2025-12-23 18:00** 启动监控：

| 检查点 | 时间 | 描述 |
|--------|------|------|
| 启动 | 12-23 18:00 | 启动验证 |
| 检查点1 | 12-23 22:00 | 4小时后 |
| 检查点2 | 12-24 02:00 | 8小时后 |
| 检查点3 | 12-24 06:00 | 12小时后 ⭐ 优雅关闭测试 |
| 检查点4 | 12-24 10:00 | 16小时后 |
| 检查点5 | 12-24 14:00 | 20小时后 |
| 最终检查 | 12-24 18:00 | 24小时后 ⭐ 生成报告 |

---

## 💡 实用技巧

### 技巧1: 使用闹钟app
在手机上设置6个闹钟，每个闹钟的名称包含检查内容。

### 技巧2: 设置重复提醒
如果担心错过，可以设置提前5分钟和准时两个提醒。

### 技巧3: 保持电脑唤醒
长时间监控建议：
```bash
# 防止Mac休眠（需要手动停止）
caffeinate -d
```

### 技巧4: 远程检查
如果不在电脑旁，可以：
- 使用SSH远程连接
- 查看日志文件（如果有云同步）
- 让朋友/同事帮忙检查

---

## ⚙️ 自动化选项（高级）

### 使用launchd定时任务

创建定时任务在检查点自动记录状态：

```bash
# 这个功能已内置在监控脚本中
# resource_monitor.sh 每分钟自动记录
# performance_monitor.py 每5分钟自动统计
```

### 使用cron（如果熟悉）

```bash
# 编辑crontab
crontab -e

# 添加定时任务（示例：每小时记录一次）
0 * * * * cd ~/Documents/related_corrcoef_abnormal_websocket_alert && ./monitoring_scripts/dashboard.sh >> monitoring_logs/auto_check.log 2>&1
```

---

## ✅ 验证提醒已设置

### 检查系统通知
```bash
# 查看后台通知进程
ps aux | grep notification_reminders

# 查看PID文件
cat monitoring_logs/notification_reminder.pid
```

### 检查日历/提醒事项
```bash
# 打开日历
open -a Calendar

# 打开提醒事项
open -a Reminders
```

### 检查清单文件
```bash
# 验证清单已生成
ls -lh monitoring_logs/checklist.txt

# 查看内容
head -n 50 monitoring_logs/checklist.txt
```

---

## 🆘 常见问题

### Q: 忘记设置提醒怎么办？
A: 随时可以运行：
```bash
./monitoring_scripts/setup_reminders.sh
```

### Q: 可以修改提醒时间吗？
A: 可以，在相应的app中编辑事件/提醒。

### Q: 系统通知不弹出怎么办？
A: 检查系统设置：
1. 系统设置 → 通知
2. 找到"脚本编辑器"或"终端"
3. 允许通知和横幅

### Q: 半夜2点的检查点怎么办？
A: 有几个选择：
1. 跳过深夜检查点（第二天早上查看日志）
2. 调整启动时间（例如早上6点启动）
3. 设置提醒但不一定要立即响应

---

## 📞 推荐设置组合

### 方案A: 最省心（推荐）
```bash
./monitoring_scripts/setup_reminders.sh
# 选择 "1" (系统通知) 或 "5" (全部设置)
```

### 方案B: 最可靠
- macOS提醒事项（主要）
- 手机提醒（备份）
- 检查清单（参考）

### 方案C: 最灵活
- 只生成检查清单
- 自己决定何时检查
- 适合已有自己的时间管理系统

---

## 🎯 下一步

1. **选择提醒方式** → 推荐使用自动设置脚本
2. **启动监控** → `./monitoring_scripts/start_monitoring.sh`
3. **设置提醒** → `./monitoring_scripts/setup_reminders.sh`
4. **等待提醒** → 在提醒时间查看仪表盘或执行检查命令

---

**文档版本**: v1.0
**创建时间**: 2025-12-23
**下一步**: 执行 `./monitoring_scripts/setup_reminders.sh`

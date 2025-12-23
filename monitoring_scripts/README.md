# 监控脚本说明

本目录包含24小时监控验证所需的所有脚本和工具。

## 📁 文件清单

### 启动/停止脚本
- **start_monitoring.sh** - 一键启动所有监控（推荐使用）
- **stop_monitoring.sh** - 停止所有监控并生成报告

### 监控脚本
- **resource_monitor.sh** - 资源监控（CPU、内存、连接数等）
- **performance_monitor.py** - 性能监控（分析速度、错误率等）
- **dashboard.sh** - 实时监控仪表盘

### 分析脚本
- **analyze_resources.py** - 资源使用分析报告生成
- **analyze_performance.py** - 性能分析报告生成

## 🚀 快速开始

```bash
# 1. 一键启动
./start_monitoring.sh

# 2. 查看实时状态
./dashboard.sh

# 3. 24小时后停止
./stop_monitoring.sh
```

## 📊 生成的日志文件

所有日志文件存储在 `../monitoring_logs/` 目录：

- `analyzer.log` - 主程序日志
- `resources_YYYYMMDD_HHMMSS.log` - 资源监控数据
- `performance_stats.log` - 性能统计数据
- `resource_report.txt` - 资源使用分析报告
- `performance_report.txt` - 性能分析报告
- `pid.txt` - 主程序进程ID
- `*.pid` - 监控脚本进程ID

## 📖 详细文档

请查看项目根目录的文档：
- `QUICK_START_24H_MONITORING.md` - 快速入门指南
- `24H_MONITORING_PLAN.md` - 完整监控方案

## ⚙️ 自定义配置

### 修改监控间隔
编辑 `start_monitoring.sh`，修改 `--interval` 参数：
```bash
--interval=1800  # 30分钟（默认）
--interval=3600  # 1小时
--interval=600   # 10分钟
```

### 修改时间周期
编辑 `start_monitoring.sh`，修改 `--timeframes` 和 `--periods` 参数：
```bash
--timeframes=5m        # 单个时间周期
--timeframes=1m,5m     # 多个时间周期
--periods=1d,7d        # 数据周期
```

### 修改资源监控频率
编辑 `resource_monitor.sh`，修改 sleep 值：
```bash
sleep 60   # 每分钟（默认）
sleep 300  # 每5分钟
```

### 修改性能统计频率
编辑 `performance_monitor.py`，修改 sleep 值：
```python
time.sleep(300)  # 每5分钟（默认）
time.sleep(600)  # 每10分钟
```

## 🆘 故障排除

### 脚本没有执行权限
```bash
chmod +x *.sh
```

### 找不到uv命令
```bash
# 确保已安装uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用系统Python
python3 代替 uv run python
```

### 进程无法停止
```bash
# 强制终止
kill -9 $(cat ../monitoring_logs/pid.txt)
kill -9 $(cat ../monitoring_logs/resource_monitor.pid)
kill -9 $(cat ../monitoring_logs/performance_monitor.pid)
```

## 📞 支持

遇到问题请查看：
1. 主程序日志: `tail -f ../monitoring_logs/analyzer.log`
2. 监控脚本日志: `../monitoring_logs/*.log`
3. 项目文档: `../QUICK_START_24H_MONITORING.md`

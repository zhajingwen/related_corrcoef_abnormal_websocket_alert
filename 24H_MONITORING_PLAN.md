# 24小时监控模式验证方案

**目标**: 验证系统在长时间运行下的稳定性、性能和资源管理
**执行日期**: 建议部署后立即执行
**预计耗时**: 24小时 + 2小时数据分析

---

## 📋 验证目标

### 核心验证点
1. **资源管理**: 无内存泄漏、数据库连接稳定
2. **性能稳定**: 分析速度保持在可接受范围
3. **错误处理**: 异常恢复能力和错误率
4. **数据质量**: 相关系数计算准确性
5. **优雅关闭**: 中断后资源正确清理

### 成功标准
```yaml
内存使用: 增长 <10%
数据库连接数: ≤10个（稳定）
分析速度: <0.5秒/币种
错误率: <1%
BTC缓存命中率: >80%
优雅关闭: 100%成功
```

---

## 🚀 执行步骤

### 第1步: 环境准备（10分钟）

#### 1.1 创建监控脚本
```bash
cd /Users/test/Documents/related_corrcoef_abnormal_websocket_alert

# 创建监控脚本目录
mkdir -p monitoring_logs
mkdir -p monitoring_scripts
```

#### 1.2 创建资源监控脚本
创建 `monitoring_scripts/resource_monitor.sh`:
```bash
#!/bin/bash
# 资源监控脚本 - 每分钟记录一次

LOG_DIR="monitoring_logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/resources_${TIMESTAMP}.log"

echo "时间,进程ID,CPU%,内存MB,线程数,文件描述符,数据库连接数" > "$LOG_FILE"

while true; do
    # 获取Python进程ID
    PID=$(pgrep -f "python.*main.py.*monitor")

    if [ -n "$PID" ]; then
        TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

        # CPU和内存使用
        CPU=$(ps -p $PID -o %cpu= | tr -d ' ')
        MEM_KB=$(ps -p $PID -o rss= | tr -d ' ')
        MEM_MB=$((MEM_KB / 1024))

        # 线程数
        THREADS=$(ps -M -p $PID | wc -l)
        THREADS=$((THREADS - 1))

        # 文件描述符数量
        FD_COUNT=$(lsof -p $PID 2>/dev/null | wc -l)

        # SQLite连接数
        DB_CONN=$(lsof -p $PID 2>/dev/null | grep -c "\.db$")

        echo "$TIMESTAMP,$PID,$CPU,$MEM_MB,$THREADS,$FD_COUNT,$DB_CONN" >> "$LOG_FILE"
    else
        echo "$TIMESTAMP,N/A,程序未运行" >> "$LOG_FILE"
    fi

    sleep 60  # 每分钟记录一次
done
```

#### 1.3 创建性能监控脚本
创建 `monitoring_scripts/performance_monitor.py`:
```python
#!/usr/bin/env python3
"""
性能监控脚本 - 解析程序日志，提取性能指标
"""
import re
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime

LOG_FILE = "monitoring_logs/analyzer.log"
STATS_FILE = "monitoring_logs/performance_stats.log"

def parse_log():
    """解析日志文件，提取性能指标"""
    stats = {
        'total_analyzed': 0,
        'errors': 0,
        'analysis_times': [],
        'cache_hits': 0,
        'cache_misses': 0,
        'api_calls': 0,
        'alerts': 0
    }

    if not Path(LOG_FILE).exists():
        return stats

    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            # 分析完成
            if '分析完成' in line or 'one_coin_analysis' in line:
                stats['total_analyzed'] += 1
                # 提取分析耗时
                match = re.search(r'耗时[:：]\s*([\d.]+)\s*秒', line)
                if match:
                    stats['analysis_times'].append(float(match.group(1)))

            # 错误
            if 'ERROR' in line:
                stats['errors'] += 1

            # 缓存命中
            if '缓存命中' in line or 'cache hit' in line.lower():
                stats['cache_hits'] += 1
            if '缓存未命中' in line or 'cache miss' in line.lower():
                stats['cache_misses'] += 1

            # API调用
            if 'API 请求' in line or 'fetch_ohlcv' in line:
                stats['api_calls'] += 1

            # 告警
            if '发现异常' in line or 'ALERT' in line:
                stats['alerts'] += 1

    return stats

def main():
    """主循环 - 每5分钟统计一次"""
    print(f"性能监控已启动 | 日志文件: {LOG_FILE}")
    print(f"统计结果: {STATS_FILE}")

    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        f.write("时间,已分析币种数,错误数,平均耗时(s),缓存命中率(%),API调用数,告警数\n")

    last_stats = parse_log()

    while True:
        time.sleep(300)  # 每5分钟

        current_stats = parse_log()

        # 计算增量
        new_analyzed = current_stats['total_analyzed'] - last_stats['total_analyzed']
        new_errors = current_stats['errors'] - last_stats['errors']

        # 计算平均耗时
        if current_stats['analysis_times']:
            avg_time = sum(current_stats['analysis_times']) / len(current_stats['analysis_times'])
        else:
            avg_time = 0

        # 计算缓存命中率
        total_cache_ops = current_stats['cache_hits'] + current_stats['cache_misses']
        if total_cache_ops > 0:
            hit_rate = (current_stats['cache_hits'] / total_cache_ops) * 100
        else:
            hit_rate = 0

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(STATS_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp},{current_stats['total_analyzed']},"
                   f"{current_stats['errors']},{avg_time:.3f},"
                   f"{hit_rate:.1f},{current_stats['api_calls']},"
                   f"{current_stats['alerts']}\n")

        print(f"[{timestamp}] 分析: {current_stats['total_analyzed']} | "
              f"错误: {current_stats['errors']} | "
              f"平均耗时: {avg_time:.3f}s | "
              f"缓存命中率: {hit_rate:.1f}%")

        last_stats = current_stats

if __name__ == '__main__':
    main()
```

---

### 第2步: 启动监控（5分钟）

#### 2.1 配置环境变量
```bash
# 设置飞书机器人（可选）
export LARKBOT_ID=your_bot_id

# 设置运行环境
export ENV=production

# Redis配置（如果使用）
export REDIS_HOST=127.0.0.1
export REDIS_PASSWORD=your_password
```

#### 2.2 启动主程序（后台运行）
```bash
# 方案1: 使用nohup（推荐）
nohup uv run python main.py \
    --mode=monitor \
    --interval=1800 \
    --timeframes=5m \
    --periods=1d,7d \
    > monitoring_logs/analyzer.log 2>&1 &

# 记录进程ID
echo $! > monitoring_logs/pid.txt
echo "主程序已启动 | PID: $(cat monitoring_logs/pid.txt)"

# 方案2: 使用screen（适合SSH会话）
# screen -dmS hyperliquid_monitor uv run python main.py --mode=monitor --interval=1800
# screen -list  # 查看会话

# 方案3: 使用tmux
# tmux new-session -d -s monitor 'uv run python main.py --mode=monitor --interval=1800'
# tmux list-sessions
```

#### 2.3 启动资源监控
```bash
# 赋予执行权限
chmod +x monitoring_scripts/resource_monitor.sh

# 后台启动资源监控
nohup ./monitoring_scripts/resource_monitor.sh > /dev/null 2>&1 &
echo $! > monitoring_logs/resource_monitor_pid.txt
echo "资源监控已启动 | PID: $(cat monitoring_logs/resource_monitor_pid.txt)"
```

#### 2.4 启动性能监控
```bash
# 后台启动性能监控
nohup uv run python monitoring_scripts/performance_monitor.py > /dev/null 2>&1 &
echo $! > monitoring_logs/performance_monitor_pid.txt
echo "性能监控已启动 | PID: $(cat monitoring_logs/performance_monitor_pid.txt)"
```

#### 2.5 验证启动状态
```bash
# 检查所有进程
ps aux | grep -E "(main.py|resource_monitor|performance_monitor)" | grep -v grep

# 检查日志文件
tail -f monitoring_logs/analyzer.log
```

---

### 第3步: 实时监控（24小时）

#### 3.1 创建实时监控仪表盘
创建 `monitoring_scripts/dashboard.sh`:
```bash
#!/bin/bash
# 实时监控仪表盘

clear
echo "========================================="
echo "  Hyperliquid 监控系统 - 实时仪表盘"
echo "========================================="
echo ""

while true; do
    PID=$(cat monitoring_logs/pid.txt 2>/dev/null)

    if [ -n "$PID" ] && kill -0 $PID 2>/dev/null; then
        echo "✅ 主程序运行中 | PID: $PID"
        echo ""

        # CPU和内存
        echo "📊 资源使用:"
        ps -p $PID -o %cpu,%mem,rss,vsz,etime | tail -n 1 | \
            awk '{printf "  CPU: %s%% | 内存: %s%% | RSS: %dMB | 运行时间: %s\n", $1, $2, $3/1024, $5}'

        # 数据库连接
        DB_CONN=$(lsof -p $PID 2>/dev/null | grep -c "\.db$")
        echo "  数据库连接数: $DB_CONN"
        echo ""

        # 最新性能统计
        echo "📈 性能统计 (最近5分钟):"
        if [ -f "monitoring_logs/performance_stats.log" ]; then
            tail -n 1 monitoring_logs/performance_stats.log | \
                awk -F',' '{printf "  分析: %s币种 | 错误: %s | 平均耗时: %ss | 缓存命中率: %s%% | 告警: %s\n", $2, $3, $4, $5, $7}'
        fi
        echo ""

        # 最新日志
        echo "📝 最新日志 (最后3条):"
        tail -n 3 monitoring_logs/analyzer.log | sed 's/^/  /'
        echo ""

    else
        echo "❌ 主程序未运行"
    fi

    echo "========================================="
    echo "按 Ctrl+C 退出 | 刷新间隔: 10秒"
    echo "========================================="

    sleep 10
    clear
done
```

#### 3.2 使用仪表盘
```bash
chmod +x monitoring_scripts/dashboard.sh
./monitoring_scripts/dashboard.sh
```

#### 3.3 定时检查点（每4小时）
设置提醒，在以下时间点手动检查：
- **0小时**: 启动验证
- **4小时**: 第一次检查
- **8小时**: 第二次检查
- **12小时**: 中期检查
- **16小时**: 第三次检查
- **20小时**: 第四次检查
- **24小时**: 最终检查

**检查清单**:
```bash
# 1. 查看资源使用趋势
tail -n 20 monitoring_logs/resources_*.log

# 2. 查看性能统计
tail -n 20 monitoring_logs/performance_stats.log

# 3. 检查错误日志
grep ERROR monitoring_logs/analyzer.log | tail -n 10

# 4. 查看告警数量
grep "发现异常\|ALERT" monitoring_logs/analyzer.log | wc -l

# 5. 检查进程状态
ps -p $(cat monitoring_logs/pid.txt) -f
```

---

### 第4步: 优雅关闭测试（30分钟）

#### 4.1 在第12小时测试优雅关闭
```bash
# 获取进程ID
PID=$(cat monitoring_logs/pid.txt)

# 发送SIGINT信号（模拟Ctrl+C）
kill -SIGINT $PID

# 等待程序关闭（最多60秒）
for i in {1..60}; do
    if ! kill -0 $PID 2>/dev/null; then
        echo "✅ 程序已优雅关闭 | 耗时: ${i}秒"
        break
    fi
    sleep 1
done

# 检查资源清理
sleep 2
lsof -p $PID 2>/dev/null || echo "✅ 进程已完全清理"

# 验证日志
tail -n 20 monitoring_logs/analyzer.log | grep -E "停止信号|清理资源|已关闭"
```

#### 4.2 重新启动继续测试
```bash
# 重新启动主程序
nohup uv run python main.py \
    --mode=monitor \
    --interval=1800 \
    --timeframes=5m \
    --periods=1d,7d \
    >> monitoring_logs/analyzer.log 2>&1 &

echo $! > monitoring_logs/pid.txt
echo "主程序已重启 | PID: $(cat monitoring_logs/pid.txt)"
```

---

### 第5步: 数据分析（2小时）

#### 5.1 生成资源使用报告
创建 `monitoring_scripts/analyze_resources.py`:
```python
#!/usr/bin/env python3
"""资源使用分析脚本"""
import pandas as pd
import glob
from pathlib import Path

def analyze_resources():
    log_files = glob.glob("monitoring_logs/resources_*.log")

    if not log_files:
        print("❌ 未找到资源监控日志")
        return

    # 读取所有日志
    dfs = []
    for f in log_files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"⚠️ 读取文件失败: {f} | {e}")

    if not dfs:
        return

    # 合并数据
    data = pd.concat(dfs, ignore_index=True)

    # 过滤有效数据
    data = data[data['进程ID'] != 'N/A']
    data['内存MB'] = pd.to_numeric(data['内存MB'], errors='coerce')
    data['CPU%'] = pd.to_numeric(data['CPU%'], errors='coerce')
    data['数据库连接数'] = pd.to_numeric(data['数据库连接数'], errors='coerce')

    print("\n" + "="*60)
    print("资源使用分析报告")
    print("="*60)

    # 内存分析
    print("\n📊 内存使用:")
    print(f"  起始: {data['内存MB'].iloc[0]:.1f} MB")
    print(f"  结束: {data['内存MB'].iloc[-1]:.1f} MB")
    print(f"  增长: {data['内存MB'].iloc[-1] - data['内存MB'].iloc[0]:.1f} MB "
          f"({((data['内存MB'].iloc[-1] / data['内存MB'].iloc[0]) - 1) * 100:.1f}%)")
    print(f"  平均: {data['内存MB'].mean():.1f} MB")
    print(f"  峰值: {data['内存MB'].max():.1f} MB")

    # CPU分析
    print("\n⚡ CPU使用:")
    print(f"  平均: {data['CPU%'].mean():.1f}%")
    print(f"  峰值: {data['CPU%'].max():.1f}%")

    # 数据库连接
    print("\n🔌 数据库连接:")
    print(f"  平均: {data['数据库连接数'].mean():.1f}")
    print(f"  最大: {data['数据库连接数'].max():.0f}")
    print(f"  最小: {data['数据库连接数'].min():.0f}")

    # 判断是否通过
    mem_growth = ((data['内存MB'].iloc[-1] / data['内存MB'].iloc[0]) - 1) * 100
    db_conn_stable = data['数据库连接数'].std() < 2

    print("\n✅ 验证结果:")
    print(f"  内存泄漏检测: {'✅ 通过' if mem_growth < 10 else '❌ 失败'} ({mem_growth:.1f}% < 10%)")
    print(f"  连接稳定性: {'✅ 通过' if db_conn_stable else '❌ 失败'}")
    print("="*60 + "\n")

if __name__ == '__main__':
    analyze_resources()
```

#### 5.2 生成性能分析报告
创建 `monitoring_scripts/analyze_performance.py`:
```python
#!/usr/bin/env python3
"""性能分析脚本"""
import pandas as pd
from pathlib import Path

def analyze_performance():
    stats_file = "monitoring_logs/performance_stats.log"

    if not Path(stats_file).exists():
        print("❌ 未找到性能统计日志")
        return

    data = pd.read_csv(stats_file)

    print("\n" + "="*60)
    print("性能分析报告")
    print("="*60)

    # 分析总量
    total_analyzed = data['已分析币种数'].iloc[-1]
    total_errors = data['错误数'].iloc[-1]
    total_alerts = data['告警数'].iloc[-1]

    print(f"\n📈 分析统计:")
    print(f"  总分析币种数: {total_analyzed}")
    print(f"  总错误数: {total_errors}")
    print(f"  错误率: {(total_errors / max(total_analyzed, 1)) * 100:.2f}%")
    print(f"  总告警数: {total_alerts}")

    # 性能指标
    avg_time = data['平均耗时(s)'].mean()
    max_time = data['平均耗时(s)'].max()
    avg_cache_hit = data['缓存命中率(%)'].mean()

    print(f"\n⚡ 性能指标:")
    print(f"  平均分析耗时: {avg_time:.3f}秒/币种")
    print(f"  最大分析耗时: {max_time:.3f}秒/币种")
    print(f"  平均缓存命中率: {avg_cache_hit:.1f}%")

    # 判断是否通过
    error_rate = (total_errors / max(total_analyzed, 1)) * 100

    print("\n✅ 验证结果:")
    print(f"  错误率检测: {'✅ 通过' if error_rate < 1 else '❌ 失败'} ({error_rate:.2f}% < 1%)")
    print(f"  性能检测: {'✅ 通过' if avg_time < 0.5 else '⚠️ 注意'} ({avg_time:.3f}s < 0.5s)")
    print(f"  缓存效率: {'✅ 通过' if avg_cache_hit > 80 else '⚠️ 注意'} ({avg_cache_hit:.1f}% > 80%)")
    print("="*60 + "\n")

if __name__ == '__main__':
    analyze_performance()
```

#### 5.3 生成最终报告
```bash
# 停止主程序
kill -SIGINT $(cat monitoring_logs/pid.txt)

# 停止监控脚本
kill $(cat monitoring_logs/resource_monitor_pid.txt)
kill $(cat monitoring_logs/performance_monitor_pid.txt)

# 等待进程完全退出
sleep 5

# 生成分析报告
echo "生成资源使用报告..."
uv run python monitoring_scripts/analyze_resources.py > monitoring_logs/resource_report.txt

echo "生成性能分析报告..."
uv run python monitoring_scripts/analyze_performance.py > monitoring_logs/performance_report.txt

# 查看报告
cat monitoring_logs/resource_report.txt
cat monitoring_logs/performance_report.txt
```

---

## 📊 预期结果

### 正常运行指标
```yaml
内存使用增长: <10%
数据库连接数: 3-10个（稳定）
平均分析耗时: 0.15-0.30秒/币种
错误率: <1%
缓存命中率: >80%
告警数量: 取决于市场异常情况
```

### 异常情况处理

#### 内存持续增长（>10%）
```bash
# 检查是否有缓存清理
grep "缓存已满" monitoring_logs/analyzer.log

# 检查是否有连接泄漏
lsof -p $(cat monitoring_logs/pid.txt) | grep .db | wc -l

# 建议: 重启程序，继续观察
```

#### 错误率过高（>1%）
```bash
# 查看错误类型
grep ERROR monitoring_logs/analyzer.log | cut -d'-' -f4- | sort | uniq -c

# 分析最常见错误
grep ERROR monitoring_logs/analyzer.log | tail -n 20

# 建议: 根据错误类型调整参数或修复代码
```

#### 性能下降（>0.5秒/币种）
```bash
# 检查API延迟
grep "API 请求" monitoring_logs/analyzer.log | grep "耗时"

# 检查数据库查询
grep "数据库查询" monitoring_logs/analyzer.log | grep "耗时"

# 建议: 检查网络连接或增加缓存大小
```

---

## 🎯 验证完成清单

- [ ] 监控脚本已准备
- [ ] 主程序成功启动
- [ ] 资源监控正常运行
- [ ] 性能监控正常运行
- [ ] 实时仪表盘可访问
- [ ] 4小时检查点已完成
- [ ] 8小时检查点已完成
- [ ] 12小时优雅关闭测试通过
- [ ] 16小时检查点已完成
- [ ] 20小时检查点已完成
- [ ] 24小时测试完成
- [ ] 资源使用报告已生成
- [ ] 性能分析报告已生成
- [ ] 所有指标符合预期

---

## 📝 报告模板

### 24小时监控验证报告

```markdown
# 24小时监控验证报告

**测试时间**: YYYY-MM-DD HH:MM - YYYY-MM-DD HH:MM
**测试环境**: 生产环境/测试环境
**配置参数**:
- 监控间隔: 1800秒
- 时间周期: 5m
- 数据周期: 1d, 7d

## 测试结果

### 资源使用
- 内存起始: XXX MB
- 内存结束: XXX MB
- 内存增长: XX% (目标: <10%)
- 平均CPU: XX%
- 数据库连接: X-X个 (稳定性: ✅/❌)

### 性能指标
- 总分析币种数: XXX
- 总错误数: XX
- 错误率: X.XX% (目标: <1%)
- 平均分析耗时: X.XXX秒 (目标: <0.5s)
- 缓存命中率: XX% (目标: >80%)

### 优雅关闭测试
- 关闭耗时: XX秒
- 资源清理: ✅/❌
- 日志完整性: ✅/❌

## 发现问题
1. [问题描述]
2. [问题描述]

## 改进建议
1. [建议]
2. [建议]

## 结论
✅ 通过 / ❌ 失败 / ⚠️ 部分通过
```

---

## 🆘 故障处理

### 程序意外退出
```bash
# 检查退出原因
tail -n 50 monitoring_logs/analyzer.log

# 检查系统日志
# macOS
log show --predicate 'process == "Python"' --last 1h

# 重启程序
nohup uv run python main.py --mode=monitor --interval=1800 >> monitoring_logs/analyzer.log 2>&1 &
echo $! > monitoring_logs/pid.txt
```

### 监控脚本停止
```bash
# 检查监控脚本状态
ps aux | grep -E "(resource_monitor|performance_monitor)"

# 重启资源监控
nohup ./monitoring_scripts/resource_monitor.sh > /dev/null 2>&1 &
echo $! > monitoring_logs/resource_monitor_pid.txt

# 重启性能监控
nohup uv run python monitoring_scripts/performance_monitor.py > /dev/null 2>&1 &
echo $! > monitoring_logs/performance_monitor_pid.txt
```

### 磁盘空间不足
```bash
# 检查日志大小
du -sh monitoring_logs/*

# 压缩旧日志
gzip monitoring_logs/analyzer.log.old

# 清理临时文件
rm -f monitoring_logs/*.tmp
```

---

**文档版本**: v1.0
**更新时间**: 2025-12-23
**适用版本**: 修复14个BUG后的版本

#!/usr/bin/env python3
"""
性能监控脚本 - 解析程序日志，提取性能指标
每5分钟统计一次性能数据
"""
import re
import time
from pathlib import Path
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

    try:
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
    except Exception as e:
        print(f"⚠️ 解析日志失败: {e}")

    return stats

def main():
    """主循环 - 每5分钟统计一次"""
    print("✅ 性能监控已启动")
    print(f"📊 日志文件: {LOG_FILE}")
    print(f"📈 统计结果: {STATS_FILE}")
    print("⏱️  统计间隔: 5分钟")
    print("")

    # 写入表头
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        f.write("时间,已分析币种数,错误数,平均耗时(s),缓存命中率(%),API调用数,告警数\n")

    last_stats = parse_log()

    while True:
        time.sleep(300)  # 每5分钟

        current_stats = parse_log()

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

        # 写入统计文件
        with open(STATS_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp},{current_stats['total_analyzed']},"
                   f"{current_stats['errors']},{avg_time:.3f},"
                   f"{hit_rate:.1f},{current_stats['api_calls']},"
                   f"{current_stats['alerts']}\n")

        # 输出到控制台
        print(f"[{timestamp}] 分析: {current_stats['total_analyzed']} | "
              f"错误: {current_stats['errors']} | "
              f"平均耗时: {avg_time:.3f}s | "
              f"缓存命中率: {hit_rate:.1f}% | "
              f"告警: {current_stats['alerts']}")

        last_stats = current_stats

if __name__ == '__main__':
    main()

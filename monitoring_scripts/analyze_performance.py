#!/usr/bin/env python3
"""性能分析脚本 - 生成24小时监控的性能分析报告"""
import pandas as pd
from pathlib import Path

def analyze_performance():
    """分析性能统计日志，生成报告"""
    stats_file = "monitoring_logs/performance_stats.log"

    if not Path(stats_file).exists():
        print("❌ 未找到性能统计日志文件")
        print("   请确认性能监控已运行并生成日志")
        return

    try:
        data = pd.read_csv(stats_file)
    except Exception as e:
        print(f"❌ 读取性能统计文件失败: {e}")
        return

    if len(data) == 0:
        print("❌ 性能统计文件为空")
        return

    print("\n" + "="*70)
    print("  Hyperliquid 监控系统 - 性能分析报告")
    print("="*70)

    print(f"\n📅 监控时间:")
    print(f"  开始: {data['时间'].iloc[0]}")
    print(f"  结束: {data['时间'].iloc[-1]}")
    print(f"  总统计点: {len(data)}个 (每5分钟1次)")
    print(f"  监控时长: {len(data) * 5 / 60:.1f}小时")

    # 分析总量
    total_analyzed = data['已分析币种数'].iloc[-1]
    total_errors = data['错误数'].iloc[-1]
    total_alerts = data['告警数'].iloc[-1]
    total_api_calls = data['API调用数'].iloc[-1]

    error_rate = (total_errors / max(total_analyzed, 1)) * 100

    print(f"\n📈 分析统计:")
    print(f"  总分析币种数: {total_analyzed}")
    print(f"  总错误数: {total_errors}")
    print(f"  错误率: {error_rate:.2f}%")
    print(f"  总API调用数: {total_api_calls}")
    print(f"  总告警数: {total_alerts}")

    # 性能指标
    avg_time = data['平均耗时(s)'].mean()
    max_time = data['平均耗时(s)'].max()
    min_time = data['平均耗时(s)'].min()
    avg_cache_hit = data['缓存命中率(%)'].mean()

    print(f"\n⚡ 性能指标:")
    print(f"  平均分析耗时: {avg_time:.3f}秒/币种")
    print(f"  最快分析耗时: {min_time:.3f}秒/币种")
    print(f"  最慢分析耗时: {max_time:.3f}秒/币种")
    print(f"  平均缓存命中率: {avg_cache_hit:.1f}%")

    # 吞吐量分析
    if total_analyzed > 0 and len(data) > 1:
        duration_hours = len(data) * 5 / 60
        throughput = total_analyzed / duration_hours
        print(f"\n🚀 吞吐量:")
        print(f"  分析速率: {throughput:.1f}币种/小时")
        print(f"  预计完成300币种需要: {300 / max(throughput, 1):.1f}小时")

    # 缓存效率
    print(f"\n💾 缓存效率:")
    print(f"  平均命中率: {avg_cache_hit:.1f}%")
    print(f"  最高命中率: {data['缓存命中率(%)'].max():.1f}%")
    print(f"  最低命中率: {data['缓存命中率(%)'].min():.1f}%")

    # 验证结果
    print(f"\n✅ 验证结果:")

    # 错误率检测
    error_rate_ok = error_rate < 1
    print(f"  错误率检测: {'✅ 通过' if error_rate_ok else '❌ 失败'} "
          f"({error_rate:.2f}% | 目标: <1%)")

    # 性能检测
    perf_ok = avg_time < 0.5
    print(f"  性能检测: {'✅ 通过' if perf_ok else '⚠️ 注意'} "
          f"({avg_time:.3f}s | 目标: <0.5s)")

    # 缓存效率
    cache_ok = avg_cache_hit > 80
    print(f"  缓存效率: {'✅ 通过' if cache_ok else '⚠️ 注意'} "
          f"({avg_cache_hit:.1f}% | 目标: >80%)")

    # 告警合理性
    alert_rate = (total_alerts / max(total_analyzed, 1)) * 100
    alert_ok = alert_rate < 10  # 告警率低于10%认为合理
    print(f"  告警合理性: {'✅ 正常' if alert_ok else '⚠️ 偏高'} "
          f"({alert_rate:.1f}% | 建议: <10%)")

    # 总体评估
    all_ok = error_rate_ok and perf_ok and cache_ok

    print(f"\n{'='*70}")
    print(f"  总体评估: {'✅ 优秀 - 性能表现良好' if all_ok else '⚠️ 需要关注部分指标'}")
    print(f"{'='*70}\n")

    # 如果有异常，提供建议
    if not all_ok:
        print("💡 改进建议:")
        if not error_rate_ok:
            print(f"  - 错误率过高({error_rate:.2f}%)，建议检查错误日志分析根本原因")
        if not perf_ok:
            print(f"  - 平均耗时({avg_time:.3f}s)超过阈值，建议优化API调用或增加缓存")
        if not cache_ok:
            print(f"  - 缓存命中率({avg_cache_hit:.1f}%)偏低，建议调整缓存策略或增加缓存大小")
        print()

if __name__ == '__main__':
    analyze_performance()

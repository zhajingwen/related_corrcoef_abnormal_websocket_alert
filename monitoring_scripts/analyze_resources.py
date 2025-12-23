#!/usr/bin/env python3
"""资源使用分析脚本 - 生成24小时监控的资源使用报告"""
import pandas as pd
import glob
from pathlib import Path

def analyze_resources():
    """分析资源监控日志，生成报告"""
    log_files = glob.glob("monitoring_logs/resources_*.log")

    if not log_files:
        print("❌ 未找到资源监控日志文件")
        print("   请确认资源监控已运行并生成日志")
        return

    # 读取所有日志文件
    dfs = []
    for f in log_files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"⚠️ 读取文件失败: {f} | 错误: {e}")

    if not dfs:
        print("❌ 无法读取任何有效的日志文件")
        return

    # 合并所有数据
    data = pd.concat(dfs, ignore_index=True)

    # 过滤有效数据行
    data = data[data['进程ID'] != 'N/A'].copy()

    if len(data) == 0:
        print("❌ 没有有效的监控数据")
        return

    # 转换数据类型
    data['内存MB'] = pd.to_numeric(data['内存MB'], errors='coerce')
    data['CPU%'] = pd.to_numeric(data['CPU%'], errors='coerce')
    data['线程数'] = pd.to_numeric(data['线程数'], errors='coerce')
    data['文件描述符'] = pd.to_numeric(data['文件描述符'], errors='coerce')
    data['数据库连接数'] = pd.to_numeric(data['数据库连接数'], errors='coerce')

    # 移除NaN行
    data = data.dropna()

    print("\n" + "="*70)
    print("  Hyperliquid 监控系统 - 资源使用分析报告")
    print("="*70)

    print(f"\n📅 监控时间:")
    print(f"  开始: {data['时间'].iloc[0]}")
    print(f"  结束: {data['时间'].iloc[-1]}")
    print(f"  总采样点: {len(data)}个 (每分钟1次)")
    print(f"  监控时长: {len(data) / 60:.1f}小时")

    # 内存分析
    mem_start = data['内存MB'].iloc[0]
    mem_end = data['内存MB'].iloc[-1]
    mem_growth = mem_end - mem_start
    mem_growth_pct = (mem_growth / mem_start) * 100

    print(f"\n📊 内存使用:")
    print(f"  起始值: {mem_start:.1f} MB")
    print(f"  结束值: {mem_end:.1f} MB")
    print(f"  增长量: {mem_growth:+.1f} MB ({mem_growth_pct:+.1f}%)")
    print(f"  平均值: {data['内存MB'].mean():.1f} MB")
    print(f"  峰值: {data['内存MB'].max():.1f} MB")
    print(f"  最小值: {data['内存MB'].min():.1f} MB")

    # CPU分析
    print(f"\n⚡ CPU使用:")
    print(f"  平均值: {data['CPU%'].mean():.1f}%")
    print(f"  峰值: {data['CPU%'].max():.1f}%")
    print(f"  最小值: {data['CPU%'].min():.1f}%")

    # 线程分析
    print(f"\n🧵 线程数:")
    print(f"  平均值: {data['线程数'].mean():.1f}")
    print(f"  最大值: {data['线程数'].max():.0f}")
    print(f"  最小值: {data['线程数'].min():.0f}")

    # 文件描述符分析
    print(f"\n📂 文件描述符:")
    print(f"  平均值: {data['文件描述符'].mean():.1f}")
    print(f"  最大值: {data['文件描述符'].max():.0f}")
    print(f"  最小值: {data['文件描述符'].min():.0f}")

    # 数据库连接分析
    db_conn_mean = data['数据库连接数'].mean()
    db_conn_std = data['数据库连接数'].std()
    db_conn_max = data['数据库连接数'].max()

    print(f"\n🔌 数据库连接:")
    print(f"  平均值: {db_conn_mean:.1f}")
    print(f"  标准差: {db_conn_std:.2f}")
    print(f"  最大值: {db_conn_max:.0f}")
    print(f"  最小值: {data['数据库连接数'].min():.0f}")

    # 验证结果
    print(f"\n✅ 验证结果:")

    # 内存泄漏检测
    mem_leak_ok = mem_growth_pct < 10
    print(f"  内存泄漏检测: {'✅ 通过' if mem_leak_ok else '❌ 失败'} "
          f"({mem_growth_pct:+.1f}% | 目标: <10%)")

    # 连接稳定性
    conn_stable = db_conn_std < 2 and db_conn_max <= 10
    print(f"  连接稳定性: {'✅ 通过' if conn_stable else '⚠️ 注意'} "
          f"(标准差: {db_conn_std:.2f} | 最大值: {db_conn_max:.0f})")

    # 资源使用合理性
    resource_ok = data['内存MB'].max() < 1000 and data['CPU%'].mean() < 50
    print(f"  资源使用: {'✅ 合理' if resource_ok else '⚠️ 偏高'} "
          f"(峰值内存: {data['内存MB'].max():.0f}MB | 平均CPU: {data['CPU%'].mean():.1f}%)")

    # 总体评估
    all_ok = mem_leak_ok and conn_stable and resource_ok

    print(f"\n{'='*70}")
    print(f"  总体评估: {'✅ 优秀 - 系统运行稳定' if all_ok else '⚠️ 需要关注部分指标'}")
    print(f"{'='*70}\n")

    # 如果有异常，提供建议
    if not all_ok:
        print("💡 改进建议:")
        if not mem_leak_ok:
            print("  - 内存增长超过阈值，建议检查缓存清理逻辑")
        if not conn_stable:
            print("  - 数据库连接不稳定，建议检查连接池配置")
        if not resource_ok:
            print("  - 资源使用偏高，建议优化性能或增加系统资源")
        print()

if __name__ == '__main__':
    analyze_resources()

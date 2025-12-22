# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

本项目是一个 **Hyperliquid 相关系数异常监控与告警系统**，用于分析山寨币与 BTC 的皮尔逊相关性，识别短期低相关但长期高相关且存在时间差的异常币种。

## 常用命令

### 安装依赖
```bash
uv sync
```

### 运行程序
```bash
# 分析模式（一次性分析所有币种）
uv run python main.py --mode=analysis

# 监控模式（持续监控）
uv run python main.py --mode=monitor --interval=3600

# 分析单个币种（用于测试）
uv run python main.py --coin=ETH/USDC:USDC

# 调试模式
uv run python main.py --debug
```

### 环境变量配置
```bash
# 飞书机器人告警（可选）
export LARKBOT_ID=your_bot_id

# Redis配置（可选，用于告警去重）
export REDIS_HOST=127.0.0.1
export REDIS_PASSWORD=your_password

# 运行环境
export ENV=production  # 或 local（开发模式）
```

## 代码架构

### 核心架构模式
项目采用 **数据管道 + 分析引擎** 架构：

```
[REST API] → [SQLite缓存] → [数据管理器] → [相关性分析器] → [告警系统]
     ↓             ↓              ↓                ↓              ↓
  ccxt库      增量更新        LRU缓存         数学计算        飞书/本地文件
```

### 关键模块职责

**数据层**：
- `rest_client.py` - REST API客户端，基于ccxt，处理数据下载和速率限制
- `sqlite_cache.py` - SQLite持久化存储，支持增量更新，线程安全
- `manager.py` - 数据管理器，统一数据访问接口，BTC数据LRU缓存

**分析层**：
- `analyzer.py` - 核心分析引擎，实现最优延迟算法和异常模式检测
- `main.py` - 命令行入口，支持analysis/monitor两种模式

**工具层**：
- `utils/lark_bot.py` - 飞书消息推送
- `utils/config.py` - 环境变量配置
- `utils/redisdb.py` - Redis连接池（可选）

### 核心算法

**最优延迟计算**（`analyzer.py:find_optimal_delay`）：
- 通过滑动窗口移动BTC收益率序列
- 计算 `Corr(BTC[t], ALT[t+τ])` 在不同延迟τ下的相关系数
- 找出使相关系数最大化的延迟值 τ*

**异常模式检测**：
1. 长期高相关：7d/30d/60d周期相关系数 > 0.6
2. 短期低相关：1d周期相关系数 < 0.3
3. 显著差值：(长期最大 - 短期最小) > 0.5
4. 滞后判定：短期最优延迟 τ* > 0

### 线程安全设计

**多级锁保护**：
- SQLite：每线程独立连接 + 60秒超时
- BTC缓存：读写锁 + OrderedDict LRU
- 下载锁：防止重复下载同一数据

**缓存策略**：
- 内存：BTC数据LRU缓存（100条，零延迟读取）
- 磁盘：SQLite增量更新（避免重复API调用）
- 网络：500ms速率限制 + 重试机制

### 性能特性

**数据流优化**：
- 首次运行：~15-20分钟（全量下载）
- 后续运行：~2-3分钟（增量更新）
- API调用：首次800+次，后续10-20次

**内存管理**：
- BTC缓存限制100条目
- 线程本地连接池
- 自动资源清理

## 重要常量和配置

### 分析参数
```python
# analyzer.py
MIN_POINTS_FOR_CORR_CALC = 30        # 相关系数计算最小数据点
MIN_DATA_POINTS_FOR_ANALYSIS = 100   # 分析所需最小数据点
LONG_TERM_CORR_THRESHOLD = 0.6       # 长期相关系数阈值
SHORT_TERM_CORR_THRESHOLD = 0.3      # 短期相关系数阈值
CORR_DIFF_THRESHOLD = 0.5            # 相关系数差值阈值
```

### 缓存配置
```python
# manager.py
MAX_BTC_CACHE_SIZE = 100             # BTC内存缓存最大条目数
BTC_SYMBOL = "BTC/USDC:USDC"         # BTC交易对符号

# rest_client.py
MAX_REQUESTS_PER_DOWNLOAD = 500      # 单次下载最大请求数
```

## 常见操作

### 添加新的分析逻辑
1. 在 `analyzer.py` 的 `DelayCorrelationAnalyzer` 类中扩展
2. 关注 `one_coin_analysis()` 方法和 `_detect_anomaly_pattern()` 方法
3. 确保线程安全和异常处理

### 修改告警逻辑
1. 编辑 `analyzer.py` 的 `_output_results()` 方法
2. 告警优先级：飞书 > 本地文件备份（`alerts/` 目录）
3. 消息格式在该方法中定义

### 调整缓存策略
1. BTC缓存：修改 `manager.py` 的 `MAX_BTC_CACHE_SIZE`
2. SQLite缓存：编辑 `sqlite_cache.py` 的连接配置
3. API限速：调整 `rest_client.py` 的 `rate_limit_ms`

### 扩展支持新交易所
1. 确保ccxt库支持该交易所
2. 修改 `rest_client.py` 的 `get_usdc_perpetuals()` 方法
3. 调整交易对匹配规则（当前为 `/USDC:USDC`）

## 项目模块导入关系

```
main.py
├── analyzer.py (DelayCorrelationAnalyzer)
│   ├── manager.py (DataManager)
│   │   ├── rest_client.py (RESTClient)
│   │   └── sqlite_cache.py (SQLiteCache)
│   └── utils/lark_bot.py (sender)
└── utils/config.py
```
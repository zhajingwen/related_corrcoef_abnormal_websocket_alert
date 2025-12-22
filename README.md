# Hyperliquid 相关系数异常监控与告警

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

本项目用于分析 **Hyperliquid** 交易所中山寨币与 **BTC/USDC:USDC** 的相关性，识别“**短期低相关但长期高相关**”且可能存在**滞后关系（时间差）**的币种，并通过**飞书机器人**告警（未配置时会自动落盘到本地文件）。

## 核心特性

- **异常模式检测**：短期（默认 `1d`）低相关、长期（默认 `7d/30d/60d`）高相关，并满足差值阈值
- **最优延迟 τ\***：在 \(0..48\) 的滞后窗口里寻找使相关系数最大的延迟
- **REST + SQLite 缓存**：K 线历史数据落 SQLite，后续运行增量更新，减少 API 调用
- **BTC LRU 内存缓存**：按 `(timeframe, period)` 缓存 BTC 数据（默认最多 **100** 项），带线程锁保护
- **飞书告警（可选）**：配置 `LARKBOT_ID` 后发送；否则写入 `alerts/` 目录做兜底

## 文件结构

```
related_corrcoef_abnormal_websocket_alert/
├── __init__.py          # 对外导出：SQLiteCache/RESTClient/WebSocketClient/DataManager/DelayCorrelationAnalyzer
├── pyproject.toml       # 项目配置与依赖（uv）
├── uv.lock              # 依赖锁定
├── sqlite_cache.py      # SQLite 缓存
├── rest_client.py       # 基于 ccxt 的 REST 获取 + 增量更新
├── websocket_client.py  # hyperliquid-python-sdk WebSocket 订阅（当前分析流程未使用）
├── manager.py           # DataManager：统一数据访问 + BTC LRU 缓存
├── analyzer.py          # DelayCorrelationAnalyzer：异常检测 + 告警
├── main.py              # 命令行入口（analysis/monitor）
└── utils/
    ├── config.py        # ENV/LARKBOT_ID/REDIS_* 环境变量
    ├── lark_bot.py      # 飞书消息发送
    ├── redisdb.py       # Redis 连接池（可选）
    ├── scheduler.py     # 定时调度装饰器（与主分析器运行无强依赖）
    └── spider_failed_alert.py # 爬虫失败告警装饰器（与主分析器运行无强依赖）
```

## 快速开始

### 安装依赖（uv）

```bash
uv sync
```

### 运行（重要：运行方式与包结构有关）

本仓库根目录本身是一个 Python package（使用了**相对导入**），因此推荐两种运行方式：

**方式 A：在仓库父目录运行（推荐）**

```bash
cd ..
python -m related_corrcoef_abnormal_websocket_alert.main --mode=analysis
```

**方式 B：在仓库目录内运行（设置 PYTHONPATH 指向父目录）**

```bash
PYTHONPATH="$(pwd)/.." python -m related_corrcoef_abnormal_websocket_alert.main --mode=analysis
```

### 常用命令示例

```bash
# 一次性分析所有币种（默认）
python -m related_corrcoef_abnormal_websocket_alert.main --mode=analysis

# 分析单个币种（快速验证）
python -m related_corrcoef_abnormal_websocket_alert.main --coin=ETH/USDC:USDC

# 监控模式：按间隔循环分析
python -m related_corrcoef_abnormal_websocket_alert.main --mode=monitor --interval=3600

# 自定义时间周期与数据周期
python -m related_corrcoef_abnormal_websocket_alert.main --timeframes=1m,5m --periods=1d,7d,30d,60d

# 调试日志
python -m related_corrcoef_abnormal_websocket_alert.main --debug

# 指定数据库路径
python -m related_corrcoef_abnormal_websocket_alert.main --db=hyperliquid_data.db
```

### 命令行参数（`main.py`）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | `analysis` 一次性分析 / `monitor` 持续监控 | `analysis` |
| `--coin` | 指定单个交易对，如 `ETH/USDC:USDC` | - |
| `--exchange` | 交易所名称（ccxt） | `hyperliquid` |
| `--db` | SQLite 数据库路径 | `hyperliquid_data.db` |
| `--timeframes` | K 线周期（逗号分隔） | `1m,5m` |
| `--periods` | 数据周期（逗号分隔） | `1d,7d,30d,60d` |
| `--interval` | 监控模式分析间隔（秒） | `3600` |
| `--debug` | 启用 DEBUG 日志 | - |

## 告警与输出

- **日志文件**：默认写入 `analyzer.log`（10MB 轮转，保留 5 个备份），同时输出到控制台（见 `analyzer.py: setup_logging()`）。
- **飞书告警**：设置 `LARKBOT_ID` 后启用（见 `analyzer.py`）。
- **告警落盘兜底**：若飞书未配置/发送失败，会在 `alerts/` 下写入：
  - `alerts/alert_{safe_coin}_{timestamp}.txt`

## 环境变量

```bash
# 环境标识（可选，scheduler 在 local 环境会“直接执行”而不等待调度）
export ENV=production

# 飞书机器人 Webhook ID（用于 analyzer 异常告警）
export LARKBOT_ID=your_bot_id

# Redis（可选：给 spider_failed_alert 做 24h 去重；未配置会自动降级）
export REDIS_HOST=127.0.0.1
export REDIS_PASSWORD=your_redis_password

# 爬虫失败告警（可选：spider_failed_alert 使用）
export SPIDER_ALERT_WEBHOOK_ID=your_webhook_id
```

## 异常检测逻辑（以代码为准）

位于 `analyzer.py: DelayCorrelationAnalyzer`：

- **最小数据点**
  - 相关系数计算最小点数：`MIN_POINTS_FOR_CORR_CALC = 30`
  - 单次分析最小点数：`MIN_DATA_POINTS_FOR_ANALYSIS = 100`
- **阈值**
  - 长期相关阈值：`LONG_TERM_CORR_THRESHOLD = 0.6`
  - 短期相关阈值：`SHORT_TERM_CORR_THRESHOLD = 0.3`
  - 差值阈值：`CORR_DIFF_THRESHOLD = 0.5`
- **判定规则（默认周期集合）**
  - 短期周期：`['1d']`
  - 长期周期：`['7d', '30d', '60d']`
  - 当长期最大相关 > 阈值 且 短期最小相关 < 阈值 时：
    - 若差值（长期最大 - 短期最小）> 差值阈值，则异常
    - 或者短期（`1d`）存在明显滞后（`tau_star > 0`）也会触发

## 模块使用（代码调用）

```python
from related_corrcoef_abnormal_websocket_alert import DataManager, DelayCorrelationAnalyzer

manager = DataManager(db_path="hyperliquid_data.db")
df = manager.get_ohlcv("BTC/USDC:USDC", "5m", "7d")

analyzer = DelayCorrelationAnalyzer(db_path="hyperliquid_data.db")
analyzer.run_single("ETH/USDC:USDC")
```

## 常见问题（Troubleshooting）

- **429 / RateLimitExceeded**：已启用 ccxt `enableRateLimit`（默认 `rateLimit=500ms`），如仍频繁触发可在 `RESTClient(rate_limit_ms=1000)` 增大间隔。
- **飞书未发送**：未设置 `LARKBOT_ID` 时会提示并落盘到 `alerts/`。
- **SQLite 锁**：`SQLiteCache` 使用线程本地连接 + `timeout=60s`，单进程多线程一般可用；多进程并发建议分库或外置存储。

## 依赖

依赖以 `pyproject.toml` 为准：

- `ccxt`
- `hyperliquid-python-sdk`
- `numpy`
- `pandas`
- `retry`
- `requests`
- `redis`（可选路径会自动降级）
- `matplotlib` / `seaborn` / `pyinform`（当前分析主流程不强依赖绘图，但在依赖中保留）

## 许可证

MIT License

## 核心特性

- **异常模式检测**：自动识别短期低相关（<0.3）但长期高相关（>0.6）的异常币种
- **最优延迟计算**：计算山寨币相对 BTC 的最优延迟 τ*，识别滞后关系
- **SQLite 本地缓存**：历史数据持久化存储，避免重复下载，支持增量更新
- **BTC 内存缓存**：LRU 缓存机制（最大 20 条），线程安全，大幅提升性能
- **增量数据更新**：只下载缺失的数据，大幅减少 API 调用
- **飞书通知集成**：发现异常币种时自动发送通知
- **内置速率限制**：自动控制请求频率，避免 429 错误
- **线程安全设计**：支持多线程环境下的并发访问

## 文件结构

```
├── __init__.py          # 模块导出 + 路径修复
├── pyproject.toml       # 项目配置和依赖管理（uv）
├── uv.lock              # 依赖锁定文件（确保可重复构建）
├── .gitignore           # Git 忽略规则
├── sqlite_cache.py      # SQLite 缓存模块
├── rest_client.py       # REST 客户端（带限流+缓存）
├── websocket_client.py  # WebSocket 客户端（官方 SDK）
├── manager.py           # 数据管理器（核心）
├── analyzer.py          # 相关系数分析器
├── main.py              # 主程序入口
├── utils/               # 工具模块
│   ├── __init__.py
│   ├── config.py        # 配置管理（环境变量）
│   ├── scheduler.py     # 定时调度器
│   ├── lark_bot.py      # 飞书通知工具
│   ├── redisdb.py       # Redis数据库连接
│   └── spider_failed_alert.py  # 爬虫失败告警
└── README.md            # 本文档
```

**文件说明**：
- `pyproject.toml`: 使用 [uv](https://github.com/astral-sh/uv) 包管理器，定义项目元数据和依赖
- `uv.lock`: 锁定所有依赖的精确版本，确保不同环境下的一致性
- `.gitignore`: 排除生成文件（如 `*.db`、`*.log`、`.venv/` 等）

## 快速开始

### 安装依赖

```bash
uv sync
```

### 运行分析

```bash
# 分析所有币种（一次性分析）
.venv/bin/python -m data.main --mode=analysis

# 分析单个币种（快速测试）
.venv/bin/python -m data.main --coin=ETH/USDC:USDC

# 持续监控模式（每小时分析一次）
.venv/bin/python -m data.main --mode=monitor --interval=3600

# 自定义时间周期和数据周期
.venv/bin/python -m data.main --timeframes=1m,5m --periods=1d,7d,30d

# 调试模式（详细日志，DEBUG 级别）
.venv/bin/python -m data.main --debug

# 指定数据库路径
.venv/bin/python -m data.main --db=my_data.db
```

**监控模式说明**：
- 监控模式会持续运行，每隔指定间隔（`--interval`）执行一次分析
- 支持信号处理：可通过 `Ctrl+C` 或 `SIGTERM` 优雅退出
- 每次分析完成后会等待指定间隔，然后开始下一轮分析

#### 运行输出示例

**分析单个币种**：
```
2024-12-22 10:30:15 - data.analyzer - INFO - ============================================================
2024-12-22 10:30:15 - data.analyzer - INFO - Hyperliquid 相关系数分析器
2024-12-22 10:30:15 - data.analyzer - INFO - 模式: analysis
2024-12-22 10:30:15 - data.analyzer - INFO - 交易所: hyperliquid
2024-12-22 10:30:15 - data.analyzer - INFO - 数据库: hyperliquid_data.db
2024-12-22 10:30:15 - data.analyzer - INFO - ============================================================
2024-12-22 10:30:15 - data.analyzer - INFO - 分析器初始化 | 交易所: hyperliquid | 时间周期: ['1m', '5m'] | 数据周期: ['1d', '7d', '30d', '60d']
2024-12-22 10:30:15 - data.analyzer - INFO - 预取 BTC 历史数据...
2024-12-22 10:30:20 - data.analyzer - INFO - 发现异常币种 | 交易所: hyperliquid | 币种: ETH/USDC:USDC | 差值: 0.58
2024-12-22 10:30:20 - data.analyzer - INFO - 程序正常退出
```

**发现异常币种时的飞书通知**：
```
hyperliquid

ETH/USDC:USDC 相关系数分析结果
  相关系数 时间周期 数据周期  最优延迟
    0.8234     1m     60d      5
    0.7891     5m     60d      3
    0.7654     1m     30d      4
    0.2145     1m      1d      2

差值: 0.61
```

**完整分析流程**：
```
2024-12-22 10:35:00 - data.analyzer - INFO - 启动分析器 | 交易所: hyperliquid | 时间周期: ['1m', '5m'] | 数据周期: ['1d', '7d', '30d', '60d']
2024-12-22 10:35:00 - data.analyzer - INFO - 发现 120 个 USDC 永续合约交易对
2024-12-22 10:35:00 - data.analyzer - INFO - 分析进度: 30/120 (25%)
2024-12-22 10:35:30 - data.analyzer - INFO - 发现异常币种 | 交易所: hyperliquid | 币种: AVAX/USDC:USDC | 差值: 0.52
2024-12-22 10:35:45 - data.analyzer - INFO - 分析进度: 60/120 (50%)
2024-12-22 10:36:15 - data.analyzer - INFO - 分析进度: 90/120 (75%)
2024-12-22 10:36:45 - data.analyzer - INFO - 分析进度: 120/120 (100%)
2024-12-22 10:36:45 - data.analyzer - INFO - 分析完成 | 交易所: hyperliquid | 总数: 120 | 异常: 3 | 跳过: 2 | 耗时: 105.3s | 平均: 0.88s/币种
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | 运行模式：`analysis` 或 `monitor` | `analysis` |
| `--coin` | 分析单个币种，如 `ETH/USDC:USDC` | - |
| `--exchange` | 交易所名称 | `hyperliquid` |
| `--db` | SQLite 数据库路径 | `hyperliquid_data.db` |
| `--timeframes` | K 线周期，逗号分隔 | `1m,5m` |
| `--periods` | 数据周期，逗号分隔 | `1d,7d,30d,60d` |
| `--debug` | 启用调试日志 | - |
| `--interval` | 监控模式分析间隔（秒） | `3600` |

## 模块说明

### SQLiteCache (`sqlite_cache.py`)

K 线数据本地缓存（线程安全），支持：
- 自动创建表结构和索引（优化查询性能）
- 按交易对/周期存储和查询
- 增量数据追加（INSERT OR REPLACE）
- 线程本地存储：每个线程使用独立的数据库连接，避免并发问题
- 自动连接管理：程序退出时自动关闭所有连接
- 支持查询最新/最早时间戳，便于增量更新

```python
from data import SQLiteCache

cache = SQLiteCache("hyperliquid_data.db")
cache.save_ohlcv("BTC/USDC:USDC", "5m", df)
df = cache.get_ohlcv("BTC/USDC:USDC", "5m", since_ms=1234567890000)

# 获取缓存统计信息
stats = cache.get_cache_stats()
```

### RESTClient (`rest_client.py`)

带速率限制的 REST API 客户端：
- 基于 ccxt，启用 `enableRateLimit`（默认 500ms 间隔）
- 自动重试机制：10 次重试，指数退避（使用 `retry` 装饰器）
- 增量下载：智能检测缓存缺失部分，只下载需要的数据
- 安全阀机制：
  - 最大请求次数限制（500 次/下载任务）
  - 时间戳检测（防止 API 返回相同数据导致死循环）
- 与 SQLiteCache 集成，自动缓存和增量更新

```python
from data import RESTClient, SQLiteCache

cache = SQLiteCache()
client = RESTClient(cache=cache, rate_limit_ms=500)
df = client.fetch_ohlcv("BTC/USDC:USDC", "5m", "7d")

# 获取所有 USDC 永续合约
perpetuals = client.get_usdc_perpetuals()
```

### WebSocketClient (`websocket_client.py`)

实时数据订阅客户端（已实现但当前未在分析器中使用）：
- 封装官方 `hyperliquid-python-sdk`
- 支持 K 线数据订阅（支持 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 3d, 1w, 1M）
- 内存缓存（每个交易对/周期最多缓存 1000 根 K 线）
- 支持回调函数注册
- 自动资源清理：程序退出时自动关闭连接

```python
from data import WebSocketClient

ws = WebSocketClient(max_cache_size=1000)
ws.start()
ws.subscribe_candles("BTC", "5m")
# ... 等待数据
df = ws.get_cached_dataframe("BTC", "5m")
ws.stop()

# 或使用 with 语句
with WebSocketClient() as ws:
    ws.subscribe_candles("BTC", "5m")
    df = ws.get_cached_dataframe("BTC", "5m")
```

### DataManager (`manager.py`)

统一数据管理器，使用 REST API + SQLite 缓存：

**核心功能**：
- 统一的数据访问接口
- BTC 数据内存缓存（LRU 机制，最大 20 条，线程安全）
- 双重检查锁定模式：避免多线程环境下的重复下载
- 预取 BTC 数据：分析前预先加载常用数据到缓存

```python
from data import DataManager

manager = DataManager(exchange_name="hyperliquid", db_path="hyperliquid_data.db")
manager.initialize()

# 获取任意交易对数据（自动使用缓存）
df = manager.get_ohlcv("BTC/USDC:USDC", "5m", "7d")

# 获取 BTC 数据（带 LRU 内存缓存，线程安全）
btc_df = manager.get_btc_data("5m", "7d")

# 预取 BTC 数据到缓存
manager.prefetch_btc_data(timeframes=["1m", "5m"], periods=["1d", "7d", "30d"])

# 获取所有 USDC 永续合约
perpetuals = manager.get_usdc_perpetuals()

manager.shutdown()
```

### DelayCorrelationAnalyzer (`analyzer.py`)

相关系数分析器（核心模块）：

**异常检测逻辑**：
- 长期相关系数阈值：`0.6`（7d/30d/60d 周期中至少有一个 > 0.6）
- 短期相关系数阈值：`0.3`（1d 周期中最小相关系数 < 0.3）
- 相关系数差值阈值：`0.5`（长期最大 - 短期最小 > 0.5）
- 或短期存在明显滞后（τ* > 0）

**核心算法**：
- 最优延迟 τ* 计算：通过计算不同延迟下 BTC 和山寨币收益率的相关系数，找出使相关系数最大的延迟值
- τ* > 0 表示山寨币滞后于 BTC，存在时间差套利机会
- 数据对齐和验证：自动对齐时间索引，验证数据量（最少 50 个数据点）

**日志系统**：
- 控制台和文件双重输出
- 日志文件：`analyzer.log`（10MB 轮转，保留 5 个备份）

```python
from data import DelayCorrelationAnalyzer

# 创建分析器
analyzer = DelayCorrelationAnalyzer(
    exchange_name="hyperliquid",
    db_path="hyperliquid_data.db",
    default_timeframes=["1m", "5m"],
    default_periods=["1d", "7d", "30d", "60d"]
)

# 分析所有 USDC 永续合约
analyzer.run()

# 分析单个币种（用于测试）
analyzer.run_single("ETH/USDC:USDC")

# 手动分析单个币种（返回是否发现异常）
is_anomaly = analyzer.one_coin_analysis("ETH/USDC:USDC")
```

### Utils 工具模块

#### Config (`utils/config.py`)

环境变量配置管理：
- `ENV` - 环境标识（local/production等），默认 `local`
- `LARKBOT_ID` - 飞书机器人 ID
- `REDIS_HOST` - Redis 主机地址，默认 `127.0.0.1`
- `REDIS_PASSWORD` - Redis 密码

#### Scheduler (`utils/scheduler.py`)

定时调度装饰器，支持三种调度方式：

```python
from data.utils.scheduler import scheduled_task

# 方式1: 每天指定时间执行
@scheduled_task(start_time='09:00')
def daily_task():
    pass

# 方式2: 指定周几的指定时间执行
@scheduled_task(start_time='09:00', weekdays=[0, 2, 4])  # 周一、周三、周五
def weekday_task():
    pass

# 方式3: 每隔N秒执行一次
@scheduled_task(duration=3600)  # 每小时执行一次
def periodic_task():
    pass
```

**注意**: 在 `local` 环境下，调度器会直接执行任务而不等待调度时间。

#### LarkBot (`utils/lark_bot.py`)

飞书消息发送工具，支持普通消息和彩色卡片：

```python
from data.utils.lark_bot import sender, sender_colourful

# 发送普通消息（使用环境变量中的 LARKBOT_ID）
sender("这是一条测试消息", title="通知标题")

# 发送彩色卡片消息
sender_colourful(url, "# 标题\n内容", title="告警")
```

#### RedisDB (`utils/redisdb.py`)

Redis 连接池管理（单例模式，线程安全）：
- 模块级单例：全局共享连接池，避免重复创建
- 双重检查锁定：确保线程安全初始化
- 连接池配置：最大 10 个连接，5 秒超时
- 自动认证测试：初始化时测试连接

```python
from data.utils.redisdb import redis_cli, close_redis

# 获取 Redis 客户端（自动创建连接池）
redis_client = redis_cli()

# 使用 Redis
redis_client.set("key", "value")
value = redis_client.get("key")

# 程序退出时关闭连接（可选）
close_redis()
```

#### SpiderFailedAlert (`utils/spider_failed_alert.py`)

爬虫失败告警装饰器：
- 异常捕获和告警：自动捕获异常并发送飞书通知
- Redis 去重机制：24 小时内单个爬虫的故障只告警一次
- 降级处理：Redis 不可用时仍会发送告警（每次都会发送）
- 需要环境变量：`SPIDER_ALERT_WEBHOOK_ID`

```python
from data.utils.spider_failed_alert import ErrorMonitor

@ErrorMonitor(spider_name="my_spider", user="username")
def my_crawler_function():
    # 如果发生异常，会自动发送飞书告警
    # 24 小时内相同爬虫的异常只会告警一次（需要 Redis 支持）
    pass
```

## 数据获取策略

**当前实现**：主要使用 REST API + SQLite 缓存架构。WebSocket 客户端已实现但未在分析器中使用。

```
┌─────────────────┐
│   数据请求      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     命中    ┌─────────────────┐
│ BTC 内存缓存    │────────────▶│ 返回缓存数据    │
│ (LRU, 20条)     │             └─────────────────┘
└────────┬────────┘
         │ 未命中
         ▼
┌─────────────────┐     有效    ┌─────────────────┐
│ SQLite 缓存检查 │────────────▶│ 返回缓存数据    │
└────────┬────────┘             └─────────────────┘
         │ 无/过期
         ▼
┌─────────────────┐             ┌─────────────────┐
│ REST API 下载   │────────────▶│ 存入 SQLite     │
│ (增量更新)      │             │ + BTC 内存缓存  │
└─────────────────┘             └─────────────────┘
```

**说明**：
- BTC 数据优先使用内存缓存（LRU，线程安全）
- 其他数据直接从 SQLite 缓存或 REST API 获取
- REST API 支持增量下载，只下载缺失部分
- WebSocket 客户端可用于实时数据订阅，但当前分析器未使用

## 性能优化

| 优化项 | 说明 | 效果 |
|--------|------|------|
| SQLite 缓存 | 历史数据持久化存储 | 避免重复下载，大幅减少 API 调用 |
| 增量更新 | 只下载缺失的数据 | 后续运行只需下载增量部分 |
| BTC 内存缓存 | LRU 缓存（最大 20 条） | 频繁访问的 BTC 数据零延迟获取 |
| 线程安全设计 | 支持并发访问 | 多线程环境下安全高效 |
| 速率限制 | 自动控制请求频率（500ms） | 避免 429 错误，稳定可靠 |
| 安全阀机制 | 最大请求次数限制、时间戳检测 | 防止死循环和异常情况 |

### 性能基准测试

**测试环境**：
- CPU: Apple M1 / Intel i5 或更高
- 内存: 8GB RAM
- 网络: 100Mbps
- Python: 3.12+

**首次运行（全量下载）**：
```
数据周期: 60 天
时间周期: 1m, 5m
交易对数量: 120

总耗时: ~15-20 分钟
API 调用次数: ~800-1000 次
数据库大小: ~500-800 MB
内存占用: ~200-300 MB
CPU 占用: ~10-20%（下载期间）
```

**后续运行（增量更新）**：
```
数据周期: 60 天
增量时间: 1 小时
交易对数量: 120

总耗时: ~2-3 分钟
API 调用次数: ~10-20 次
内存占用: ~150-200 MB
CPU 占用: ~5-10%
```

**分析性能**：
```
单个币种分析:
- 数据加载: 10-50ms（缓存命中）/ 100-500ms（缓存未命中）
- 相关系数计算: 5-20ms
- 总耗时: 15-100ms

全量分析 (120 个交易对):
- 总耗时: ~90-120 秒
- 平均每币种: ~0.8-1.0 秒
- 瓶颈: API 请求速率限制（500ms 间隔）
```

### 性能优化建议

#### 1. 调整缓存大小

如果分析的时间周期和数据周期组合较多，可增加 BTC 缓存大小：

```python
# 在 manager.py 中修改
class DataManager:
    MAX_BTC_CACHE_SIZE = 50  # 默认 20，可根据需要调整
```

**影响**：
- 缓存大小 20 → 内存占用约 50MB
- 缓存大小 50 → 内存占用约 125MB

#### 2. 并发下载（实验性）

对于大量交易对，可考虑并发下载（需自行实现）：

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(analyzer.one_coin_analysis, coin) 
               for coin in coins]
```

**注意**：
- 需要控制并发数（建议 ≤ 3）避免触发速率限制
- SQLiteCache 已支持多线程，无需额外处理

#### 3. 数据库优化

如果数据库文件过大（> 5GB），考虑定期清理旧数据：

```python
# 清理 90 天前的数据
cutoff_time = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)
cache.execute(f"DELETE FROM ohlcv WHERE timestamp < {cutoff_time}")
cache.execute("VACUUM")  # 回收空间
```

#### 4. 网络优化

- 使用稳定的网络连接
- 如频繁出现超时，可增加超时时间：
```python
client = RESTClient(timeout=60000)  # 60 秒
```

### 资源占用监控

**实时监控脚本**：

```python
import psutil
import os

def monitor_resources():
    process = psutil.Process(os.getpid())
    
    print(f"CPU: {process.cpu_percent()}%")
    print(f"内存: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    print(f"线程数: {process.num_threads()}")
    
    # 数据库大小
    if os.path.exists("hyperliquid_data.db"):
        db_size = os.path.getsize("hyperliquid_data.db") / 1024 / 1024
        print(f"数据库大小: {db_size:.2f} MB")
```

### 示例：60 天数据下载

**详细时间分解**：

| 阶段 | 耗时 | API 调用 | 说明 |
|------|------|---------|------|
| BTC 数据预取 | 2-3 分钟 | 40-60 次 | 预取 8 个组合（1m/5m × 1d/7d/30d/60d） |
| 首个币种分析 | 1-2 分钟 | 40-60 次 | 首次下载全量数据 |
| 后续币种分析 | 0.5-1 秒/个 | 0-2 次/个 | 大部分数据已缓存 |
| 异常检测 | < 10ms/个 | 0 | 纯计算，无 IO |
| 飞书通知 | 100-500ms/次 | 1 次 | 仅异常币种发送 |

**首次运行**：~800 次 API 调用（全量下载 + 缓存）
**后续运行**：~10 次 API 调用（只下载增量部分）
**限流风险**：极低（内置速率限制和安全阀）

## 注意事项

### 异常检测阈值

分析器使用以下阈值来识别异常币种：
- **长期相关系数阈值**：`0.6`（7d/30d/60d 周期中至少有一个 > 0.6）
- **短期相关系数阈值**：`0.3`（1d 周期中最小相关系数 < 0.3）
- **相关系数差值阈值**：`0.5`（长期最大 - 短期最小 > 0.5）
- **延迟检测**：短期存在明显滞后（τ* > 0）时也会触发

如需调整阈值，可在代码中修改 `DelayCorrelationAnalyzer` 类的类属性。

### 日志文件

分析器会生成日志文件 `analyzer.log`：
- 日志轮转：文件大小达到 10MB 时自动轮转
- 备份数量：保留最近 5 个备份文件
- 日志级别：默认 INFO，使用 `--debug` 参数可启用 DEBUG 级别

### 线程安全

以下模块已实现线程安全：
- **SQLiteCache**：使用线程本地存储，每个线程独立的数据库连接
- **DataManager**：BTC 缓存使用双重检查锁定模式
- **RedisDB**：使用模块级单例和双重检查锁定

### hyperliquid.py 命名冲突

如果项目根目录存在 `hyperliquid.py` 文件，会遮蔽 `hyperliquid` SDK 包。

**解决方案**（二选一）：
1. 将 `hyperliquid.py` 重命名为其他名称（如 `hyperliquid_analyzer.py`）
2. 本模块已内置路径修复，会自动处理此问题

### 环境变量配置

需要设置以下环境变量：

```bash
# 环境标识（可选，默认 local）
export ENV=production

# 飞书机器人 ID（用于通知功能）
export LARKBOT_ID=your_bot_id

# Redis 配置（可选）
export REDIS_HOST=127.0.0.1
export REDIS_PASSWORD=your_redis_password

# 爬虫告警 Webhook ID（可选，用于 spider_failed_alert）
export SPIDER_ALERT_WEBHOOK_ID=your_webhook_id
```

**说明**:
- `ENV`: 设置为 `local` 时，定时调度器会直接执行任务而不等待调度时间
- `LARKBOT_ID`: 飞书通知功能必需，用于发送分析结果和告警消息
- `REDIS_HOST`: Redis 主机地址，默认 `127.0.0.1`
- `REDIS_PASSWORD`: Redis 密码，如果 Redis 未设置密码可省略
- `SPIDER_ALERT_WEBHOOK_ID`: 爬虫失败告警功能需要，用于发送异常告警

### 数据要求

分析器对数据有以下要求：
- **最小数据点数**：每个 timeframe/period 组合至少需要 50 个数据点才能进行分析
- **相关系数计算**：至少需要 10 个数据点才能计算相关系数
- **数据对齐**：BTC 和山寨币数据会自动对齐时间索引，只使用共同的时间点

## 故障排查

### 常见问题

#### 1. 导入错误：找不到 hyperliquid 模块

**问题**：
```
ModuleNotFoundError: No module named 'hyperliquid'
```

**原因**：项目根目录存在同名的 `hyperliquid.py` 文件，遮蔽了 SDK 包。

**解决方案**：
- 删除或重命名项目中的 `hyperliquid.py` 文件
- 或使用本模块内置的路径修复功能（已自动处理）

#### 2. 数据库锁定错误

**问题**：
```
sqlite3.OperationalError: database is locked
```

**原因**：多个进程或线程同时访问数据库。

**解决方案**：
- SQLiteCache 已实现线程本地存储，单进程多线程环境下自动处理
- 如果多进程并发，考虑为每个进程使用独立的数据库文件
- 或增加数据库超时时间（已默认设置为 30 秒）

#### 3. API 速率限制（429 错误）

**问题**：
```
ccxt.errors.RateLimitExceeded: hyperliquid GET https://api.hyperliquid.xyz/info 429 Too Many Requests
```

**原因**：请求频率超过交易所限制。

**解决方案**：
- 本模块已内置速率限制（默认 500ms 间隔）
- 如仍然出现，可增加 `rate_limit_ms` 参数：
```python
client = RESTClient(rate_limit_ms=1000)  # 增加到 1 秒
```

#### 4. 飞书通知发送失败

**问题**：
```
WARNING - 飞书通知未发送（未配置）| 币种: ETH/USDC:USDC
```

**原因**：环境变量 `LARKBOT_ID` 未设置。

**解决方案**：
```bash
export LARKBOT_ID=your_bot_id
```

#### 5. Redis 连接失败

**问题**：
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**原因**：Redis 服务未启动或配置错误。

**解决方案**：
- 检查 Redis 服务是否运行：`redis-cli ping`
- 检查环境变量配置：
```bash
export REDIS_HOST=127.0.0.1
export REDIS_PASSWORD=your_password
```
- SpiderFailedAlert 模块会在 Redis 不可用时自动降级

#### 6. 内存占用过高

**问题**：长时间运行后内存占用持续增长。

**原因**：BTC 缓存或其他数据累积。

**解决方案**：
- BTC 内存缓存已实现 LRU 机制（最大 20 条），自动清理旧数据
- 如需手动清理：
```python
manager.clear_btc_cache()
```
- 考虑定期重启监控进程（如每天一次）

#### 7. 数据不足警告

**问题**：
```
WARNING - 数据量不足，跳过 | 币种: XXX/USDC:USDC | 1m/1d
```

**原因**：缓存中的数据点数少于最小要求（50 个点）。

**解决方案**：
- 首次运行时正常，等待数据下载完成
- 如持续出现，检查交易对是否为新上线币种
- 可通过 `--debug` 参数查看详细日志

#### 8. Python 版本不兼容

**问题**：
```
ERROR: This package requires Python >=3.12
```

**原因**：Python 版本低于 3.12。

**解决方案**：
```bash
# 升级 Python
pyenv install 3.12
pyenv local 3.12

# 或使用 uv 管理 Python 版本
uv python install 3.12
```

### 调试技巧

#### 启用详细日志

```bash
.venv/bin/python -m data.main --debug
```

这将启用 DEBUG 级别日志，输出详细的：
- API 请求和响应
- 缓存命中/未命中信息
- 数据对齐和验证过程
- 相关系数计算细节

#### 查看缓存统计

```python
from data import DataManager

manager = DataManager()
stats = manager.get_cache_stats()
print(stats)
```

输出示例：
```python
{
    'sqlite': {
        'BTC/USDC:USDC': {
            '1m': {'count': 43200, 'oldest_ms': 1701234567000, 'newest_ms': 1703826567000},
            '5m': {'count': 8640, 'oldest_ms': 1701234567000, 'newest_ms': 1703826567000}
        }
    },
    'btc_memory_cache': [('1m', '7d'), ('5m', '7d'), ('1m', '30d')]
}
```

#### 测试单个币种

```bash
# 快速测试单个币种，避免遍历所有交易对
.venv/bin/python -m data.main --coin=ETH/USDC:USDC --debug
```

#### 清理缓存

如需从头开始：
```bash
# 删除数据库文件
rm hyperliquid_data.db

# 或在代码中清理特定交易对
cache.clear_symbol("ETH/USDC:USDC", "5m")
```

## 依赖

- `ccxt>=4.5.14` - 交易所 API
- `hyperliquid-python-sdk>=0.8.0` - 官方 SDK（WebSocket）
- `pandas>=2.3.3` - 数据处理
- `numpy>=2.3.4` - 数值计算
- `retry>=0.9.2` - 重试机制
- `matplotlib>=3.10.7` - 数据可视化
- `pyinform>=0.2.0` - 信息论分析
- `redis>=7.1.0` - Redis 支持
- `requests>=2.32.0` - HTTP 请求
- `seaborn>=0.13.2` - 统计可视化

## 许可证

MIT License


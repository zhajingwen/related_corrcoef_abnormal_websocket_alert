# calculate-fake-te

## 概述

本模块是一个**相关系数分析器**，用于分析 Hyperliquid 交易所中山寨币与 BTC 的相关性，识别存在时间差套利机会的异常币种。

**核心功能**：检测短期低相关但长期高相关的币种模式。这类币种与 BTC 在长期趋势上高度相关，但在短期内存在明显滞后，可能存在时间差套利机会。

**技术架构**：采用 REST API + SQLite 缓存的混合架构，提供高效的数据获取和分析能力。WebSocket 客户端已实现但当前未在分析器中使用。

**要求**: Python >= 3.12

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

**示例**：60 天数据下载
- 首次运行：~800 次 API 调用（全量下载 + 缓存）
- 后续运行：~10 次 API 调用（只下载增量部分）
- 限流风险：极低（内置速率限制和安全阀）

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


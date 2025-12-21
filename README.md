# calculate-fake-te

## 概述

本模块提供 Hyperliquid 交易所数据获取的完整解决方案，采用 WebSocket + REST API 混合架构，彻底解决 API 限流问题。

**要求**: Python >= 3.12

## 核心特性

- **SQLite 本地缓存**：历史数据持久化存储，避免重复下载
- **增量更新**：只下载缺失的数据，大幅减少 API 调用
- **WebSocket 实时订阅**：使用官方 SDK，毫秒级数据推送
- **智能数据源选择**：短期数据优先 WebSocket，长期数据使用 REST + 缓存
- **内置速率限制**：自动控制请求频率，避免 429 错误

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
# 分析所有币种
.venv/bin/python -m data.main --mode=analysis

# 分析单个币种（快速测试）
.venv/bin/python -m data.main --coin=ETH/USDC:USDC

# 持续监控模式（每小时分析一次）
.venv/bin/python -m data.main --mode=monitor --interval=3600

# 调试模式（详细日志）
.venv/bin/python -m data.main --debug
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

K 线数据本地缓存，支持：
- 自动创建表结构和索引
- 按交易对/周期存储和查询
- 增量数据追加

```python
from data import SQLiteCache

cache = SQLiteCache("hyperliquid_data.db")
cache.save_ohlcv("BTC/USDC:USDC", "5m", df)
df = cache.get_ohlcv("BTC/USDC:USDC", "5m", since_ms=1234567890000)
```

### RESTClient (`rest_client.py`)

带速率限制的 REST API 客户端：
- 基于 ccxt，启用 `enableRateLimit`
- 自动重试（10 次，指数退避）
- 与 SQLiteCache 集成，自动缓存

```python
from data import RESTClient, SQLiteCache

cache = SQLiteCache()
client = RESTClient(cache=cache)
df = client.fetch_ohlcv("BTC/USDC:USDC", "5m", "7d")
```

### WebSocketClient (`websocket_client.py`)

实时数据订阅客户端：
- 封装官方 `hyperliquid-python-sdk`
- 支持 K 线数据订阅
- 内存缓存（最近 1000 根 K 线）

```python
from data import WebSocketClient

ws = WebSocketClient()
ws.start()
ws.subscribe_candles("BTC", "5m")
# ... 等待数据
df = ws.get_cached_dataframe("BTC", "5m")
ws.stop()
```

### DataManager (`manager.py`)

统一数据管理器，智能选择数据源：

```python
from data import DataManager

manager = DataManager()
manager.initialize()

# 自动选择最优数据源
df = manager.get_ohlcv("BTC/USDC:USDC", "5m", "7d")

# 获取 BTC 数据（带内存缓存）
btc_df = manager.get_btc_data("5m", "7d")

manager.shutdown()
```

### DelayCorrelationAnalyzer (`analyzer.py`)

相关系数分析器：
- 分析山寨币与 BTC 的皮尔逊相关系数
- 识别短期低相关但长期高相关的异常币种
- 支持飞书通知

```python
from data import DelayCorrelationAnalyzer

analyzer = DelayCorrelationAnalyzer()
analyzer.run()  # 分析所有币种

# 或分析单个币种
analyzer.run_single("ETH/USDC:USDC")
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

## 数据获取策略

```
┌─────────────────┐
│   数据请求      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     是      ┌─────────────────┐
│ 短期数据(1d)?   │────────────▶│ WebSocket 缓存  │
└────────┬────────┘             └─────────────────┘
         │ 否
         ▼
┌─────────────────┐     有效    ┌─────────────────┐
│ SQLite 缓存检查 │────────────▶│ 返回缓存数据    │
└────────┬────────┘             └─────────────────┘
         │ 无/过期
         ▼
┌─────────────────┐             ┌─────────────────┐
│ REST API 下载   │────────────▶│ 存入 SQLite     │
└─────────────────┘             └─────────────────┘
```

## 性能对比

| 指标 | 原版 | 新版（本模块） |
|------|------|----------------|
| 首次运行 | 全量下载 | 全量下载 + 缓存 |
| 后续运行 | 重复全量下载 | 只下载增量 |
| 实时数据 | REST 轮询 | WebSocket 推送 |
| 限流风险 | 高 | 极低 |
| 60天数据 | ~800 次 API | 首次 ~800，后续 ~10 次 |

## 注意事项

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
```

**说明**:
- `ENV`: 设置为 `local` 时，定时调度器会直接执行任务而不等待调度时间
- `LARKBOT_ID`: 飞书通知功能必需，用于发送分析结果和告警消息
- `REDIS_HOST`: Redis 主机地址，默认 `127.0.0.1`
- `REDIS_PASSWORD`: Redis 密码，如果 Redis 未设置密码可省略

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


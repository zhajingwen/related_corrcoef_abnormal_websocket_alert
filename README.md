# Hyperliquid 相关系数异常监控与告警

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

本项目（**Delay Correlation Analyzer**）专注于分析 **Hyperliquid** 交易所中山寨币与 **BTC/USDC:USDC** 的皮尔逊相关性。其核心目标是识别"**短期低相关但长期高相关**"且可能存在**时间差（滞后关系）**的异常币种，通过**飞书机器人**实时推送告警，帮助发现潜在的滞后套利或补涨机会。

---

## ⚡ 快速上手

只需 3 步即可开始使用：

```bash
# 1. 安装依赖（需要 Python 3.12+）
uv sync

# 2. 运行全量分析
python -m qff.main --mode=analysis

# 3. （可选）配置飞书告警
export LARKBOT_ID=your_bot_id
```

**预期输出：**
```
============================================================
Hyperliquid 相关系数分析器
模式: analysis
交易所: hyperliquid
数据库: hyperliquid_data.db
============================================================
预取 BTC 历史数据...
发现 150 个 USDC 永续合约交易对
分析进度: 38/150 (25%)
...
发现异常币种 | 交易所: hyperliquid | 币种: XXX/USDC:USDC | 差值: 0.65
分析完成 | 总数: 150 | 异常: 3 | 跳过: 2 | 耗时: 180.5s
```

---

## 🚀 核心特性

- **多维异常检测**：自动识别短期（如 1d）低相关（<0.3）但长期（如 7d/30d/60d）高相关（>0.6）的异常模式。
- **最优延迟 $\tau^*$ 计算**：在 $0 \dots 48$ 个时间单位窗口内寻找使相关系数最大化的延迟，精准量化山寨币相对 BTC 的滞后时间。
- **高效数据流架构**：
    - **REST + SQLite 增量更新**：基于 `ccxt` 获取数据并持久化至本地 SQLite，后续运行仅请求缺失的增量部分，大幅减少 API 调用。
    - **BTC LRU 内存缓存**：针对频繁访问的 BTC 数据，内置带线程锁保护的 LRU 缓存（默认 **100** 条），实现零延迟数据读取。
- **稳健的告警机制**：支持飞书消息卡片推送；若未配置或发送失败，会自动将告警详情落盘至 `alerts/` 目录。
- **线程安全设计**：所有核心模块（Cache, Manager, Redis）均支持在多线程环境下并发访问。

---

## 📂 项目结构

```text
qff/
├── __init__.py          # 模块导出
├── pyproject.toml       # 项目元数据与依赖管理 (uv)
├── uv.lock              # 依赖锁定文件
├── main.py              # 命令行入口：支持 analysis (一次性) 与 monitor (持续监控)
├── analyzer.py          # DelayCorrelationAnalyzer：核心算法与告警逻辑
├── manager.py           # DataManager：统一数据访问中心 + BTC LRU 缓存
├── rest_client.py       # REST 客户端：带限流与增量下载逻辑
├── sqlite_cache.py      # SQLite 缓存：持久化 K 线数据
├── websocket_client.py  # WebSocket 客户端：实时订阅 (SDK 封装，保留扩展)
└── utils/
    ├── __init__.py      # 工具模块初始化
    ├── config.py        # 环境变量加载
    ├── lark_bot.py      # 飞书消息推送工具
    ├── redisdb.py       # Redis 连接池 (可选，用于告警去重)
    └── scheduler.py     # 定时任务装饰器
```

---

## 🛠️ 详细使用指南

### 1. 环境准备

本项目要求 **Python 3.12+**。推荐使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理：

```bash
# 克隆项目
git clone <repo_url>
cd qff

# 安装依赖
uv sync
```

**核心依赖：**
| 包名 | 版本 | 说明 |
| :--- | :--- | :--- |
| ccxt | >= 4.5.14 | 加密货币交易所 API |
| numpy | >= 2.3.4 | 数值计算 |
| pandas | >= 2.3.3 | 数据分析 |
| redis | >= 7.1.0 | 可选，用于告警去重 |

### 2. 运行分析

项目采用包结构，需要使用 `python -m qff.main` 方式运行。

**常用命令：**

```bash
# 全量分析：检查所有 USDC 永续合约
python -m qff.main --mode=analysis

# 持续监控：每小时自动运行一次，发现异常即告警
python -m qff.main --mode=monitor --interval=3600

# 指定币种：仅分析特定交易对（适合测试）
python -m qff.main --coin=ETH/USDC:USDC

# 指定交易所：使用其他 ccxt 支持的交易所
python -m qff.main --exchange=binance

# 调试模式：开启 DEBUG 日志，查看详细执行过程
python -m qff.main --debug
```

### 3. 命令行参数

| 参数 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `--mode` | 运行模式：`analysis` (单次) 或 `monitor` (持续) | `analysis` |
| `--coin` | 指定分析单个币种（如 `ETH/USDC:USDC`） | - |
| `--exchange` | 交易所名称（基于 ccxt 支持的交易所） | `hyperliquid` |
| `--db` | SQLite 数据库路径 | `hyperliquid_data.db` |
| `--timeframes`| K 线周期（逗号分隔） | `1m,5m` |
| `--periods` | 数据统计周期（逗号分隔） | `1d,7d,30d,60d` |
| `--interval` | 监控模式下的运行间隔（秒） | `3600` |
| `--debug` | 启用详细调试日志 | - |

---

## 🧠 异常检测逻辑

位于 `analyzer.py: DelayCorrelationAnalyzer`。

### 判定标准
1. **长期高相关**：在 `7d`, `30d`, `60d` 周期中，最大相关系数 > **0.6**。
2. **短期低相关**：在 `1d` 周期中，最小相关系数 < **0.3**。
3. **显著差值**：(长期最大相关 - 短期最小相关) > **0.5**。
4. **滞后判定**：若短期（`1d`）计算出的最优延迟 $\tau^* > 0$，同样视为潜在异常。

### 核心算法：最优延迟 $\tau^*$
通过滑动窗口移动 BTC 的收益率序列，计算 $Corr(BTC_{t}, ALT_{t+\tau})$，寻找使相关系数最大的 $\tau$。

---

## 📊 性能基准 (典型值)

| 场景 | API 调用 | 耗时 | 说明 |
| :--- | :--- | :--- | :--- |
| **首次运行 (全量)** | ~800+ 次 | 15-20 min | 受限于 500ms 请求限速 |
| **后续运行 (增量)** | ~10-20 次 | 2-3 min | 仅下载最新增量数据 |
| **单币种分析** | 0-2 次 | < 1s | 缓存命中时计算极快 |

---

## ⚙️ 环境变量配置

在运行前，可以通过以下环境变量配置功能：

```bash
# 飞书机器人 Webhook ID (用于推送告警，未配置则告警保存至 alerts/ 目录)
export LARKBOT_ID=your_bot_id

# Redis 配置 (可选，用于告警去重)
export REDIS_HOST=127.0.0.1      # 默认值
export REDIS_PASSWORD=your_password

# 运行环境
# - local: 开发模式，禁用定时器等待，直接执行
# - production: 生产模式
export ENV=production
```

**配置优先级说明：**
- `LARKBOT_ID` 未设置时，告警信息会自动保存到 `alerts/` 目录作为备份
- `REDIS_HOST` 未设置时默认使用 `127.0.0.1`
- `ENV` 未设置时默认为 `local`

---

## ❓ 常见问题 (Troubleshooting)

### 429 Too Many Requests
项目内置了 500ms 的限流间隔。如网络环境特殊，可在 `rest_client.py` 中调大 `rate_limit_ms` 参数。

### 数据不足跳过
单次分析至少需要 **100** 个有效数据点（可在 `analyzer.py` 中通过 `MIN_DATA_POINTS_FOR_ANALYSIS` 调整）。新上线币种可能因历史数据不足被暂时忽略。

### SQLite 锁定
项目采用线程本地连接（默认超时 60 秒）。若使用多进程（如 `multiprocessing`）访问同一数据库，请确保使用不同的文件名。

### 飞书通知未发送
检查 `LARKBOT_ID` 环境变量是否正确设置。未配置时，告警会自动保存到 `alerts/` 目录。

---

## 📄 许可证

[MIT License](LICENSE)

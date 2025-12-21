"""
Data 模块

提供 WebSocket + REST 混合数据架构，支持：
- SQLite 本地缓存
- REST API 历史数据下载（带速率限制）
- WebSocket 实时数据订阅
- 统一的数据管理接口
- 相关系数分析器

使用示例:
    import DataManager, DelayCorrelationAnalyzer
    
    # 使用数据管理器获取数据
    manager = DataManager()
    manager.initialize()
    df = manager.get_ohlcv("BTC/USDC:USDC", "5m", "7d")
    manager.shutdown()
    
    # 运行分析器
    analyzer = DelayCorrelationAnalyzer()
    analyzer.run()
"""

import sys
import os


from .sqlite_cache import SQLiteCache
from .rest_client import RESTClient
from .websocket_client import WebSocketClient
from .manager import DataManager
from .analyzer import DelayCorrelationAnalyzer

__all__ = [
    "SQLiteCache",
    "RESTClient",
    "WebSocketClient",
    "DataManager",
    "DelayCorrelationAnalyzer",
]

__version__ = "1.0.0"


"""
WebSocket 客户端模块

封装 Hyperliquid 官方 SDK 的 WebsocketManager，提供 K 线数据实时订阅功能。
支持多交易对订阅、内存缓存、自动重连。
"""

import logging
import asyncio
import atexit
import weakref
from collections import deque
from functools import partial
from typing import Optional, Callable
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

from hyperliquid.info import Info
from hyperliquid.utils import constants

# 全局注册表，用于跟踪所有 WebSocketClient 实例以便在程序退出时清理
_ws_client_instances: weakref.WeakSet = weakref.WeakSet()


def _cleanup_all_ws_clients():
    """程序退出时清理所有 WebSocket 客户端连接"""
    for client in _ws_client_instances:
        try:
            client.stop()
        except Exception:
            pass


atexit.register(_cleanup_all_ws_clients)


class WebSocketClient:
    """
    Hyperliquid WebSocket 客户端
    
    封装官方 SDK，提供 K 线数据实时订阅和内存缓存功能。
    """
    
    # 支持的 K 线周期
    SUPPORTED_INTERVALS = [
        "1m", "3m", "5m", "15m", "30m",
        "1h", "2h", "4h", "8h", "12h",
        "1d", "3d", "1w", "1M"
    ]
    
    def __init__(self, max_cache_size: int = 1000, testnet: bool = False):
        """
        初始化 WebSocket 客户端
        
        Args:
            max_cache_size: 每个交易对/周期的最大缓存 K 线数量
            testnet: 是否使用测试网
        """
        self.max_cache_size = max_cache_size
        self.testnet = testnet
        self.base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        
        # 数据缓存: {(coin, interval): deque([candle_data, ...])}
        self.data_cache: dict[tuple[str, str], deque] = {}
        
        # 订阅状态
        self.subscriptions: set[tuple[str, str]] = set()
        
        # Info 客户端（用于 WebSocket）
        self._info: Optional[Info] = None
        self._running = False
        
        # 回调函数
        self._callbacks: dict[tuple[str, str], list[Callable]] = {}
        
        # 注册到全局跟踪器，确保程序退出时能够清理资源
        _ws_client_instances.add(self)
        
        logger.info(f"WebSocket 客户端初始化 | 测试网: {testnet} | 缓存大小: {max_cache_size}")
    
    def start(self):
        """启动 WebSocket 连接"""
        if self._running:
            logger.warning("WebSocket 已在运行中")
            return
        
        self._info = Info(self.base_url, skip_ws=False)
        self._running = True
        logger.info("WebSocket 连接已启动")
    
    def stop(self):
        """停止 WebSocket 连接"""
        if not self._running:
            return
        
        # 1. 先取消所有活跃订阅，确保服务器端连接清理
        active_subs = list(self.subscriptions)
        for coin, interval in active_subs:
            try:
                self.unsubscribe_candles(coin, interval)
            except Exception as e:
                logger.debug(f"停止时取消订阅失败 (正常现象) | {coin} | {interval} | {e}")
        
        self._running = False
        self.subscriptions.clear()
        self._callbacks.clear()  # 清理所有回调函数，避免内存泄漏
        
        if self._info:
            try:
                # 尝试关闭 WebSocket 连接
                # 根据 hyperliquid SDK 的实现方式尝试不同的关闭方法
                self._close_info_connection(self._info)
            except Exception as e:
                logger.warning(f"关闭 WebSocket 连接时出错: {e}")
            finally:
                self._info = None
        
        # 清理数据缓存以释放内存
        self.data_cache.clear()
        
        logger.info("WebSocket 连接已停止")
    
    @staticmethod
    def _close_info_connection(info: Info):
        """
        尝试关闭 Info 对象的 WebSocket 连接
        
        hyperliquid SDK 的 Info 对象可能有多种关闭方式，
        此方法尝试所有可能的方式以确保连接被正确关闭。
        """
        close_attempts = []
        
        # 方法1: 直接调用 close 方法
        if hasattr(info, 'close'):
            try:
                info.close()
                logger.debug("WebSocket 连接已通过 close() 方法关闭")
                return
            except Exception as e:
                close_attempts.append(f"close(): {type(e).__name__}: {e}")
        
        # 方法2: 调用 disconnect 方法
        if hasattr(info, 'disconnect'):
            try:
                info.disconnect()
                logger.debug("WebSocket 连接已通过 disconnect() 方法关闭")
                return
            except Exception as e:
                close_attempts.append(f"disconnect(): {type(e).__name__}: {e}")
        
        # 方法3: 关闭内部 ws 对象
        if hasattr(info, 'ws') and info.ws:
            try:
                if hasattr(info.ws, 'close'):
                    info.ws.close()
                    logger.debug("WebSocket 连接已通过 ws.close() 方法关闭")
            except Exception as e:
                close_attempts.append(f"ws.close(): {type(e).__name__}: {e}")
        
        # 方法4: 关闭 websocket manager
        if hasattr(info, 'ws_manager') and info.ws_manager:
            try:
                if hasattr(info.ws_manager, 'close'):
                    info.ws_manager.close()
                    logger.debug("WebSocket 连接已通过 ws_manager.close() 方法关闭")
                elif hasattr(info.ws_manager, 'stop'):
                    info.ws_manager.stop()
                    logger.debug("WebSocket 连接已通过 ws_manager.stop() 方法关闭")
            except Exception as e:
                close_attempts.append(f"ws_manager: {type(e).__name__}: {e}")
        
        # 方法5: 尝试关闭内部线程（如果存在）
        if hasattr(info, '_thread') and info._thread:
            try:
                if hasattr(info._thread, 'join'):
                    info._thread.join(timeout=1.0)  # 等待最多1秒
                    logger.debug("WebSocket 内部线程已停止")
            except Exception as e:
                close_attempts.append(f"_thread.join(): {type(e).__name__}: {e}")
        
        # 如果所有方法都失败，记录详细的失败信息
        if close_attempts:
            logger.warning(f"WebSocket 关闭尝试遇到错误: {'; '.join(close_attempts)}")
    
    def __del__(self):
        """析构函数：确保资源被释放"""
        try:
            self.stop()
        except Exception:
            pass
    
    def __enter__(self):
        """支持 with 语句"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出 with 语句时停止连接"""
        self.stop()
        return False
    
    def subscribe_candles(
        self,
        coin: str,
        interval: str,
        callback: Optional[Callable] = None
    ) -> bool:
        """
        订阅 K 线数据
        
        Args:
            coin: 币种符号，如 "BTC"、"ETH"
            interval: K 线周期，如 "5m"、"1h"
            callback: 收到数据时的回调函数（可选）
        
        Returns:
            是否订阅成功
        """
        if not self._running:
            logger.error("WebSocket 未启动，请先调用 start()")
            return False
        
        if interval not in self.SUPPORTED_INTERVALS:
            logger.error(f"不支持的 K 线周期: {interval}，支持: {self.SUPPORTED_INTERVALS}")
            return False
        
        cache_key = (coin, interval)
        
        # 初始化缓存
        if cache_key not in self.data_cache:
            self.data_cache[cache_key] = deque(maxlen=self.max_cache_size)
        
        # 注册回调（去重检查）
        if callback:
            if cache_key not in self._callbacks:
                self._callbacks[cache_key] = []
            # 检查回调是否已存在，避免重复注册
            if callback not in self._callbacks[cache_key]:
                self._callbacks[cache_key].append(callback)
            else:
                logger.debug(f"回调已存在，跳过重复注册 | {coin} | {interval}")
        
        # 订阅
        try:
            self._info.subscribe(
                {
                    "type": "candle",
                    "coin": coin,
                    "interval": interval
                },
                partial(self._handle_candle, cache_key)
            )
            self.subscriptions.add(cache_key)
            logger.info(f"已订阅 K 线 | {coin} | {interval}")
            return True
        except Exception as e:
            logger.error(f"订阅失败 | {coin} | {interval} | {e}")
            return False
    
    def unsubscribe_candles(self, coin: str, interval: str):
        """
        取消订阅 K 线数据
        
        Args:
            coin: 币种符号
            interval: K 线周期
        """
        cache_key = (coin, interval)
        
        if cache_key in self.subscriptions:
            try:
                self._info.unsubscribe(
                    {
                        "type": "candle",
                        "coin": coin,
                        "interval": interval
                    }
                )
                self.subscriptions.discard(cache_key)
                self._callbacks.pop(cache_key, None)  # 清理该订阅的回调函数
                logger.info(f"已取消订阅 | {coin} | {interval}")
            except Exception as e:
                logger.error(f"取消订阅失败 | {coin} | {interval} | {e}")
    
    def _handle_candle(self, cache_key: tuple[str, str], data: dict):
        """处理接收到的 K 线数据"""
        try:
            # 解析 K 线数据
            candle = self._parse_candle(data)
            if candle is None:
                return
            
            # 更新缓存
            cache = self.data_cache.get(cache_key)
            if cache is not None:
                # 检查是否是更新现有 K 线还是新 K 线
                if cache and cache[-1]["timestamp"] == candle["timestamp"]:
                    # 更新最后一根 K 线
                    cache[-1] = candle
                else:
                    # 添加新 K 线
                    cache.append(candle)
            
            # 触发回调
            callbacks = self._callbacks.get(cache_key, [])
            for cb in callbacks:
                try:
                    cb(candle)
                except Exception as e:
                    logger.error(f"回调执行失败 | {cache_key} | {e}")
        
        except Exception as e:
            logger.error(f"处理 K 线数据失败 | {cache_key} | {e}")
    
    @staticmethod
    def _parse_candle(data: dict) -> Optional[dict]:
        """
        解析 K 线数据
        
        Args:
            data: 原始数据
        
        Returns:
            解析后的 K 线字典，包含 timestamp, open, high, low, close, volume
        """
        try:
            # 根据官方 SDK 的数据格式解析
            # 格式可能是: {"t": timestamp, "o": open, "h": high, "l": low, "c": close, "v": volume}
            # 或者: {"time": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}
            
            if "data" in data:
                candle_data = data["data"]
            else:
                candle_data = data
            
            # 尝试多种格式
            if "t" in candle_data:
                return {
                    "timestamp": int(candle_data["t"]),
                    "open": float(candle_data["o"]),
                    "high": float(candle_data["h"]),
                    "low": float(candle_data["l"]),
                    "close": float(candle_data["c"]),
                    "volume": float(candle_data.get("v", 0))
                }
            elif "time" in candle_data:
                return {
                    "timestamp": int(candle_data["time"]),
                    "open": float(candle_data["open"]),
                    "high": float(candle_data["high"]),
                    "low": float(candle_data["low"]),
                    "close": float(candle_data["close"]),
                    "volume": float(candle_data.get("volume", 0))
                }
            else:
                logger.warning(f"未知的 K 线数据格式: {candle_data}")
                return None
        
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"解析 K 线数据失败: {e} | 数据: {data}")
            return None
    
    def get_cached_data(
        self,
        coin: str,
        interval: str,
        count: Optional[int] = None
    ) -> list[dict]:
        """
        获取缓存的 K 线数据
        
        Args:
            coin: 币种符号
            interval: K 线周期
            count: 返回的数量（从最新开始），None 表示全部
        
        Returns:
            K 线数据列表
        """
        cache_key = (coin, interval)
        cache = self.data_cache.get(cache_key)
        
        if cache is None:
            return []
        
        data = list(cache)
        if count is not None:
            data = data[-count:]
        
        return data
    
    def get_cached_dataframe(
        self,
        coin: str,
        interval: str,
        count: Optional[int] = None
    ) -> pd.DataFrame:
        """
        获取缓存的 K 线数据（DataFrame 格式）
        
        Args:
            coin: 币种符号
            interval: K 线周期
            count: 返回的数量
        
        Returns:
            DataFrame，索引为 Timestamp
        """
        data = self.get_cached_data(coin, interval, count)
        
        if not data:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        
        df = pd.DataFrame(data)
        df["Timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(None)
        df = df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume"
        })
        df = df.set_index("Timestamp")[["Open", "High", "Low", "Close", "Volume"]]
        df = df.sort_index()
        
        return df
    
    def has_enough_data(self, coin: str, interval: str, required_bars: int) -> bool:
        """
        检查缓存中是否有足够的数据
        
        Args:
            coin: 币种符号
            interval: K 线周期
            required_bars: 需要的 K 线数量
        
        Returns:
            是否有足够数据
        """
        cache_key = (coin, interval)
        cache = self.data_cache.get(cache_key)
        
        if cache is None:
            return False
        
        return len(cache) >= required_bars
    
    def get_subscription_status(self) -> dict:
        """获取订阅状态"""
        return {
            "running": self._running,
            "subscriptions": list(self.subscriptions),
            "cache_sizes": {
                f"{coin}_{interval}": len(cache)
                for (coin, interval), cache in self.data_cache.items()
            }
        }
    
    @property
    def is_running(self) -> bool:
        """WebSocket 是否正在运行"""
        return self._running


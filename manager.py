"""
数据管理器模块

统一管理 REST 历史数据，提供一致的数据访问接口。
自动处理 SQLite 缓存和增量更新。
"""

import logging
import threading
from collections import OrderedDict
from typing import Optional
import pandas as pd

from .sqlite_cache import SQLiteCache
from .rest_client import RESTClient

logger = logging.getLogger(__name__)

# BTC 交易对符号常量
BTC_SYMBOL = "BTC/USDC:USDC"


class DataManager:
    """
    数据管理器
    
    使用 REST API 获取数据，通过 SQLite 缓存避免重复下载。
    """
    
    # BTC 内存缓存最大条目数
    MAX_BTC_CACHE_SIZE = 100
    # 下载锁最大数量（防止内存泄漏）
    MAX_DOWNLOAD_LOCKS = 200
    
    def __init__(
        self,
        exchange_name: str = "hyperliquid",
        db_path: str = "hyperliquid_data.db"
    ):
        """
        初始化数据管理器
        
        Args:
            exchange_name: 交易所名称
            db_path: SQLite 数据库路径
        """
        self.exchange_name = exchange_name
        
        # 初始化 SQLite 缓存
        self.cache = SQLiteCache(db_path)
        
        # 初始化 REST 客户端
        self.rest_client = RESTClient(
            exchange_name=exchange_name,
            cache=self.cache
        )
        
        # BTC 数据缓存（使用 OrderedDict 实现 LRU 缓存，避免内存无限增长）
        self._btc_cache: OrderedDict[tuple[str, str], pd.DataFrame] = OrderedDict()
        self._btc_cache_lock = threading.Lock()  # 保护 BTC 缓存的线程锁
        
        # 下载锁：防止同一数据被多个线程重复下载
        # 使用字典为每个缓存键维护独立的锁
        self._download_locks: dict[tuple[str, str], threading.Lock] = {}
        self._download_locks_lock = threading.Lock()  # 保护 _download_locks 的元锁
        
        # 缓存命中率统计
        self._cache_stats = {'hits': 0, 'misses': 0}
        self._cache_stats_lock = threading.Lock()  # 保护缓存统计的锁
        
        logger.info(f"数据管理器初始化 | 交易所: {exchange_name} | 数据库: {db_path}")
    
    def initialize(self):
        """初始化（清除 BTC 内存缓存，确保数据新鲜）"""
        self.clear_btc_cache()
    
    def shutdown(self):
        """关闭（保留接口兼容性）"""
        pass
    
    def get_ohlcv(self, symbol: str, timeframe: str, period: str) -> pd.DataFrame:
        """
        获取 OHLCV 数据
        
        Args:
            symbol: 交易对，如 "BTC/USDC:USDC"
            timeframe: K 线周期，如 "5m"
            period: 数据周期，如 "60d"
        
        Returns:
            包含 OHLCV 数据的 DataFrame
        """
        logger.debug(f"获取数据 | {symbol} | {timeframe} | {period}")
        return self.rest_client.fetch_ohlcv(symbol, timeframe, period)
    
    def _get_download_lock(self, cache_key: tuple[str, str]) -> threading.Lock:
        """
        获取或创建指定缓存键的下载锁

        Args:
            cache_key: 缓存键 (timeframe, period)

        Returns:
            该缓存键对应的下载锁
        """
        with self._download_locks_lock:
            if cache_key not in self._download_locks:
                # 清理过期的锁（防止内存泄漏）
                if len(self._download_locks) >= self.MAX_DOWNLOAD_LOCKS:
                    # 移除一半的旧锁（只移除未被持有的锁）
                    keys_to_remove = []
                    for key, lock in list(self._download_locks.items()):
                        if not lock.locked():
                            keys_to_remove.append(key)
                            if len(keys_to_remove) >= self.MAX_DOWNLOAD_LOCKS // 2:
                                break
                    for key in keys_to_remove:
                        del self._download_locks[key]
                    if keys_to_remove:
                        logger.debug(f"清理了 {len(keys_to_remove)} 个过期的下载锁")

                self._download_locks[cache_key] = threading.Lock()
            return self._download_locks[cache_key]
    
    def get_btc_data(self, timeframe: str, period: str) -> Optional[pd.DataFrame]:
        """
        获取 BTC 数据（带 LRU 内存缓存，线程安全）
        
        使用下载锁模式，确保同一数据只下载一次，避免多线程环境下的重复下载。
        
        Args:
            timeframe: K 线周期
            period: 数据周期
        
        Returns:
            BTC 的 OHLCV 数据
        """
        cache_key = (timeframe, period)
        
        # 第一次检查（快速路径，无下载锁）
        with self._btc_cache_lock:
            if cache_key in self._btc_cache:
                # 记录缓存命中
                with self._cache_stats_lock:
                    self._cache_stats['hits'] += 1
                # 移到末尾（标记为最近使用）
                self._btc_cache.move_to_end(cache_key)
                logger.debug(f"BTC 数据缓存命中 | {timeframe}/{period}")
                return self._btc_cache[cache_key].copy(deep=True)
        
        # 缓存未命中，获取该键的下载锁
        download_lock = self._get_download_lock(cache_key)
        
        with download_lock:
            # 在下载锁内再次检查缓存（其他线程可能已经下载完成）
            with self._btc_cache_lock:
                if cache_key in self._btc_cache:
                    # 其他线程已经下载了，直接返回缓存的数据
                    self._btc_cache.move_to_end(cache_key)
                    logger.debug(f"BTC 数据已被其他线程缓存 | {timeframe}/{period}")
                    return self._btc_cache[cache_key].copy(deep=True)
                else:
                    # 记录缓存未命中
                    with self._cache_stats_lock:
                        self._cache_stats['misses'] += 1
            
            # 确实需要下载数据
            try:
                df = self.get_ohlcv(BTC_SYMBOL, timeframe, period)
                if not df.empty:
                    with self._btc_cache_lock:
                        # 添加到缓存
                        self._btc_cache[cache_key] = df
                        
                        # 如果超过最大缓存大小，移除最旧的条目
                        while len(self._btc_cache) > self.MAX_BTC_CACHE_SIZE:
                            oldest_key = next(iter(self._btc_cache))
                            self._btc_cache.pop(oldest_key)
                            logger.debug(f"BTC 缓存已满，移除最旧条目 | {oldest_key}")

                    return df.copy(deep=True)
            except Exception as e:
                logger.error(f"获取 BTC 数据失败 | {timeframe}/{period} | {e}")
        
        return None
    
    def clear_btc_cache(self):
        """清除 BTC 内存缓存（线程安全）"""
        with self._btc_cache_lock:
            self._btc_cache.clear()
        logger.debug("BTC 内存缓存已清除")
    
    def get_usdc_perpetuals(self) -> list[str]:
        """获取所有 USDC 永续合约交易对"""
        return self.rest_client.get_usdc_perpetuals()
    
    def load_markets(self) -> dict:
        """加载市场信息"""
        return self.rest_client.load_markets()
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息（线程安全）"""
        with self._btc_cache_lock:
            btc_cache_keys = list(self._btc_cache.keys())
        
        with self._cache_stats_lock:
            cache_stats = self._cache_stats.copy()
        
        # 计算命中率
        total = cache_stats['hits'] + cache_stats['misses']
        hit_rate = cache_stats['hits'] / total if total > 0 else 0.0
            
        return {
            "sqlite": self.cache.get_cache_stats(),
            "btc_memory_cache": btc_cache_keys,
            "btc_cache_hits": cache_stats['hits'],
            "btc_cache_misses": cache_stats['misses'],
            "btc_cache_hit_rate": f"{hit_rate:.2%}"
        }
    
    def prefetch_btc_data(self, timeframes: list[str], periods: list[str]):
        """
        预取 BTC 数据到缓存
        
        Args:
            timeframes: K 线周期列表
            periods: 数据周期列表
        """
        logger.info(f"预取 BTC 数据 | 周期: {timeframes} | 范围: {periods}")
        
        for timeframe in timeframes:
            for period in periods:
                try:
                    self.get_btc_data(timeframe, period)
                    logger.debug(f"预取完成 | BTC | {timeframe}/{period}")
                except Exception as e:
                    logger.error(f"预取失败 | BTC | {timeframe}/{period} | {e}")

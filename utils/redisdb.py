import redis
import logging
import threading
from .config import redis_password, redis_host
from typing import Optional

logger = logging.getLogger(__name__)

# 模块级单例：连接池和客户端
_connection_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None
_init_lock = threading.Lock()


def _create_connection_pool() -> redis.ConnectionPool:
    """创建 Redis 连接池（内部函数）"""
    pool_kwargs = {
        'host': redis_host,
        'port': 6379,
        'db': 0,
        'max_connections': 10,  # 限制最大连接数
        'socket_timeout': 5,
        'socket_connect_timeout': 5,
    }
    
    if redis_password:
        pool_kwargs['password'] = redis_password
    
    return redis.ConnectionPool(**pool_kwargs)


def redis_cli() -> redis.Redis:
    """
    获取 Redis 客户端单例（线程安全）
    
    使用模块级连接池，避免重复创建连接池导致资源泄漏。
    """
    global _connection_pool, _redis_client
    
    # 双重检查锁定模式，确保线程安全
    if _redis_client is not None:
        return _redis_client
    
    with _init_lock:
        # 再次检查，防止多个线程同时进入
        if _redis_client is not None:
            return _redis_client
        
        logger.debug(f'Redis 连接配置: host={redis_host}, password={"***" if redis_password else "未设置"}')
        
        # 创建连接池（单例）
        _connection_pool = _create_connection_pool()
        
        # 创建 Redis 客户端（单例）
        _redis_client = redis.Redis(connection_pool=_connection_pool)
        
        # 测试连接
        try:
            _redis_client.ping()
            logger.info("Redis 连接成功")
        except redis.AuthenticationError:
            logger.error("Redis 认证失败，请检查密码")
            # 清理连接池资源
            if _connection_pool:
                try:
                    _connection_pool.disconnect()
                except Exception:
                    pass
            _redis_client = None
            _connection_pool = None
            raise
        except redis.ConnectionError:
            logger.error("Redis 连接失败，请检查 Redis 是否运行")
            # 清理连接池资源
            if _connection_pool:
                try:
                    _connection_pool.disconnect()
                except Exception:
                    pass
            _redis_client = None
            _connection_pool = None
            raise
        
        return _redis_client


def close_redis():
    """关闭 Redis 连接池（可选，用于程序退出时清理）"""
    global _connection_pool, _redis_client
    
    with _init_lock:
        if _connection_pool is not None:
            try:
                _connection_pool.disconnect()
            except Exception:
                pass
            _connection_pool = None
        _redis_client = None
        logger.debug("Redis 连接池已关闭")
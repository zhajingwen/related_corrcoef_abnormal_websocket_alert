import redis
import logging
import threading
import time
from .config import redis_password, redis_host
from typing import Optional

logger = logging.getLogger(__name__)

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒
RETRY_BACKOFF = 2  # 指数退避倍数

# 模块级单例：连接池和客户端
_connection_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None
_init_lock = threading.Lock()
_last_connection_attempt: float = 0  # 上次连接尝试时间
_connection_cooldown: float = 30  # 连接失败后的冷却时间（秒）


def _create_connection_pool() -> redis.ConnectionPool:
    """创建 Redis 连接池（内部函数）"""
    pool_kwargs = {
        'host': redis_host,
        'port': 6379,
        'db': 0,
        'max_connections': 10,  # 限制最大连接数
        'socket_timeout': 5,
        'socket_connect_timeout': 5,
        'retry_on_timeout': True,  # 超时时自动重试
    }
    
    if redis_password:
        pool_kwargs['password'] = redis_password
    
    return redis.ConnectionPool(**pool_kwargs)


def _try_connect() -> Optional[redis.Redis]:
    """
    尝试建立 Redis 连接（带重试机制）
    
    Returns:
        成功返回 Redis 客户端，失败返回 None
    """
    global _connection_pool, _redis_client
    
    for attempt in range(MAX_RETRIES):
        try:
            # 创建连接池
            pool = _create_connection_pool()
            client = redis.Redis(connection_pool=pool)
            
            # 测试连接
            client.ping()
            
            # 连接成功
            _connection_pool = pool
            _redis_client = client
            logger.info(f"Redis 连接成功 (尝试 {attempt + 1}/{MAX_RETRIES})")
            return client
            
        except redis.AuthenticationError:
            logger.error("Redis 认证失败，请检查密码")
            # 认证错误不重试，直接返回
            _cleanup_pool(pool if 'pool' in dir() else None)
            return None
            
        except redis.ConnectionError as e:
            logger.warning(f"Redis 连接失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
            _cleanup_pool(pool if 'pool' in dir() else None)
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                logger.info(f"等待 {delay} 秒后重试...")
                time.sleep(delay)
                
        except Exception as e:
            logger.error(f"Redis 连接异常: {type(e).__name__}: {e}")
            _cleanup_pool(pool if 'pool' in dir() else None)
            
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                time.sleep(delay)
    
    logger.error(f"Redis 连接失败，已重试 {MAX_RETRIES} 次")
    return None


def _cleanup_pool(pool: Optional[redis.ConnectionPool]):
    """清理连接池资源"""
    if pool is not None:
        try:
            pool.disconnect()
        except Exception:
            pass


def redis_cli() -> redis.Redis:
    """
    获取 Redis 客户端单例（线程安全，带重试机制）
    
    使用模块级连接池，避免重复创建连接池导致资源泄漏。
    如果连接失败会自动重试，并在冷却期后允许再次尝试。
    
    Raises:
        redis.ConnectionError: 如果无法建立连接
    """
    global _connection_pool, _redis_client, _last_connection_attempt
    
    # 快速路径：已有有效连接
    if _redis_client is not None:
        try:
            # 验证连接是否仍然有效
            _redis_client.ping()
            return _redis_client
        except (redis.ConnectionError, redis.TimeoutError):
            # 连接已失效，需要重新建立
            logger.warning("Redis 连接已失效，尝试重新连接...")
            with _init_lock:
                _cleanup_pool(_connection_pool)
                _redis_client = None
                _connection_pool = None
    
    with _init_lock:
        # 双重检查
        if _redis_client is not None:
            return _redis_client
        
        # 检查冷却期（避免频繁重试）
        now = time.time()
        if _last_connection_attempt > 0 and (now - _last_connection_attempt) < _connection_cooldown:
            remaining = _connection_cooldown - (now - _last_connection_attempt)
            raise redis.ConnectionError(
                f"Redis 连接处于冷却期，请在 {remaining:.1f} 秒后重试"
            )
        
        _last_connection_attempt = now
        
        logger.debug(f'Redis 连接配置: host={redis_host}, password={"***" if redis_password else "未设置"}')
        
        # 尝试连接（带重试）
        client = _try_connect()
        
        if client is None:
            raise redis.ConnectionError("无法建立 Redis 连接")
        
        return client


def reset_redis_connection():
    """
    重置 Redis 连接状态（用于手动触发重连）
    
    调用此函数后，下次调用 redis_cli() 将重新尝试建立连接。
    """
    global _connection_pool, _redis_client, _last_connection_attempt
    
    with _init_lock:
        _cleanup_pool(_connection_pool)
        _redis_client = None
        _connection_pool = None
        _last_connection_attempt = 0  # 重置冷却期
        logger.info("Redis 连接状态已重置")


def close_redis():
    """关闭 Redis 连接池（可选，用于程序退出时清理）"""
    global _connection_pool, _redis_client, _last_connection_attempt
    
    with _init_lock:
        _cleanup_pool(_connection_pool)
        _connection_pool = None
        _redis_client = None
        _last_connection_attempt = 0
        logger.debug("Redis 连接池已关闭")
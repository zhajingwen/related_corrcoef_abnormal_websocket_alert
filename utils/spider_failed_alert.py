import traceback
import os
import logging
from .lark_bot import sender
# from .config import env

logger = logging.getLogger(__name__)

# Redis 客户端缓存和状态标记
_redis_client = None
_redis_available = True  # 标记 Redis 是否可用，避免反复尝试连接


def _get_redis_client():
    """
    获取 Redis 客户端单例（带降级处理）
    
    如果 Redis 连接失败，返回 None 并标记为不可用，
    后续调用将直接返回 None 而不是反复尝试连接。
    """
    global _redis_client, _redis_available
    
    # 如果已标记为不可用，直接返回 None
    if not _redis_available:
        return None
    
    if _redis_client is not None:
        return _redis_client
    
    try:
        from .redisdb import redis_cli
        _redis_client = redis_cli()
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis 连接失败，告警去重功能将不可用: {e}")
        _redis_available = False
        return None


def ErrorMonitor(spider_name, user=None):
    """
    捕获异常并且发送消息的装饰器,用于加在各个爬虫的解析方法上
    :param spider_name:爬虫名
    :param user: 用户名
    24个小时内单个爬虫的故障只告警一次（需要 Redis 支持，否则每次都告警）
    """
    # 从环境变量读取 webhook ID
    webhook_id = os.getenv('SPIDER_ALERT_WEBHOOK_ID')
    if not webhook_id:
        logger.warning("环境变量 SPIDER_ALERT_WEBHOOK_ID 未设置，告警功能将不可用")
        webhook = None
    else:
        webhook = f'https://open.feishu.cn/open-apis/bot/v2/hook/{webhook_id}'
    title = f'{spider_name}\n  @{user}'
    key_base = 'process:failed:filter:{}'
        
    # 捕获异常
    def catch_exception(func):
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            # 捕获异常，发送告警
            except Exception as e:
                err_info = traceback.format_exc()
                logger.error(err_info)
                
                # 尝试获取 Redis 客户端（带降级处理）
                redis_c = _get_redis_client()
                
                # 检查是否需要过滤告警（如果 Redis 可用）
                if redis_c is not None:
                    try:
                        key = key_base.format(spider_name)
                        filter_status = redis_c.get(key)
                        if filter_status:
                            logger.debug('过滤该告警（24小时内已告警）')
                            raise e
                    except Exception as redis_err:
                        # Redis 操作失败，降级处理：继续发送告警
                        logger.warning(f"Redis 操作失败，跳过去重检查: {redis_err}")
                
                # 发送告警
                if webhook:
                    try:
                        sender(err_info, url=webhook, title=title)
                    except Exception as send_err:
                        logger.error(f"发送告警失败: {send_err}")
                else:
                    logger.warning('告警功能未配置，跳过发送')
                
                # 设置告警过滤标记（如果 Redis 可用）
                if redis_c is not None:
                    try:
                        key = key_base.format(spider_name)
                        redis_c.setex(key, 24*60*60, 1)
                    except Exception as redis_err:
                        logger.warning(f"Redis 设置过滤标记失败: {redis_err}")
                
                raise e
        return inner
    return catch_exception

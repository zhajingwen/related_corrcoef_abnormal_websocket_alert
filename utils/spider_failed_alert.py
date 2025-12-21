import traceback
import os
import logging
from .lark_bot import sender
# from .config import env

logger = logging.getLogger(__name__)

# 模块级 Redis 客户端单例，避免每次异常都创建新连接
_redis_client = None


def _get_redis_client():
    """获取 Redis 客户端单例"""
    global _redis_client
    if _redis_client is None:
        from .redisdb import redis_cli
        _redis_client = redis_cli()
    return _redis_client


def ErrorMonitor(spider_name, user=None):
    """
    捕获异常并且发送消息的装饰器,用于加在各个爬虫的解析方法上
    :param spider_name:爬虫名
    :param user: 用户名
    24个小时内单个爬虫的故障只告警一次
    """
    # 从环境变量读取 webhook ID
    webhook_id = os.getenv('SPIDER_ALERT_WEBHOOK_ID')
    if not webhook_id:
        logger.warning("环境变量 SPIDER_ALERT_WEBHOOK_ID 未设置，告警功能将不可用")
        webhook = None
    else:
        webhook = f'https://open.larksuite.com/open-apis/bot/v2/hook/{webhook_id}'
    title = f'{spider_name}\n  @{user}'
    key_base = 'process:failed:filter:{}'
        
    # 捕获异常
    def catch_exception(func):
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            # 捕获异常，发送告警
            except Exception as e:
                redis_c = _get_redis_client()  # 复用单例连接
                err_info = traceback.format_exc()
                logger.error(err_info)
                key = key_base.format(spider_name)
                filter_status = redis_c.get(key)
                if filter_status:
                    logger.debug('过滤该告警（24小时内已告警）')
                    return
                # 只有线上环境才告警
                # if env == 'prod':
                if webhook:
                    sender(err_info, url=webhook, title=title)
                else:
                    logger.warning('告警功能未配置，跳过发送')
                # 24个小时内单个爬虫的故障只告警一次
                redis_c.setex(key, 24*60*60, 1)
                raise e
        return inner
    return catch_exception

import time
import logging
from datetime import datetime, timedelta
from .config import env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Timer Scheduler')


def _calculate_days_until_next_weekday(current_weekday: int, target_weekdays: list) -> int:
    """
    计算到下一个符合条件的周几需要等待的天数
    
    Args:
        current_weekday: 当前是周几 (0=周一, 6=周日)
        target_weekdays: 目标周几列表，如 [1, 3, 5] 表示周二、周四、周六
    
    Returns:
        需要等待的天数（至少1天）
    """
    # 计算到下一个目标周几需要等待的天数
    for days_ahead in range(1, 8):  # 最多等待7天
        next_weekday = (current_weekday + days_ahead) % 7
        if next_weekday in target_weekdays:
            return days_ahead
    
    # 理论上不会到达这里（因为一周有7天，至少会找到一个目标周几），但为了安全返回7天
    return 7

def scheduled_task(start_time=None, duration=None, weekdays=None):
    """
    定时调度装饰器
    (以下三种调度方式任选其一，其他参数按需配置)

    :param start_time: 启动时间，格式为 'HH:MM'
    :param duration: 多长时间调度一次（秒），必须 > 0
    :param weekdays: 指定周几执行，格式为整数列表 [0,1,2,3,4,5,6]，0表示周一，6表示周日
                     如 [1,3,5] 表示周二、周四、周六执行
                     如果不指定，则每天都执行
                     
    调度方式说明：
    1. 周几的几点执行：提供 start_time 和 weekdays 参数
    2. 每天的几点执行：只提供 start_time 参数 
    3. 每隔 N 秒执行一次：只提供 duration 参数
    
    Raises:
        ValueError: 参数配置无效时抛出
    """
    # 参数校验：必须提供 start_time 或 duration 之一
    if start_time is None and duration is None:
        raise ValueError("必须提供 start_time 或 duration 参数之一")
    
    # duration 模式时校验值有效性
    if start_time is None and duration is not None:
        if not isinstance(duration, (int, float)):
            raise ValueError(f"duration 必须是数字，当前类型: {type(duration).__name__}")
        if duration <= 0:
            raise ValueError(f"duration 必须大于 0，当前值: {duration}")
    
    # start_time 格式校验
    if start_time is not None:
        try:
            parts = start_time.split(':')
            if len(parts) != 2:
                raise ValueError()
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except (ValueError, AttributeError):
            raise ValueError(f"start_time 格式无效，应为 'HH:MM'，当前值: {start_time}")
    
    # weekdays 校验
    if weekdays is not None:
        if not isinstance(weekdays, (list, tuple)):
            raise ValueError(f"weekdays 必须是列表或元组，当前类型: {type(weekdays).__name__}")
        for day in weekdays:
            if not isinstance(day, int) or day < 0 or day > 6:
                raise ValueError(f"weekdays 中的值必须是 0-6 的整数，当前值: {day}")
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            if env == 'local':
                logger.info('开发环境，直接启动（放弃定时调度）')
                func(*args, **kwargs)
                return
            logger.info('程序启动，等待调度中...')
            while True:
                # 定时调度
                if start_time:
                    # 获取当前时间和调度时间范围
                    today_now = datetime.now()
                    
                    # 检查是否指定了周几，如果指定了，则检查当前是否是指定的周几
                    if weekdays is not None:
                        # 获取当前是周几 (0表示周一，6表示周日)
                        current_weekday = today_now.weekday()  # 0-6 对应周一至周日
                        if current_weekday not in weekdays:
                            # 不是指定的周几，计算到下一个符合条件的周几需要等待的时间
                            days_until_next = _calculate_days_until_next_weekday(current_weekday, weekdays)
                            wait_seconds = days_until_next * 24 * 60 * 60
                            logger.info(f'当前是周{current_weekday+1}，不在调度计划 {weekdays} 中，等待 {days_until_next} 天后再次检查')
                            time.sleep(wait_seconds)
                            continue
                        else:
                            logger.info(f'今天是周{current_weekday+1}，符合调度计划 {weekdays}')    
                    
                    # 解析调度时间
                    start_hour, start_minute = map(int, start_time.split(':'))
                    start = today_now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                    end = start + timedelta(minutes=10)

                    # 如果当前时间在调度时间范围内，执行任务
                    if start <= today_now < end:
                        logger.info('激活调度')
                        func(*args, **kwargs)
                        logger.info('调度结束')

                        # 计算到明天同一时间需要等待的秒数
                        next_run = start + timedelta(days=1)
                        wait_seconds = (next_run - datetime.now()).total_seconds()
                        # 确保至少等待到窗口结束后，防止在同一窗口内重复执行
                        min_wait = (end - datetime.now()).total_seconds() + 60
                        wait_seconds = max(wait_seconds, min_wait, 60)
                        logger.info(f'等待 {wait_seconds:.0f} 秒后进行下一次调度')
                        time.sleep(wait_seconds)
                    else:
                        # 不在执行时间范围内，等待一段时间再检查
                        time.sleep(10)
                else:
                    logger.info('激活调度')
                    func(*args, **kwargs)
                    logger.info('调度结束')
                    time.sleep(duration)
        return wrapper
    return decorator
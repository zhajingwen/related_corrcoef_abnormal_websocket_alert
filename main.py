"""
主程序入口

支持两种运行模式：
- analysis: 一次性分析所有币种
- monitor: 持续监控实时数据

使用方式：
    python main.py --mode=analysis
    python main.py --mode=monitor
    python main.py --coin=ETH/USDC:USDC  # 分析单个币种
"""

import argparse
import logging
import sys
import time
import signal
import threading

from .analyzer import DelayCorrelationAnalyzer, setup_logging

logger = setup_logging()


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Hyperliquid 相关系数分析器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --mode=analysis              # 一次性分析所有币种
  python main.py --coin=ETH/USDC:USDC         # 分析单个币种
  python main.py --mode=monitor               # 持续监控模式
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["analysis", "monitor"],
        default="analysis",
        help="运行模式: analysis=一次性分析, monitor=持续监控 (默认: analysis)"
    )
    
    parser.add_argument(
        "--coin",
        type=str,
        default=None,
        help="分析单个币种，如 ETH/USDC:USDC"
    )
    
    parser.add_argument(
        "--exchange",
        type=str,
        default="hyperliquid",
        help="交易所名称 (默认: hyperliquid)"
    )
    
    parser.add_argument(
        "--db",
        type=str,
        default="hyperliquid_data.db",
        help="SQLite 数据库路径 (默认: hyperliquid_data.db)"
    )
    
    parser.add_argument(
        "--timeframes",
        type=str,
        default="1m,5m",
        help="K 线周期，逗号分隔 (默认: 1m,5m)"
    )
    
    parser.add_argument(
        "--periods",
        type=str,
        default="1d,7d,30d,60d",
        help="数据周期，逗号分隔 (默认: 1d,7d,30d,60d)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试日志"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="监控模式下的分析间隔（秒）(默认: 3600)"
    )
    
    return parser.parse_args()


def create_analyzer(args: argparse.Namespace) -> DelayCorrelationAnalyzer:
    """根据命令行参数创建分析器实例"""
    timeframes = [tf.strip() for tf in args.timeframes.split(",")]
    periods = [p.strip() for p in args.periods.split(",")]
    
    return DelayCorrelationAnalyzer(
        exchange_name=args.exchange,
        db_path=args.db,
        default_timeframes=timeframes,
        default_periods=periods
    )


def run_analysis(args: argparse.Namespace):
    """运行一次性分析"""
    analyzer = create_analyzer(args)
    
    if args.coin:
        # 分析单个币种
        logger.info(f"分析单个币种: {args.coin}")
        analyzer.run_single(args.coin)
    else:
        # 分析所有币种
        analyzer.run()


def run_monitor(args: argparse.Namespace):
    """运行持续监控模式"""
    analyzer = create_analyzer(args)
    
    # 使用 Event 替代布尔变量，确保线程安全
    stop_event = threading.Event()
    
    def signal_handler(signum, frame):
        logger.info("收到停止信号，正在退出...")
        stop_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(f"启动监控模式 | 分析间隔: {args.interval}s")
    
    try:
        while not stop_event.is_set():
            logger.info("开始新一轮分析...")
            
            try:
                analyzer.run()
            except Exception as e:
                logger.error(f"分析过程出错: {e}")
            
            if not stop_event.is_set():
                logger.info(f"等待 {args.interval} 秒后进行下一轮分析...")
                
                # 使用 wait() 替代 sleep，可以被中断
                # 分段等待以便响应信号
                remaining = args.interval
                while remaining > 0 and not stop_event.is_set():
                    wait_chunk = min(remaining, 10)
                    if stop_event.wait(timeout=wait_chunk):
                        break
                    remaining -= wait_chunk
    
    except KeyboardInterrupt:
        logger.info("用户中断，正在退出...")
    
    finally:
        logger.info("监控模式已停止")


def main():
    """主函数"""
    args = parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.info("调试模式已启用")
    
    logger.info("=" * 60)
    logger.info("Hyperliquid 相关系数分析器")
    logger.info(f"模式: {args.mode}")
    logger.info(f"交易所: {args.exchange}")
    logger.info(f"数据库: {args.db}")
    logger.info("=" * 60)
    
    try:
        if args.mode == "analysis":
            run_analysis(args)
        elif args.mode == "monitor":
            run_monitor(args)
        else:
            logger.error(f"未知模式: {args.mode}")
            sys.exit(1)
    
    except Exception as e:
        logger.exception(f"程序异常退出: {e}")
        sys.exit(1)
    
    logger.info("程序正常退出")


if __name__ == "__main__":
    main()


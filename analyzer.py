"""
相关系数分析器模块

分析山寨币与 BTC 的皮尔逊相关系数，识别存在时间差套利空间的异常币种。
基于 DataManager 获取数据，使用 REST API 和 SQLite 缓存。
"""

import time
import os
import logging
import warnings
import threading
import uuid
from logging.handlers import RotatingFileHandler
from typing import Optional
import numpy as np
import pandas as pd

from manager import DataManager, BTC_SYMBOL

# 尝试导入飞书通知（可选）
try:
    from utils.lark_bot import sender
    from utils.config import lark_bot_id
    HAS_LARK_BOT = True
except ImportError:
    HAS_LARK_BOT = False
    lark_bot_id = None


def setup_logging(log_file: str = "analyzer.log", level: int = logging.INFO) -> logging.Logger:
    """
    配置日志系统，支持控制台和文件输出
    
    Args:
        log_file: 日志文件路径
        level: 日志级别
    
    Returns:
        配置好的 logger 实例
    """
    log = logging.getLogger(__name__)
    
    # 避免重复添加 handlers
    if log.handlers:
        return log
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # 文件处理器（10MB轮转，保留5个备份）
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # 配置 logger
    log.setLevel(level)
    log.addHandler(console_handler)
    log.addHandler(file_handler)
    
    return log


logger = setup_logging()


class DelayCorrelationAnalyzer:
    """
    山寨币与 BTC 相关系数分析器
    
    识别短期低相关但长期高相关的异常币种，这类币种存在时间差套利机会。
    """
    
    # 相关系数计算所需的最小数据点数
    MIN_POINTS_FOR_CORR_CALC = 30
    # 数据分析所需的最小数据点数
    MIN_DATA_POINTS_FOR_ANALYSIS = 100

    # 异常模式检测阈值
    LONG_TERM_CORR_THRESHOLD = 0.6   # 长期相关系数阈值
    SHORT_TERM_CORR_THRESHOLD = 0.3  # 短期相关系数阈值
    CORR_DIFF_THRESHOLD = 0.5        # 相关系数差值阈值

    # 数据质量阈值
    MAX_NAN_RATIO = 0.05  # 最大允许 NaN 值比例（5%），确保数据质量
    
    def __init__(
        self,
        exchange_name: str = "hyperliquid",
        db_path: str = "hyperliquid_data.db",
        default_timeframes: Optional[list[str]] = None,
        default_periods: Optional[list[str]] = None
    ):
        """
        初始化分析器
        
        Args:
            exchange_name: 交易所名称
            db_path: SQLite 数据库路径
            default_timeframes: K 线颗粒度列表
            default_periods: 数据周期列表
        """
        self.exchange_name = exchange_name
        self.timeframes = default_timeframes or ["1m", "5m"]
        self.periods = default_periods or ["1d", "7d", "30d", "60d"]
        self.btc_symbol = BTC_SYMBOL
        
        # 初始化数据管理器
        self.data_manager = DataManager(
            exchange_name=exchange_name,
            db_path=db_path
        )
        
        # 飞书通知配置
        if HAS_LARK_BOT and lark_bot_id:
            self.lark_hook = f'https://open.feishu.cn/open-apis/bot/v2/hook/{lark_bot_id}'
        else:
            self.lark_hook = None
            if not HAS_LARK_BOT:
                logger.warning("飞书通知模块未找到，通知功能不可用")
            elif not lark_bot_id:
                logger.warning("环境变量 LARKBOT_ID 未设置，飞书通知功能不可用")
        
        # 初始化锁（防止多线程环境下的竞态条件）
        self._init_lock = threading.Lock()
        self._is_initialized = False  # 初始化标志，避免重复预取数据

        logger.info(
            f"分析器初始化 | 交易所: {exchange_name} | "
            f"时间周期: {self.timeframes} | 数据周期: {self.periods}"
        )

    def initialize(self):
        """初始化：启动数据管理器（线程安全，只在首次调用时预取数据）"""
        with self._init_lock:
            if self._is_initialized:
                logger.debug("分析器已初始化，跳过重复初始化")
                return

            self.data_manager.initialize()

            # 预取 BTC 数据（只在首次初始化时执行）
            logger.info("预取 BTC 历史数据...")
            self.data_manager.prefetch_btc_data(self.timeframes, self.periods)

            self._is_initialized = True
            logger.info("分析器初始化完成")
    
    def shutdown(self):
        """关闭：停止数据管理器"""
        self.data_manager.shutdown()
    
    @staticmethod
    def find_optimal_delay(btc_ret: np.ndarray, alt_ret: np.ndarray, max_lag: int = 48) -> tuple:
        """
        寻找最优延迟 τ*

        通过计算不同延迟下 BTC 和山寨币收益率的相关系数，找出使相关系数最大的延迟值。
        tau_star > 0 表示山寨币滞后于 BTC，存在时间差套利机会。

        Args:
            btc_ret: BTC 收益率数组（应与alt_ret长度一致）
            alt_ret: 山寨币收益率数组（应与btc_ret长度一致）
            max_lag: 最大延迟值

        Returns:
            (tau_star, corrs, max_corr): 最优延迟、相关系数列表、最大相关系数
        """
        corrs = []
        lags = list(range(0, max_lag + 1))
        btc_len = len(btc_ret)
        alt_len = len(alt_ret)

        # 严格检查：数据长度必须一致（应该在调用前已对齐）
        if btc_len != alt_len:
            logger.error(
                f"严重错误：输入数据长度不一致 | BTC={btc_len}, ALT={alt_len} | "
                f"这表明数据对齐逻辑存在问题，返回NaN避免错误计算"
            )
            # 返回无效结果，不进行不准确的计算
            return 0, [np.nan] * (max_lag + 1), np.nan

        arr_len = btc_len
        
        for lag in lags:
            # 检查 lag 是否会导致数据不足
            # 当 lag > 0 时，切片后的数据长度为 arr_len - lag
            # 需要确保剩余数据点足够进行相关系数计算
            remaining_points = arr_len - lag if lag > 0 else arr_len
            if remaining_points < DelayCorrelationAnalyzer.MIN_POINTS_FOR_CORR_CALC:
                corrs.append(np.nan)
                continue
            
            if lag > 0:
                # ALT 滞后 BTC: 比较 BTC[0:len-lag] 与 ALT[lag:len]
                # 即比较 BTC[t] 与 ALT[t+lag]，其中 t 从 0 到 len-lag-1
                # 确保切片后的长度一致
                x = btc_ret[:-lag]
                y = alt_ret[lag:]
            else:
                x = btc_ret
                y = alt_ret

            # 再次检查对齐后的长度（虽然理论上应该一致，但为了安全）
            m = min(len(x), len(y))

            # 二次检查：确保对齐后的数据点足够
            if m < DelayCorrelationAnalyzer.MIN_POINTS_FOR_CORR_CALC:
                corrs.append(np.nan)
                continue

            # 修复BUG#4：使用pandas自动处理NaN
            x_series = pd.Series(x[:m])
            y_series = pd.Series(y[:m])

            # 检查有效数据点数量（去除NaN后）
            valid_mask = ~(x_series.isna() | y_series.isna())
            valid_count = valid_mask.sum()

            if valid_count < DelayCorrelationAnalyzer.MIN_POINTS_FOR_CORR_CALC:
                logger.debug(f"有效数据点不足: {valid_count}/{m}")
                corrs.append(np.nan)
                continue

            # 计算相关系数（pandas会自动跳过NaN对）
            correlation = x_series.corr(y_series, method='pearson')

            # 双重检查结果
            if pd.isna(correlation):
                logger.debug("相关系数计算结果为NaN")
                corrs.append(np.nan)
            else:
                corrs.append(correlation)
        
        # 找出最大相关系数对应的延迟值
        valid_corrs = np.array(corrs)
        valid_mask = ~np.isnan(valid_corrs)
        
        if valid_mask.any():
            valid_indices = np.where(valid_mask)[0]
            best_idx = valid_indices[np.argmax(valid_corrs[valid_mask])]
            tau_star = lags[best_idx]
            max_corr = valid_corrs[best_idx]
        else:
            tau_star = 0
            max_corr = np.nan
        
        return tau_star, corrs, max_corr
    
    def _get_btc_data(self, timeframe: str, period: str) -> Optional[pd.DataFrame]:
        """获取 BTC 数据"""
        return self.data_manager.get_btc_data(timeframe, period)
    
    def _get_coin_data(self, symbol: str, timeframe: str, period: str) -> Optional[pd.DataFrame]:
        """获取币种数据"""
        try:
            df = self.data_manager.get_ohlcv(symbol, timeframe, period)
            return df if not df.empty else None
        except Exception as e:
            logger.warning(f"获取数据失败 | {symbol} | {timeframe}/{period} | {e}")
            return None
    
    def _align_and_validate_data(
        self,
        btc_df: pd.DataFrame,
        alt_df: pd.DataFrame,
        coin: str,
        timeframe: str,
        period: str
    ) -> Optional[tuple[pd.DataFrame, pd.DataFrame]]:
        """
        对齐和验证 BTC 与山寨币数据

        Args:
            btc_df: BTC 数据 DataFrame
            alt_df: 山寨币数据 DataFrame
            coin: 币种名称（用于日志）
            timeframe: 时间周期
            period: 数据周期

        Returns:
            成功返回对齐后的 (btc_df, alt_df)，失败返回 None
        """
        # 记录原始数据量
        original_btc_len = len(btc_df)
        original_alt_len = len(alt_df)

        # 对齐时间索引
        common_idx = btc_df.index.intersection(alt_df.index)
        btc_df_aligned = btc_df.loc[common_idx].copy()
        alt_df_aligned = alt_df.loc[common_idx].copy()

        # 计算对齐损失率
        aligned_len = len(btc_df_aligned)
        if aligned_len == 0:
            logger.warning(
                f"时间对齐后无共同数据点 | 币种: {coin} | {timeframe}/{period} | "
                f"BTC原始={original_btc_len}, ALT原始={original_alt_len}"
            )
            return None

        loss_ratio = 1 - (aligned_len / min(original_btc_len, original_alt_len))
        if loss_ratio > 0.1:  # 损失超过10%发出警告
            logger.warning(
                f"时间对齐损失超过10% | 币种: {coin} | {timeframe}/{period} | "
                f"BTC: {original_btc_len}→{aligned_len} | "
                f"ALT: {original_alt_len}→{aligned_len} | "
                f"损失率: {loss_ratio:.1%}"
            )
        else:
            logger.debug(
                f"数据对齐完成 | 币种: {coin} | {timeframe}/{period} | "
                f"共同点: {aligned_len}/{min(original_btc_len, original_alt_len)}"
            )
        
        # 数据验证：检查数据量
        if len(btc_df_aligned) < self.MIN_DATA_POINTS_FOR_ANALYSIS:
            logger.warning(f"数据量不足，跳过 | 币种: {coin} | {timeframe}/{period}")
            return None
        
        if len(alt_df_aligned) < self.MIN_DATA_POINTS_FOR_ANALYSIS:
            logger.warning(f"数据量不足，跳过 | 币种: {coin} | {timeframe}/{period}")
            return None
        
        # 数据验证：检查NaN值比例（使用更严格的5%阈值）
        btc_nan_ratio = btc_df_aligned['return'].isna().sum() / len(btc_df_aligned)
        if btc_nan_ratio > self.MAX_NAN_RATIO:
            logger.warning(f"BTC数据包含过多NaN值 ({btc_nan_ratio:.1%})，跳过 | 币种: {coin} | {timeframe}/{period}")
            return None

        alt_nan_ratio = alt_df_aligned['return'].isna().sum() / len(alt_df_aligned)
        if alt_nan_ratio > self.MAX_NAN_RATIO:
            logger.warning(f"山寨币数据包含过多NaN值 ({alt_nan_ratio:.1%})，跳过 | 币种: {coin} | {timeframe}/{period}")
            return None
        
        return btc_df_aligned, alt_df_aligned
    
    def _analyze_single_combination(
        self,
        coin: str,
        timeframe: str,
        period: str
    ) -> Optional[tuple]:
        """
        分析单个 timeframe/period 组合
        
        Returns:
            成功返回 (correlation, timeframe, period, tau_star)，失败返回 None
        """
        logger.debug(f"下载数据 | 币种: {coin} | {timeframe}/{period}")
        
        btc_df = self._get_btc_data(timeframe, period)
        if btc_df is None:
            return None
        
        alt_df = self._get_coin_data(coin, timeframe, period)
        if alt_df is None:
            return None
        
        # 对齐和验证数据
        aligned_data = self._align_and_validate_data(btc_df, alt_df, coin, timeframe, period)
        if aligned_data is None:
            return None
        
        btc_df_aligned, alt_df_aligned = aligned_data
        
        tau_star, _, corr = self.find_optimal_delay(
            btc_df_aligned['return'].values,
            alt_df_aligned['return'].values
        )
        
        logger.debug(
            f"分析结果 | timeframe: {timeframe} | period: {period} | "
            f"tau_star: {tau_star} | 相关系数: {corr:.4f}"
        )
        
        return (corr, timeframe, period, tau_star)
    
    def _detect_anomaly_pattern(self, results: list) -> tuple[bool, float]:
        """
        检测异常模式：短期低相关但长期高相关
        
        Returns:
            (is_anomaly, diff_amount): 是否异常模式、相关系数差值
        """
        short_periods = ['1d']
        long_periods = ['7d', '30d', '60d']
        
        short_term_corrs = [x[0] for x in results if x[2] in short_periods]
        long_term_corrs = [x[0] for x in results if x[2] in long_periods]
        
        if not short_term_corrs or not long_term_corrs:
            return False, 0
        
        # 过滤掉 NaN 值，避免 min/max 返回 NaN
        short_term_corrs_valid = [c for c in short_term_corrs if not np.isnan(c)]
        long_term_corrs_valid = [c for c in long_term_corrs if not np.isnan(c)]
        
        if not short_term_corrs_valid or not long_term_corrs_valid:
            logger.debug("有效相关系数不足，无法进行异常检测")
            return False, 0
        
        min_short_corr = min(short_term_corrs_valid)
        max_long_corr = max(long_term_corrs_valid)
        
        logger.debug(f"相关系数检测 | 短期最小: {min_short_corr:.4f} | 长期最大: {max_long_corr:.4f}")
        
        # 计算差值（无论是否满足阈值条件，都先计算，避免后续使用未定义变量）
        diff_amount = max_long_corr - min_short_corr
        
        if max_long_corr > self.LONG_TERM_CORR_THRESHOLD and min_short_corr < self.SHORT_TERM_CORR_THRESHOLD:
            if diff_amount > self.CORR_DIFF_THRESHOLD:
                return True, diff_amount
            # 短期存在明显滞后时也触发（修复BUG#4：增加NaN检查）
            if any(not np.isnan(tau_star) and tau_star > 0 for _, _, period, tau_star in results if period == '1d'):
                return True, diff_amount
        
        return False, 0
    
    def _output_results(self, coin: str, results: list, diff_amount: float):
        """输出异常模式的分析结果"""
        df_results = pd.DataFrame([
            {'相关系数': corr, '时间周期': tf, '数据周期': p, '最优延迟': ts}
            for corr, tf, p, ts in results
        ])
        
        logger.info(
            f"发现异常币种 | 交易所: {self.exchange_name} | 币种: {coin} | 差值: {diff_amount:.2f}"
        )
        
        # 飞书消息内容
        content = f"{self.exchange_name}\n\n{coin} 相关系数分析结果\n{df_results.to_string(index=False)}\n"
        content += f"\n差值: {diff_amount:.2f}"
        logger.debug(f"详细分析结果:\n{df_results.to_string(index=False)}")
        
        # 发送飞书通知
        alert_sent = False
        if self.lark_hook and HAS_LARK_BOT:
            try:
                result = sender(content, self.lark_hook)
                alert_sent = result is not None
                if not alert_sent:
                    logger.error(f"飞书通知发送失败（无返回结果）| 币种: {coin}")
            except Exception as e:
                logger.error(f"飞书通知发送失败 | {e}")
        else:
            logger.warning(f"飞书通知未发送（未配置）| 币种: {coin}")
        
        # 如果告警未成功发送，保存到本地文件作为备份
        # 修复BUG#10：增强文件告警保存健壮性
        if not alert_sent:
            alert_dir = "alerts"
            try:
                # 创建告警目录
                os.makedirs(alert_dir, exist_ok=True)

                # 检查写权限
                if not os.access(alert_dir, os.W_OK):
                    logger.error(f"告警目录无写权限: {alert_dir}")
                    return

            except Exception as e:
                logger.error(f"创建告警目录失败: {e}")
                return

            # 生成唯一文件名（时间戳 + UUID避免冲突）
            safe_coin = coin.replace('/', '_').replace(':', '_')
            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex[:8]
            alert_file = os.path.join(alert_dir, f"alert_{safe_coin}_{timestamp}_{unique_id}.txt")

            try:
                # 写入告警内容
                with open(alert_file, 'w', encoding='utf-8') as f:
                    f.write(f"告警时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"交易所: {self.exchange_name}\n")
                    f.write(f"币种: {coin}\n")
                    f.write(f"差值: {diff_amount:.2f}\n\n")
                    f.write("详细分析结果:\n")
                    f.write(df_results.to_string(index=False))

                logger.warning(f"告警已保存到本地文件: {alert_file}")
            except OSError as e:
                logger.error(f"保存告警文件失败: {e}")
            except Exception as e:
                logger.error(f"保存告警到本地文件失败: {e}")
    
    def one_coin_analysis(self, coin: str) -> bool:
        """
        分析单个币种与 BTC 的相关系数，识别异常模式
        
        Args:
            coin: 币种交易对名称，如 "ETH/USDC:USDC"
        
        Returns:
            是否发现异常模式
        """
        results = []
        
        for timeframe in self.timeframes:
            for period in self.periods:
                try:
                    result = self._analyze_single_combination(coin, timeframe, period)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"处理失败 | {coin} | {timeframe}/{period} | {e}")
        
        # 过滤 NaN 并按相关系数降序排序（修复BUG#4：同时检查corr和tau_star）
        valid_results = [(corr, tf, p, ts) for corr, tf, p, ts in results
                         if not np.isnan(corr) and not np.isnan(ts)]
        valid_results = sorted(valid_results, key=lambda x: x[0], reverse=True)
        
        if not valid_results:
            logger.warning(f"数据不足，无法分析 | 币种: {coin}")
            return False
        
        is_anomaly, diff_amount = self._detect_anomaly_pattern(valid_results)
        
        if is_anomaly:
            self._output_results(coin, valid_results, diff_amount)
            return True
        else:
            logger.debug(f"常规数据 | 币种: {coin}")
            return False
    
    def run(self, stop_event: Optional[threading.Event] = None):
        """
        分析交易所中所有 USDC 永续合约交易对

        修复BUG#12：支持优雅关闭

        Args:
            stop_event: 可选的停止事件，用于优雅关闭
        """
        logger.info(
            f"启动分析器 | 交易所: {self.exchange_name} | "
            f"时间周期: {self.timeframes} | 数据周期: {self.periods}"
        )

        # 初始化
        self.initialize()

        try:
            # 获取所有交易对
            usdc_coins = self.data_manager.get_usdc_perpetuals()
            total = len(usdc_coins)
            anomaly_count = 0
            skip_count = 0
            start_time = time.time()

            logger.info(f"发现 {total} 个 USDC 永续合约交易对")

            # 进度里程碑
            milestones = {max(1, int(total * p)) for p in [0.25, 0.5, 0.75, 1.0]}

            for idx, coin in enumerate(usdc_coins, 1):
                # 检查停止信号（修复BUG#12）
                if stop_event and stop_event.is_set():
                    logger.info(f"检测到停止信号，已分析 {idx-1}/{total} 个币种")
                    break

                logger.debug(f"检查币种: {coin}")

                try:
                    result = self.one_coin_analysis(coin)
                    if result:
                        anomaly_count += 1
                except Exception as e:
                    logger.error(f"分析币种失败 | {coin} | {e}")
                    skip_count += 1

                # 在里程碑位置打印进度
                if idx in milestones:
                    logger.info(f"分析进度: {idx}/{total} ({idx * 100 // total}%)")

                time.sleep(0.5)  # 降低请求频率

            elapsed = time.time() - start_time
            logger.info(
                f"分析完成 | 交易所: {self.exchange_name} | "
                f"总数: {total} | 异常: {anomaly_count} | 跳过: {skip_count} | "
                f"耗时: {elapsed:.1f}s | 平均: {elapsed/max(total, 1):.2f}s/币种"
            )

        finally:
            self.shutdown()
    
    def run_single(self, coin: str):
        """分析单个币种（用于测试）"""
        self.initialize()
        try:
            self.one_coin_analysis(coin)
        finally:
            self.shutdown()


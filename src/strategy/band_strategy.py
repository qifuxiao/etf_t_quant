"""
波段策略模块
负责波段交易的建仓、加仓、减仓、止盈、止损信号生成
"""

import math
from datetime import datetime, timedelta
from typing import Optional, List

from src.strategy.signal import TradingSignal, SignalType, Direction
from src.market_data import QuoteData, MarketModule
from src.log.logger import Logger


class BandStrategy:
    """波段策略"""
    
    def __init__(self, config, market: MarketModule, state_manager):
        """
        初始化波段策略
        
        Args:
            config: 配置对象
            market: 行情模块
            state_manager: 状态管理器
        """
        self.config = config
        self.market = market
        self.state_manager = state_manager
        
        # K线数据缓存
        self._kline_data: dict = {}
        
        Logger.info("波段策略初始化完成")
        
    def check_signals(self) -> Optional[TradingSignal]:
        """
        检查波段信号
        
        Returns:
            交易信号（无信号返回None）
        """
        # 获取当前持仓
        position = self.state_manager.get_band_position()
        
        if not position.has_position:
            # 检查建仓条件
            return self._check_entry_signals()
        else:
            # 检查持仓状态
            return self._check_position_signals()
            
    def _check_entry_signals(self) -> Optional[TradingSignal]:
        """
        检查建仓信号
        
        建仓条件：初始建仓比例60%
        """
        # 检查是否需要重新建仓（清仓后需等待3天）
        last_trade_date = self.state_manager.get_band_stats().get('last_trade_date', '')
        if last_trade_date:
            try:
                last_date = datetime.strptime(last_trade_date, "%Y%m%d")
                days_since = (datetime.now() - last_date).days
                if days_since < 3:
                    Logger.debug(f"建仓冷却期 | 距离上次清仓:{days_since}天")
                    return None
            except:
                pass
                
        # 获取行情
        quote = self.market.get_quote(self.config.stock_code)
        if not quote:
            return None
            
        # 计算建仓数量
        initial_fund = self.config.total_capital * self.config.band_initial_ratio
        quantity = int(initial_fund / quote.last_price / 100) * 100
        
        if quantity <= 0:
            return None
            
        Logger.info(
            f"波段建仓信号 | 价格:{quote.last_price:.2f} | "
            f"数量:{quantity} | 金额:{quantity*quote.last_price:.2f}"
        )
        
        return TradingSignal(
            signal_type=SignalType.BAND_BUY.value,
            direction=Direction.BUY.value,
            stock_code=self.config.stock_code,
            quantity=quantity,
            price=quote.last_price,
            reason="波段建仓 | 初始建仓60%",
            is_open_position=True
        )
        
    def _check_position_signals(self) -> Optional[TradingSignal]:
        """
        检查持仓后的信号
        
        检查顺序：止损 -> 止盈 -> 减仓 -> 加仓
        """
        position = self.state_manager.get_band_position()
        quote = self.market.get_quote(self.config.stock_code)
        
        if not quote or not position.has_position:
            return None
            
        # 计算持仓收益率
        profit_ratio = (quote.last_price - position.avg_cost) / position.avg_cost
        
        # 1. 检查止损
        signal = self._check_stop_loss(profit_ratio, position, quote)
        if signal:
            return signal
            
        # 2. 检查止盈
        signal = self._check_profit_take(profit_ratio, position, quote)
        if signal:
            return signal
            
        # 3. 检查减仓
        signal = self._check_reduce_position(profit_ratio, position, quote)
        if signal:
            return signal
            
        # 4. 检查加仓
        signal = self._check_add_position(profit_ratio, position, quote)
        if signal:
            return signal
            
        return None
        
    def _check_stop_loss(self, profit_ratio: float, position, quote) -> Optional[TradingSignal]:
        """
        检查止损条件
        
        止损类型：
        1. 固定止损: 持仓收益率 ≤ -5%
        2. 均线止损: 股价跌破20日均线
        3. 放量止损: 跌幅 ≥ 5% 且 量能 ≥ 20日均量200%
        4. 时间止损: 持仓30日且收益率 ≤ 0%
        """
        # 1. 固定止损
        if profit_ratio <= -self.config.band_stop_loss_fixed:
            Logger.info(
                f"波段止损-固定 | 收益率:{profit_ratio*100:.2f}% | "
                f"成本:{position.avg_cost:.2f} | 当前:{quote.last_price:.2f}"
            )
            
            return TradingSignal(
                signal_type=SignalType.BAND_SELL.value,
                direction=Direction.SELL.value,
                stock_code=self.config.stock_code,
                quantity=position.quantity,
                price=quote.last_price,
                reason=f"波段止损-固定 | 收益率≤{-self.config.band_stop_loss_fixed*100}%",
                is_open_position=False
            )
            
        # 2. 均线止损（需要K线数据）
        # TODO: 实现均线止损
        
        # 3. 放量止损
        if quote.change_pct <= -0.05:
            # TODO: 检查量能
            pass
            
        # 4. 时间止损
        if position.holding_days >= 30 and profit_ratio <= 0:
            Logger.info(
                f"波段止损-时间 | 持仓天数:{position.holding_days} | "
                f"收益率:{profit_ratio*100:.2f}%"
            )
            
            return TradingSignal(
                signal_type=SignalType.BAND_SELL.value,
                direction=Direction.SELL.value,
                stock_code=self.config.stock_code,
                quantity=position.quantity,
                price=quote.last_price,
                reason=f"波段止损-时间 | 持仓30日且收益率≤0%",
                is_open_position=False
            )
            
        return None
        
    def _check_profit_take(self, profit_ratio: float, position, quote) -> Optional[TradingSignal]:
        """
        检查止盈条件
        
        止盈类型（按优先级执行）：
        1. 分批止盈1: 收益率≥10% 减仓30%
        2. 分批止盈2: 收益率≥15% 再减仓30%
        3. 目标止盈: 收益率≥15% 清仓
        4. 加速止盈: 单日涨幅≥9% 减仓50%
        """
        band_config = self.config._config.get('band_strategy', {})
        reduce_records = self.state_manager.get_band_reduce_records()
        
        # 4. 加速止盈（优先级最高）
        if quote.change_pct >= 0.09:
            reduce_ratio = band_config.get('profit_accelerate', {}).get('reduce_ratio', 0.5)
            quantity = int(position.quantity * reduce_ratio / 100) * 100
            
            if quantity > 0:
                Logger.info(
                    f"波段止盈-加速 | 涨幅:{quote.change_pct*100:.2f}% | "
                    f"减仓数量:{quantity}"
                )
                
                return TradingSignal(
                    signal_type=SignalType.BAND_SELL.value,
                    direction=Direction.SELL.value,
                    stock_code=self.config.stock_code,
                    quantity=quantity,
                    price=quote.last_price,
                    reason=f"波段止盈-加速 | 单日涨幅≥9%",
                    is_open_position=False
                )
        
        # 3. 目标止盈（收益率≥15% 清仓）
        # PRD要求：持仓收益率 ≥ 15% → 全部清仓
        if profit_ratio >= 0.15:
            # 检查是否已完成分批止盈（分批止盈2是第二次减仓30%）
            # 如果已经执行过两次减仓，则执行目标止盈（清仓）
            if len(reduce_records) >= 2:
                Logger.info(
                    f"波段止盈-目标 | 收益率:{profit_ratio*100:.2f}% | "
                    f"清仓数量:{position.quantity}"
                )
                
                return TradingSignal(
                    signal_type=SignalType.BAND_SELL.value,
                    direction=Direction.SELL.value,
                    stock_code=self.config.stock_code,
                    quantity=position.quantity,
                    price=quote.last_price,
                    reason=f"波段止盈-目标 | 收益率≥15%清仓",
                    is_open_position=False
                )
                
        # 2. 分批止盈2（收益率≥15% 再减仓30%）
        # PRD要求：持仓收益率 ≥ 15% → 再减仓30%
        if profit_ratio >= 0.15:
            # 检查是否已经执行过分批止盈1（第一次减仓）
            if len(reduce_records) < 2:
                reduce_ratio = band_config.get('profit_take2', {}).get('reduce_ratio', 0.3)
                quantity = int(position.quantity * reduce_ratio / 100) * 100
                
                if quantity > 0:
                    Logger.info(
                        f"波段止盈-分批2 | 收益率:{profit_ratio*100:.2f}% | "
                        f"减仓数量:{quantity}"
                    )
                    
                    return TradingSignal(
                        signal_type=SignalType.BAND_SELL.value,
                        direction=Direction.SELL.value,
                        stock_code=self.config.stock_code,
                        quantity=quantity,
                        price=quote.last_price,
                        reason=f"波段止盈-分批2 | 收益率≥15%",
                        is_open_position=False
                    )
                    
        # 1. 分批止盈1（收益率≥10% 减仓30%）
        if profit_ratio >= 0.10:
            # 检查是否还未执行过分批止盈
            if len(reduce_records) < 1:
                reduce_ratio = band_config.get('profit_take1', {}).get('reduce_ratio', 0.3)
                quantity = int(position.quantity * reduce_ratio / 100) * 100
                
                if quantity > 0:
                    Logger.info(
                        f"波段止盈-分批1 | 收益率:{profit_ratio*100:.2f}% | "
                        f"减仓数量:{quantity}"
                    )
                    
                    return TradingSignal(
                        signal_type=SignalType.BAND_SELL.value,
                        direction=Direction.SELL.value,
                        stock_code=self.config.stock_code,
                        quantity=quantity,
                        price=quote.last_price,
                        reason=f"波段止盈-分批1 | 收益率≥10%",
                        is_open_position=False
                    )
                    
        return None
        
    def _check_reduce_position(self, profit_ratio: float, position, quote) -> Optional[TradingSignal]:
        """
        检查减仓条件
        
        减仓类型：
        1. 破线减仓: 股价跌破5日均线 且 5日均线向下 -20%
        2. 涨幅减仓: 单日涨幅≥7% 且 量能≥20日均量200% -20%
        3. 趋势减仓: 连续3日收盘价低于10日均线 -30%
        """
        # 检查当前仓位是否低于最小仓位
        min_position = self.config.total_capital * self.config.band_min_ratio / quote.last_price
        if position.quantity <= min_position:
            return None
            
        # 1. 涨幅减仓
        if quote.change_pct >= 0.07:
            # TODO: 检查量能
            reduce_ratio = 0.2
            quantity = int(position.quantity * reduce_ratio / 100) * 100
            
            if quantity > 0:
                Logger.info(
                    f"波段减仓-涨幅 | 涨幅:{quote.change_pct*100:.2f}% | "
                    f"减仓数量:{quantity}"
                )
                
                return TradingSignal(
                    signal_type=SignalType.BAND_SELL.value,
                    direction=Direction.SELL.value,
                    stock_code=self.config.stock_code,
                    quantity=quantity,
                    price=quote.last_price,
                    reason=f"波段减仓-涨幅 | 单日涨幅≥7%",
                    is_open_position=False
                )
                
        # TODO: 实现其他减仓条件
        
        return None
        
    def _check_add_position(self, profit_ratio: float, position, quote) -> Optional[TradingSignal]:
        """
        检查加仓条件
        
        加仓类型：
        1. 首次加仓: 股价站上5日均线 + 5日均线向上 + 量能≥120% +10%
        2. 二次加仓: 股价站上10日均线 + 10日均线向上 + 首次加仓后涨幅≥5% +10%
        3. 突破加仓: 股价突破20日高点 + 量能≥150% +10%
        
        最大仓位: 80%
        """
        # 检查是否达到最大仓位
        max_position = self.config.total_capital * self.config.band_max_ratio / quote.last_price
        if position.quantity >= max_position:
            return None
            
        # 获取加仓记录
        add_records = self.state_manager.get_band_add_records()
        
        # 获取均线数据用于判断
        ma_data = self._calculate_ma_data(quote)
        if not ma_data:
            return None
            
        # 1. 首次加仓：股价站上5日均线 + 5日均线向上 + 成交量 ≥ 5日均量120%
        if len(add_records) == 0:
            if self._check_first_add(quote, ma_data):
                add_ratio = 0.1
                quantity = int(self.config.total_capital * add_ratio / quote.last_price / 100) * 100
                
                if quantity > 0:
                    Logger.info(
                        f"波段加仓-首次 | 当前持仓:{position.quantity} | "
                        f"加仓数量:{quantity} | 价格:{quote.last_price:.2f} | "
                        f"MA5:{ma_data.get('ma5', 0):.2f} | 量能比:{ma_data.get('volume_ratio', 0)*100:.1f}%"
                    )
                    
                    return TradingSignal(
                        signal_type=SignalType.BAND_BUY.value,
                        direction=Direction.BUY.value,
                        stock_code=self.config.stock_code,
                        quantity=quantity,
                        price=quote.last_price,
                        reason=f"波段加仓-首次 | 站上5日均线+量能120%",
                        is_open_position=True
                    )
        
        # 2. 二次加仓：股价站上10日均线 + 10日均线向上 + 首次加仓后股价涨幅≥5%
        if len(add_records) == 1:
            if self._check_second_add(quote, ma_data, add_records, position):
                add_ratio = 0.1
                quantity = int(self.config.total_capital * add_ratio / quote.last_price / 100) * 100
                
                if quantity > 0:
                    Logger.info(
                        f"波段加仓-二次 | 当前持仓:{position.quantity} | "
                        f"加仓数量:{quantity} | 价格:{quote.last_price:.2f} | "
                        f"MA10:{ma_data.get('ma10', 0):.2f}"
                    )
                    
                    return TradingSignal(
                        signal_type=SignalType.BAND_BUY.value,
                        direction=Direction.BUY.value,
                        stock_code=self.config.stock_code,
                        quantity=quantity,
                        price=quote.last_price,
                        reason=f"波段加仓-二次 | 站上10日均线+涨幅≥5%",
                        is_open_position=True
                    )
        
        # 3. 突破加仓：股价突破20日高点 + 成交量 ≥ 20日均量150%
        if len(add_records) < 3:
            if self._check_breakout_add(quote, ma_data):
                add_ratio = 0.1
                quantity = int(self.config.total_capital * add_ratio / quote.last_price / 100) * 100
                
                if quantity > 0:
                    Logger.info(
                        f"波段加仓-突破 | 当前持仓:{position.quantity} | "
                        f"加仓数量:{quantity} | 价格:{quote.last_price:.2f} | "
                        f"20日高点:{ma_data.get('high20', 0):.2f} | 量能比:{ma_data.get('volume_ratio_20d', 0)*100:.1f}%"
                    )
                    
                    return TradingSignal(
                        signal_type=SignalType.BAND_BUY.value,
                        direction=Direction.BUY.value,
                        stock_code=self.config.stock_code,
                        quantity=quantity,
                        price=quote.last_price,
                        reason=f"波段加仓-突破 | 突破20日高点+量能150%",
                        is_open_position=True
                    )
        
        return None
    
    def _calculate_ma_data(self, quote) -> Optional[dict]:
        """
        计算均线数据
        
        Returns:
            包含MA5, MA10, MA5方向, MA20, 20日高点, 量能比的字典
        """
        try:
            # 从市场模块获取K线数据
            kline_data = self.market.get_kline(self.config.stock_code, days=25)
            if not kline_data or len(kline_data) < 20:
                Logger.debug("K线数据不足，无法计算均线")
                return None
                
            closes = [k.get('close', 0) for k in kline_data]
            volumes = [k.get('volume', 0) for k in kline_data]
            
            if not closes or len(closes) < 20:
                return None
                
            # 计算MA5（最近5日收盘价均值）
            ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else 0
            
            # 计算MA5方向（比较当前MA5与昨日MA5）
            ma5_yesterday = sum(closes[-6:-1]) / 5 if len(closes) >= 6 else ma5
            ma5_direction = 1 if ma5 > ma5_yesterday else (-1 if ma5 < ma5_yesterday else 0)
            
            # 计算MA10
            ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else 0
            ma10_yesterday = sum(closes[-11:-1]) / 10 if len(closes) >= 11 else ma10
            ma10_direction = 1 if ma10 > ma10_yesterday else (-1 if ma10 < ma10_yesterday else 0)
            
            # 计算MA20
            ma20 = sum(closes[-20:]) / 20
            
            # 计算20日最高价
            highs = [k.get('high', 0) for k in kline_data]
            high20 = max(highs[-20:]) if highs else 0
            
            # 计算5日均量
            avg_volume_5d = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
            
            # 计算20日均量
            avg_volume_20d = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 0
            
            # 计算量能比
            current_volume = volumes[-1] if volumes else 0
            volume_ratio = current_volume / avg_volume_5d if avg_volume_5d > 0 else 0
            volume_ratio_20d = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
            
            return {
                'ma5': ma5,
                'ma5_direction': ma5_direction,
                'ma10': ma10,
                'ma10_direction': ma10_direction,
                'ma20': ma20,
                'high20': high20,
                'avg_volume_5d': avg_volume_5d,
                'avg_volume_20d': avg_volume_20d,
                'volume_ratio': volume_ratio,
                'volume_ratio_20d': volume_ratio_20d,
                'close': closes[-1] if closes else 0,
                'add_records': add_records,
            }
            
        except Exception as e:
            Logger.error(f"计算均线数据失败: {e}")
            return None
    
    def _check_first_add(self, quote, ma_data: dict) -> bool:
        """
        检查首次加仓条件
        
        PRD要求：
        - 股价站上5日均线
        - 5日均线向上
        - 成交量 ≥ 5日均量120%
        """
        # 股价站上5日均线
        if quote.last_price <= ma_data.get('ma5', 0):
            Logger.debug(f"首次加仓条件不满足: 股价{quote.last_price:.2f}未站上MA5{ma_data.get('ma5', 0):.2f}")
            return False
            
        # 5日均线向上
        if ma_data.get('ma5_direction', 0) != 1:
            Logger.debug(f"首次加仓条件不满足: MA5方向{ma_data.get('ma5_direction', 0)}向下或走平")
            return False
            
        # 成交量 ≥ 5日均量120%
        volume_ratio = ma_data.get('volume_ratio', 0)
        if volume_ratio < 1.2:
            Logger.debug(f"首次加仓条件不满足: 量能比{volume_ratio*100:.1f}% < 120%")
            return False
            
        return True
    
    def _check_second_add(self, quote, ma_data: dict, add_records: list, position) -> bool:
        """
        检查二次加仓条件
        
        PRD要求：
        - 股价站上10日均线
        - 10日均线向上
        - 首次加仓后股价涨幅 ≥ 5%
        """
        # 股价站上10日均线
        if quote.last_price <= ma_data.get('ma10', 0):
            Logger.debug(f"二次加仓条件不满足: 股价{quote.last_price:.2f}未站上MA10{ma_data.get('ma10', 0):.2f}")
            return False
            
        # 10日均线向上
        if ma_data.get('ma10_direction', 0) != 1:
            Logger.debug(f"二次加仓条件不满足: MA10方向{ma_data.get('ma10_direction', 0)}向下或走平")
            return False
            
        # 首次加仓后股价涨幅 ≥ 5%
        if add_records:
            first_add_price = add_records[0].get('price', 0)
            if first_add_price > 0:
                price_increase = (quote.last_price - first_add_price) / first_add_price
                if price_increase < 0.05:
                    Logger.debug(f"二次加仓条件不满足: 首次加仓后涨幅{price_increase*100:.2f}% < 5%")
                    return False
                    
        return True
    
    def _check_breakout_add(self, quote, ma_data: dict) -> bool:
        """
        检查突破加仓条件
        
        PRD要求：
        - 股价突破20日高点
        - 成交量 ≥ 20日均量150%
        """
        high20 = ma_data.get('high20', 0)
        
        # 股价突破20日高点
        if high20 <= 0 or quote.last_price <= high20:
            Logger.debug(f"突破加仓条件不满足: 当前价{quote.last_price:.2f}未突破20日高点{high20:.2f}")
            return False
            
        # 成交量 ≥ 20日均量150%
        volume_ratio_20d = ma_data.get('volume_ratio_20d', 0)
        if volume_ratio_20d < 1.5:
            Logger.debug(f"突破加仓条件不满足: 20日量能比{volume_ratio_20d*100:.1f}% < 150%")
            return False
            
        return True
        
    def calculate_holding_days(self, entry_date: str) -> int:
        """
        计算持仓天数
        
        Args:
            entry_date: 建仓日期
            
        Returns:
            持仓天数
        """
        if not entry_date:
            return 0
            
        try:
            date = datetime.strptime(entry_date, "%Y%m%d")
            return (datetime.now() - date).days
        except:
            return 0
            
    def update_band_stats(self, signal_type: str, profit: float):
        """
        更新波段统计
        
        Args:
            signal_type: 信号类型
            profit: 盈亏金额
        """
        stats = self.state_manager.get_band_stats()
        
        if profit > 0:
            stats['profit_trades'] = stats.get('profit_trades', 0) + 1
            stats['continuous_loss'] = 0
        else:
            stats['loss_trades'] = stats.get('loss_trades', 0) + 1
            stats['continuous_loss'] = stats.get('continuous_loss', 0) + 1
            
        stats['total_trades'] = stats.get('total_trades', 0) + 1
        stats['total_profit'] = stats.get('total_profit', 0) + profit
        stats['last_trade_date'] = datetime.now().strftime("%Y%m%d")
        
        # 记录状态
        self.state_manager.save_state()
        
        Logger.info(
            f"波段统计更新 | 总次数:{stats['total_trades']} | "
            f"盈利:{stats.get('profit_trades', 0)} | 亏损:{stats.get('loss_trades', 0)} | "
            f"连续亏损:{stats.get('continuous_loss', 0)}"
        )

"""
做T策略模块
负责做多T和做空T的信号生成
"""

import math
from datetime import datetime
from typing import Optional

from src.strategy.signal import TradingSignal, SignalType, Direction
from src.market_data import QuoteData, VWAPData, MarketModule
from src.log.logger import Logger


class TStrategy:
    """做T策略"""
    
    def __init__(self, config, market: MarketModule, state_manager):
        """
        初始化做T策略
        
        Args:
            config: 配置对象
            market: 行情模块
            state_manager: 状态管理器
        """
        self.config = config
        self.market = market
        self.state_manager = state_manager
        
        Logger.info("做T策略初始化完成")
        
    def check_signals(self, quote: QuoteData) -> Optional[TradingSignal]:
        """
        检查做T信号
        
        Args:
            quote: 实时行情数据
            
        Returns:
            交易信号（无信号返回None）
        """
        # 获取做T仓位状态
        t_position = self.state_manager.get_t_position()
        
        # 检查做多T仓位
        if t_position.has_long_position:
            # 检查平仓条件
            signal = self._check_long_t_close(quote, t_position)
            if signal:
                return signal
        else:
            # 检查开仓条件
            signal = self._check_long_t_open(quote, t_position)
            if signal:
                return signal
                
        # 检查做空T仓位
        if t_position.has_short_position:
            # 检查平仓条件
            signal = self._check_short_t_close(quote, t_position)
            if signal:
                return signal
        else:
            # 检查开仓条件
            signal = self._check_short_t_open(quote, t_position)
            if signal:
                return signal
                
        return None
        
    def _check_long_t_open(self, quote: QuoteData, t_position) -> Optional[TradingSignal]:
        """
        检查做多T开仓条件
        
        条件：
        1. 当前价格 ≤ 分时均线 - 0.3%
        2. 股价跌幅 ≥ 2%
        """
        # 获取VWAP数据
        vwap_data = self.market.get_vwap(quote.stock_code)
        if not vwap_data:
            return None
            
        # 条件1: 当前价格 ≤ 分时均线 - 0.3%
        price_condition = quote.last_price <= vwap_data.vwap * (1 - self.config.t_trigger_deviation)
        
        # 条件2: 股价跌幅 ≥ 2%
        drop_condition = quote.change_pct <= -self.config.t_trigger_drop
        
        if price_condition and drop_condition:
            # 计算买入数量
            quantity = self._calculate_long_t_quantity(quote.last_price)
            if quantity > 0:
                Logger.info(
                    f"做多T开仓信号 | 价格:{quote.last_price:.2f} | "
                    f"Vwap:{vwap_data.vwap:.2f} | 跌幅:{quote.change_pct*100:.2f}%"
                )
                
                return TradingSignal(
                    signal_type=SignalType.T_LONG_BUY.value,
                    direction=Direction.BUY.value,
                    stock_code=self.config.stock_code,
                    quantity=quantity,
                    price=quote.last_price,
                    reason=f"做多T开仓 | 价格≤均线-{self.config.t_trigger_deviation*100}% | 跌幅≥{self.config.t_trigger_drop*100}%",
                    is_open_position=True
                )
                
        return None
        
    def _check_long_t_close(self, quote: QuoteData, t_position) -> Optional[TradingSignal]:
        """
        检查做多T平仓条件
        
        条件（三选一）：
        1. 止盈: 当前价格 ≥ 买入价格 + 0.5%
        2. 止损: 当前价格 ≤ 买入价格 - 1.0%
        3. 保本: 分时均线走平
        """
        buy_price = t_position.long_buy_price
        
        # 止盈条件
        if quote.last_price >= buy_price * (1 + self.config.t_profit_target):
            Logger.info(
                f"做多T平仓-止盈 | 买入价:{buy_price:.2f} | "
                f"当前价:{quote.last_price:.2f} | 涨幅:{(quote.last_price/buy_price-1)*100:.2f}%"
            )
            
            return TradingSignal(
                signal_type=SignalType.T_LONG_SELL.value,
                direction=Direction.SELL.value,
                stock_code=self.config.stock_code,
                quantity=t_position.long_quantity,
                price=quote.last_price,
                reason=f"做多T止盈 | 涨幅≥{self.config.t_profit_target*100}%",
                is_open_position=False
            )
            
        # 止损条件
        if quote.last_price <= buy_price * (1 - self.config.t_loss_stop):
            Logger.info(
                f"做多T平仓-止损 | 买入价:{buy_price:.2f} | "
                f"当前价:{quote.last_price:.2f} | 跌幅:{(1-quote.last_price/buy_price)*100:.2f}%"
            )
            
            return TradingSignal(
                signal_type=SignalType.T_LONG_SELL.value,
                direction=Direction.SELL.value,
                stock_code=self.config.stock_code,
                quantity=t_position.long_quantity,
                price=quote.last_price,
                reason=f"做多T止损 | 跌幅≥{self.config.t_loss_stop*100}%",
                is_open_position=False
            )
            
        # 保本条件（均线走平）
        vwap_data = self.market.get_vwap(quote.stock_code)
        if vwap_data and vwap_data.is_flat:
            Logger.info(
                f"做多T平仓-保本 | 买入价:{buy_price:.2f} | "
                f"当前价:{quote.last_price:.2f} | 均线走平"
            )
            
            return TradingSignal(
                signal_type=SignalType.T_LONG_SELL.value,
                direction=Direction.SELL.value,
                stock_code=self.config.stock_code,
                quantity=t_position.long_quantity,
                price=quote.last_price,
                reason="做多T保本 | 分时均线走平",
                is_open_position=False
            )
            
        return None
        
    def _check_short_t_open(self, quote: QuoteData, t_position) -> Optional[TradingSignal]:
        """
        检查做空T开仓条件
        
        条件：
        1. 当前价格 ≥ 分时均线 + 0.3%
        2. 股价涨幅 ≥ 2%
        """
        # 获取波段持仓（做空T需要先有持仓）
        band_position = self.state_manager.get_band_position()
        if not band_position.has_position or band_position.quantity < self.config.t_min_position:
            return None
            
        # 获取VWAP数据
        vwap_data = self.market.get_vwap(quote.stock_code)
        if not vwap_data:
            return None
            
        # 条件1: 当前价格 ≥ 分时均线 + 0.3%
        price_condition = quote.last_price >= vwap_data.vwap * (1 + self.config.t_trigger_deviation)
        
        # 条件2: 股价涨幅 ≥ 2%
        rise_condition = quote.change_pct >= self.config.t_trigger_drop
        
        if price_condition and rise_condition:
            # 计算卖出数量
            quantity = self._calculate_short_t_quantity(band_position.quantity)
            if quantity > 0:
                Logger.info(
                    f"做空T开仓信号 | 价格:{quote.last_price:.2f} | "
                    f"Vwap:{vwap_data.vwap:.2f} | 涨幅:{quote.change_pct*100:.2f}%"
                )
                
                return TradingSignal(
                    signal_type=SignalType.T_SHORT_SELL.value,
                    direction=Direction.SELL.value,
                    stock_code=self.config.stock_code,
                    quantity=quantity,
                    price=quote.last_price,
                    reason=f"做空T开仓 | 价格≥均线+{self.config.t_trigger_deviation*100}% | 涨幅≥{self.config.t_trigger_drop*100}%",
                    is_open_position=True
                )
                
        return None
        
    def _check_short_t_close(self, quote: QuoteData, t_position) -> Optional[TradingSignal]:
        """
        检查做空T平仓条件
        
        条件（三选一）：
        1. 止盈: 当前价格 ≤ 卖出价格 - 0.5%
        2. 止损: 当前价格 ≥ 卖出价格 + 1.0%
        3. 保本: 分时均线走平
        """
        sell_price = t_position.short_sell_price
        
        # 止盈条件
        if quote.last_price <= sell_price * (1 - self.config.t_profit_target):
            Logger.info(
                f"做空T平仓-止盈 | 卖出价:{sell_price:.2f} | "
                f"当前价:{quote.last_price:.2f} | 跌幅:{(1-quote.last_price/sell_price)*100:.2f}%"
            )
            
            return TradingSignal(
                signal_type=SignalType.T_SHORT_BUY.value,
                direction=Direction.BUY.value,
                stock_code=self.config.stock_code,
                quantity=t_position.short_quantity,
                price=quote.last_price,
                reason=f"做空T止盈 | 跌幅≥{self.config.t_profit_target*100}%",
                is_open_position=False
            )
            
        # 止损条件
        if quote.last_price >= sell_price * (1 + self.config.t_loss_stop):
            Logger.info(
                f"做空T平仓-止损 | 卖出价:{sell_price:.2f} | "
                f"当前价:{quote.last_price:.2f} | 涨幅:{(quote.last_price/sell_price-1)*100:.2f}%"
            )
            
            return TradingSignal(
                signal_type=SignalType.T_SHORT_BUY.value,
                direction=Direction.BUY.value,
                stock_code=self.config.stock_code,
                quantity=t_position.short_quantity,
                price=quote.last_price,
                reason=f"做空T止损 | 涨幅≥{self.config.t_loss_stop*100}%",
                is_open_position=False
            )
            
        # 保本条件（均线走平）
        vwap_data = self.market.get_vwap(quote.stock_code)
        if vwap_data and vwap_data.is_flat:
            Logger.info(
                f"做空T平仓-保本 | 卖出价:{sell_price:.2f} | "
                f"当前价:{quote.last_price:.2f} | 均线走平"
            )
            
            return TradingSignal(
                signal_type=SignalType.T_SHORT_BUY.value,
                direction=Direction.BUY.value,
                stock_code=self.config.stock_code,
                quantity=t_position.short_quantity,
                price=quote.last_price,
                reason="做空T保本 | 分时均线走平",
                is_open_position=False
            )
            
        return None
        
    def _calculate_long_t_quantity(self, current_price: float) -> int:
        """
        计算做多T买入数量
        
        数量计算：
        1. 按资金计算: MIN(总资金×10%, 20000元) / 当前价格
        2. 按底仓比例: 底仓数量×30%
        3. 取两者最小值，且为100的倍数
        """
        # 获取可用资金
        account = self.state_manager.get_account()
        
        # 按资金计算
        available_fund = min(self.config.total_capital * 0.1, self.config.t_max_fund)
        qty_by_fund = int(available_fund / current_price / 100) * 100
        
        # 按底仓比例计算
        band_position = self.state_manager.get_band_position()
        if band_position.has_position:
            qty_by_ratio = int(band_position.quantity * self.config.t_max_ratio / 100) * 100
        else:
            qty_by_ratio = 0
            
        # 取最小值
        quantity = min(qty_by_fund, qty_by_ratio)
        
        # 资金校验
        if account.available < 1000 or account.available < current_price * 100:
            quantity = 0
            
        return quantity
        
    def _calculate_short_t_quantity(self, holding_quantity: int) -> int:
        """
        计算做空T卖出数量
        
        数量计算：
        1. 按持仓比例: 持仓数量×30%
        2. 按最大值限制: 1000股
        3. 取两者最小值，且为100的倍数
        """
        # 按持仓比例
        qty_by_ratio = int(holding_quantity * self.config.t_max_ratio / 100) * 100
        
        # 按最大值限制
        qty_by_max = self.config.t_max_single_quantity
        
        # 取最小值
        quantity = min(qty_by_ratio, qty_by_max)
        
        # 确保是100的倍数
        quantity = int(quantity / 100) * 100
        
        return quantity
        
    def update_t_stats(self, signal_type: str, profit: float):
        """
        更新做T统计
        
        Args:
            signal_type: 信号类型
            profit: 盈亏金额
        """
        t_position = self.state_manager.get_t_position()
        
        if profit > 0:
            t_position.success_count += 1
            t_position.continuous_loss = 0
        else:
            t_position.fail_count += 1
            t_position.continuous_loss += 1
            
        t_position.total_t_count += 1
        t_position.total_profit += profit
        t_position.last_t_date = datetime.now().strftime("%Y%m%d")
        
        # 记录状态
        self.state_manager.save_state()
        
        Logger.info(
            f"做T统计更新 | 总次数:{t_position.total_t_count} | "
            f"成功:{t_position.success_count} | 失败:{t_position.fail_count} | "
            f"连续亏损:{t_position.continuous_loss} | 总盈亏:{t_position.total_profit:.2f}"
        )

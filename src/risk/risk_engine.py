"""
风控引擎模块
负责风险控制和合规检查
"""

from datetime import datetime, timedelta
from typing import Optional

from src.log.logger import Logger


class RiskEngine:
    """风控引擎"""
    
    def __init__(self, config, state_manager, market):
        """
        初始化风控引擎
        
        Args:
            config: 配置对象
            state_manager: 状态管理器
            market: 行情模块
        """
        self.config = config
        self.state_manager = state_manager
        self.market = market
        
        # 熔断状态
        self.t_circuit_broken = False
        self.t_circuit_start_date = None
        self.band_circuit_broken = False
        self.band_circuit_start_date = None
        
        Logger.info("风控引擎初始化完成")
        
    def check_signal(self, signal) -> bool:
        """
        检查交易信号是否通过风控
        
        Args:
            signal: 交易信号
            
        Returns:
            是否通过风控检查
        """
        # 1. 检查时间限制
        if not self._check_time_allowed(signal):
            Logger.log_risk_block("时间限制", f"时间:{datetime.now().strftime('%H:%M:%S')} 禁止交易")
            return False
            
        # 2. 检查资金限制
        if signal.direction == "BUY":
            if not self._check_fund_available(signal):
                Logger.log_risk_block("资金限制", "可用资金不足")
                return False
                
        # 3. 检查持仓限制
        if signal.direction == "SELL":
            if not self._check_position_available(signal):
                Logger.log_risk_block("持仓限制", "可用持仓不足")
                return False
                
        # 4. 检查熔断状态
        if self._check_circuit_broken(signal):
            Logger.log_risk_block("熔断限制", "策略处于熔断状态")
            return False
            
        # 5. 检查市场环境
        if not self._check_market_environment():
            Logger.log_risk_block("市场环境", "市场环境恶劣")
            return False
            
        # 6. 检查涨跌停限制
        if not self._check_limit_up_down(signal):
            Logger.log_risk_block("涨跌停限制", "涨跌停无法交易")
            return False
            
        # 7. 检查波动率限制
        if not self._check_volatility(signal):
            Logger.log_risk_block("波动率限制", "波动率过低")
            return False
            
        return True
        
    def _check_time_allowed(self, signal) -> bool:
        """
        检查时间是否允许交易
        
        规则：
        1. 开仓时间截止14:55
        2. 必须在交易时段内
        """
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_date = now.strftime("%Y%m%d")
        
        # 判断是否周末
        if now.weekday() >= 5:
            return False
            
        # 14:55后禁止开新仓
        if signal.is_open_position and current_time >= self.config.trading_afternoon_end:
            return False
            
        # 检查交易时段
        trading_hours = [
            (self.config.trading_morning_start, self.config.trading_morning_end),
            (self.config.trading_afternoon_start, self.config.trading_afternoon_end)
        ]
        
        for start, end in trading_hours:
            if start <= current_time <= end:
                return True
                
        return False
        
    def _check_fund_available(self, signal) -> bool:
        """
        检查可用资金
        
        规则：
        1. 可用资金 >= 1000元
        2. 可用资金 >= 买入1手所需资金
        """
        account = self.state_manager.get_account()
        
        # 最低资金限制
        if account.available < self.config.t_min_fund:
            return False
            
        # 买入1手所需资金
        required = signal.price * 100
        if account.available < required:
            return False
            
        # 检查是否超过可用资金
        required_total = signal.price * signal.quantity
        if account.available < required_total:
            return False
            
        return True
        
    def _check_position_available(self, signal) -> bool:
        """
        检查可用持仓
        
        规则：
        1. 做空T需要持仓 >= 100股
        """
        position = self.state_manager.get_band_position()
        
        # 做空T需要持仓
        if "T_SHORT" in signal.signal_type:
            if position.quantity < self.config.t_min_position:
                return False
                
        # 检查卖出数量是否超过持仓
        if signal.direction == "SELL":
            if signal.quantity > position.quantity:
                return False
                
        return True
        
    def _check_circuit_broken(self, signal) -> bool:
        """
        检查熔断状态
        
        规则：
        1. 做T连续亏损3次，熔断1天
        2. 波段连续亏损2次，熔断3天
        """
        today = datetime.now().strftime("%Y%m%d")
        
        # 检查做T熔断
        if "T_" in signal.signal_type:
            if self.t_circuit_broken:
                if self.t_circuit_start_date != today:
                    # 新的一天，解除熔断
                    self.t_circuit_broken = False
                    self.t_circuit_start_date = None
                    Logger.info("做T熔断已解除")
                else:
                    return True
                    
        # 检查波段熔断
        if "BAND_" in signal.signal_type:
            if self.band_circuit_broken:
                if self.band_circuit_start_date:
                    start_date = datetime.strptime(self.band_circuit_start_date, "%Y%m%d")
                    days_since = (datetime.now() - start_date).days
                    if days_since >= self.config.risk_band_circuit_duration:
                        # 熔断期结束
                        self.band_circuit_broken = False
                        self.band_circuit_start_date = None
                        Logger.info("波段熔断已解除")
                    else:
                        return True
                        
        return False
        
    def _check_market_environment(self) -> bool:
        """
        检查市场环境
        
        规则：
        1. 大盘跌幅 < 5%
        2. 板块跌幅 < 6%
        """
        market_drop = self.market.get_market_drop()
        
        if market_drop >= self.config.risk_market_drop_limit:
            Logger.warning(f"市场环境恶劣 | 大盘跌幅:{market_drop*100:.2f}%")
            return False
            
        return True
        
    def _check_limit_up_down(self, signal) -> bool:
        """
        检查涨跌停限制
        
        规则：
        1. 涨停禁止做空T卖出
        2. 跌停禁止做多T买入
        """
        quote = self.market.get_quote(self.config.stock_code)
        if not quote:
            return True
            
        # 涨停禁止做空T
        if signal.signal_type == "T_SHORT_SELL":
            # 涨幅>=9.9%近似认为是涨停
            if quote.change_pct >= 0.099:
                Logger.warning(f"涨停限制 | 涨幅:{quote.change_pct*100:.2f}% 禁止做空T")
                return False
                
        # 跌停禁止做多T
        if signal.signal_type == "T_LONG_BUY":
            # 跌幅<=-9.9%近似认为是跌停
            if quote.change_pct <= -0.099:
                Logger.warning(f"跌停限制 | 跌幅:{quote.change_pct*100:.2f}% 禁止做多T")
                return False
                
        return True
        
    def _check_volatility(self, signal) -> bool:
        """
        检查波动率限制
        
        规则：
        1. 做T: 5分钟振幅<1%持续30分钟禁止做T
        2. 波段: 20日波动率<2%禁止开仓
        """
        # 做T波动率检查
        if "T_" in signal.signal_type:
            if self.market.check_low_amplitude(self.config.stock_code):
                Logger.warning("低波动率限制 | 5分钟振幅<1%持续30分钟")
                return False
                
        # 波段波动率检查
        if "BAND_" in signal.signal_type and signal.is_open_position:
            volatility = self.market.calculate_volatility_20d(self.config.stock_code)
            if volatility < self.config.risk_band_volatility_limit:
                Logger.warning(f"低波动率限制 | 20日波动率:{volatility*100:.2f}%")
                return False
                
        return True
        
    # ==================== 熔断触发 ====================
    
    def trigger_circuit(self, signal_type: str):
        """
        触发熔断
        
        Args:
            signal_type: 信号类型
        """
        today = datetime.now().strftime("%Y%m%d")
        
        if "T_" in signal_type:
            if not self.t_circuit_broken:
                self.t_circuit_broken = True
                self.t_circuit_start_date = today
                Logger.log_circuit_triggered("做T熔断", f"连续亏损触发 | 开始日期:{today}")
                
        elif "BAND_" in signal_type:
            if not self.band_circuit_broken:
                self.band_circuit_broken = True
                self.band_circuit_start_date = today
                Logger.log_circuit_triggered("波段熔断", f"连续亏损触发 | 开始日期:{today}")
                
    def check_circuit_condition(self):
        """
        检查是否触发熔断条件
        
        在每次平仓后调用
        """
        # 检查做T连续亏损
        t_position = self.state_manager.get_t_position()
        if t_position.continuous_loss >= self.config.risk_t_continuous_loss_limit:
            self.trigger_circuit("T_CIRCUIT")
            
        # 检查波段连续亏损
        band_stats = self.state_manager.get_band_stats()
        if band_stats.get('continuous_loss', 0) >= self.config.risk_band_continuous_loss_limit:
            self.trigger_circuit("BAND_CIRCUIT")
            
    # ==================== 强制风控 ====================
    
    def emergency_stop(self) -> bool:
        """
        紧急停止所有交易
        
        Returns:
            是否执行了紧急停止
        """
        # 大盘跌幅超过7%
        market_drop = self.market.get_market_drop()
        if market_drop >= 0.07:
            Logger.critical(f"紧急停止 | 大盘跌幅:{market_drop*100:.2f}%")
            return True
            
        # 连续亏损超过5次
        t_position = self.state_manager.get_t_position()
        if t_position.continuous_loss >= 5:
            Logger.critical("紧急停止 | 做T连续亏损5次")
            return True
            
        return False
        
    def get_risk_status(self) -> dict:
        """
        获取风控状态
        
        Returns:
            风控状态字典
        """
        return {
            "t_circuit_broken": self.t_circuit_broken,
            "t_circuit_start_date": self.t_circuit_start_date,
            "band_circuit_broken": self.band_circuit_broken,
            "band_circuit_start_date": self.band_circuit_start_date,
            "market_drop": self.market.get_market_drop()
        }

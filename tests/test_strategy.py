"""
ETF T策略量化交易系统 - 测试用例
根据PRD规则进行测试验证
"""

import sys
import os
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== PRD参数一致性验证 ====================
# 这些常量定义了PRD中的精确规则，用于验证代码实现是否正确

# 做T策略PRD参数
PRD_T_PARAMS = {
    "做多T买入触发跌幅": 0.02,  # 2%
    "做多T买入触发偏离": 0.003,  # 0.3%
    "做多T止盈": 0.005,  # 0.5%
    "做多T止损": 0.01,  # 1.0%
    "做空T止盈": 0.005,  # 0.5%
    "做空T止损": 0.01,  # 1.0%
    "做T最大资金": 20000,
    "做T最大比例": 0.3,  # 30%
    "做空T单次最大": 1000,
    "分时均线走平斜率": 0.001,
    "分时均线走平变化率": 0.001,
}

# 波段策略PRD参数
PRD_BAND_PARAMS = {
    "初始建仓比例": 0.6,  # 60%
    "最大仓位": 0.8,  # 80%
    "最小仓位": 0.3,  # 30%
    "首次加仓比例": 0.1,  # 10%
    "首次加仓量能": 1.2,  # 120%
    "二次加仓比例": 0.1,  # 10%
    "突破加仓比例": 0.1,  # 10%
    "止盈1": 0.10,  # 10%
    "止盈1减仓比例": 0.3,  # 30%
    "止盈2": 0.15,  # 15%
    "止盈2减仓比例": 0.3,  # 30%
    "加速止盈涨幅": 0.09,  # 9%
    "加速止盈减仓比例": 0.5,  # 50%
    "固定止损": 0.05,  # 5%
}

# 风控规则PRD参数
PRD_RISK_PARAMS = {
    "大盘跌幅限制": 0.05,  # 5%
    "板块跌幅限制": 0.06,  # 6%
    "做T连续亏损熔断": 3,  # 3次
    "做T熔断持续": 1,  # 1天
    "波段连续亏损熔断": 2,  # 2次
    "波段熔断持续": 3,  # 3天
    "做T波动率限制": 0.01,  # 1%
    "做T波动率持续": 30,  # 30分钟
    "波段波动率限制": 0.02,  # 2%
    "做空T最低持仓": 100,
    "做T最低资金": 1000,
    "开仓截止时间": "14:55",
}


class TestConfigPRDConsistency:
    """配置参数与PRD一致性测试"""

    def test_t_strategy_params_match_prd(self):
        """测试做T策略参数与PRD是否一致"""
        from src.config import Config
        
        config = Config()
        
        # 做多T买入触发跌幅 ≥ 2%
        assert config.t_trigger_drop == PRD_T_PARAMS["做多T买入触发跌幅"], \
            f"做多T买入触发跌幅应为{PRD_T_PARAMS['做多T买入触发跌幅']}，实际为{config.t_trigger_drop}"
        
        # 做多T买入触发偏离 ≤ 分时均线 - 0.3%
        assert config.t_trigger_deviation == PRD_T_PARAMS["做多T买入触发偏离"], \
            f"做多T买入触发偏离应为{PRD_T_PARAMS['做多T买入触发偏离']}，实际为{config.t_trigger_deviation}"
        
        # 做多T止盈 ≥ 买入价 + 0.5%
        assert config.t_profit_target == PRD_T_PARAMS["做多T止盈"], \
            f"做多T止盈应为{PRD_T_PARAMS['做多T止盈']}，实际为{config.t_profit_target}"
        
        # 做多T止损 ≤ 买入价 - 1.0%
        assert config.t_loss_stop == PRD_T_PARAMS["做多T止损"], \
            f"做多T止损应为{PRD_T_PARAMS['做多T止损']}，实际为{config.t_loss_stop}"
        
        # 做T最大资金
        assert config.t_max_fund == PRD_T_PARAMS["做T最大资金"], \
            f"做T最大资金应为{PRD_T_PARAMS['做T最大资金']}，实际为{config.t_max_fund}"
        
        # 做T最大比例
        assert config.t_max_ratio == PRD_T_PARAMS["做T最大比例"], \
            f"做T最大比例应为{PRD_T_PARAMS['做T最大比例']}，实际为{config.t_max_ratio}"
        
        # 做空T单次最大数量
        assert config.t_max_single_quantity == PRD_T_PARAMS["做空T单次最大"], \
            f"做空T单次最大数量应为{PRD_T_PARAMS['做空T单次最大']}，实际为{config.t_max_single_quantity}"

    def test_band_strategy_params_match_prd(self):
        """测试波段策略参数与PRD是否一致"""
        from src.config import Config
        
        config = Config()
        
        # 初始建仓比例 60%
        assert config.band_initial_ratio == PRD_BAND_PARAMS["初始建仓比例"], \
            f"初始建仓比例应为{PRD_BAND_PARAMS['初始建仓比例']}，实际为{config.band_initial_ratio}"
        
        # 最大仓位 80%
        assert config.band_max_ratio == PRD_BAND_PARAMS["最大仓位"], \
            f"最大仓位应为{PRD_BAND_PARAMS['最大仓位']}，实际为{config.band_max_ratio}"
        
        # 最小仓位 30%
        assert config.band_min_ratio == PRD_BAND_PARAMS["最小仓位"], \
            f"最小仓位应为{PRD_BAND_PARAMS['最小仓位']}，实际为{config.band_min_ratio}"
        
        # 固定止损 -5%
        assert config.band_stop_loss_fixed == PRD_BAND_PARAMS["固定止损"], \
            f"固定止损应为{PRD_BAND_PARAMS['固定止损']}，实际为{config.band_stop_loss_fixed}"

    def test_risk_params_match_prd(self):
        """测试风控参数与PRD是否一致"""
        from src.config import Config
        
        config = Config()
        
        # 大盘跌幅 ≥ 5% 禁止开仓
        assert config.risk_market_drop_limit == PRD_RISK_PARAMS["大盘跌幅限制"], \
            f"大盘跌幅限制应为{PRD_RISK_PARAMS['大盘跌幅限制']}，实际为{config.risk_market_drop_limit}"
        
        # 做T连续亏损 ≥ 3次熔断1天
        assert config.risk_t_continuous_loss_limit == PRD_RISK_PARAMS["做T连续亏损熔断"], \
            f"做T连续亏损熔断应为{PRD_RISK_PARAMS['做T连续亏损熔断']}，实际为{config.risk_t_continuous_loss_limit}"
        
        assert config.risk_t_circuit_duration == PRD_RISK_PARAMS["做T熔断持续"], \
            f"做T熔断持续应为{PRD_RISK_PARAMS['做T熔断持续']}，实际为{config.risk_t_circuit_duration}"
        
        # 波段连续亏损 ≥ 2次熔断3天
        assert config.risk_band_continuous_loss_limit == PRD_RISK_PARAMS["波段连续亏损熔断"], \
            f"波段连续亏损熔断应为{PRD_RISK_PARAMS['波段连续亏损熔断']}，实际为{config.risk_band_continuous_loss_limit}"
        
        assert config.risk_band_circuit_duration == PRD_RISK_PARAMS["波段熔断持续"], \
            f"波段熔断持续应为{PRD_RISK_PARAMS['波段熔断持续']}，实际为{config.risk_band_circuit_duration}"


class TestConfig:
    """配置类测试"""
    
    def test_config_loading(self):
        """测试配置加载"""
        from src.config import Config
        
        config = Config()
        
        # 检查基础配置
        assert config.stock_code == "300124"
        assert config.total_capital == 200000
        assert config.band_position_ratio == 0.6
        assert config.t_position_fund == 20000
        
    def test_trading_hours(self):
        """测试交易时间段"""
        from src.config import Config
        
        config = Config()
        
        assert config.trading_morning_start == "09:30"
        assert config.trading_morning_end == "11:30"
        assert config.trading_afternoon_start == "13:00"
        assert config.trading_afternoon_end == "14:55"
        
    def test_t_strategy_params(self):
        """测试做T策略参数"""
        from src.config import Config
        
        config = Config()
        
        assert config.t_max_fund == 20000
        assert config.t_max_ratio == 0.3
        assert config.t_trigger_drop == 0.02
        assert config.t_trigger_deviation == 0.003
        assert config.t_profit_target == 0.005
        assert config.t_loss_stop == 0.01
        
    def test_band_strategy_params(self):
        """测试波段策略参数"""
        from src.config import Config
        
        config = Config()
        
        assert config.band_initial_ratio == 0.6
        assert config.band_max_ratio == 0.8
        assert config.band_min_ratio == 0.3
        assert config.band_profit_target == 0.15
        assert config.band_stop_loss_fixed == 0.05
        
    def test_risk_params(self):
        """测试风控参数"""
        from src.config import Config
        
        config = Config()
        
        assert config.risk_market_drop_limit == 0.05
        assert config.risk_sector_drop_limit == 0.06
        assert config.risk_t_continuous_loss_limit == 3
        assert config.risk_band_continuous_loss_limit == 2


class TestSignal:
    """信号定义测试"""
    
    def test_signal_creation(self):
        """测试信号创建"""
        from src.strategy.signal import TradingSignal, SignalType, Direction
        
        signal = TradingSignal(
            signal_type=SignalType.T_LONG_BUY.value,
            direction=Direction.BUY.value,
            stock_code="300124",
            quantity=500,
            price=25.50,
            reason="测试信号",
            is_open_position=True
        )
        
        assert signal.signal_type == "T_LONG_BUY"
        assert signal.direction == "BUY"
        assert signal.stock_code == "300124"
        assert signal.quantity == 500
        assert signal.price == 25.50
        assert signal.is_open_position == True
        
    def test_signal_string(self):
        """测试信号字符串表示"""
        from src.strategy.signal import TradingSignal, SignalType, Direction
        
        signal = TradingSignal(
            signal_type=SignalType.T_LONG_BUY.value,
            direction=Direction.BUY.value,
            stock_code="300124",
            quantity=500,
            price=25.50,
            reason="测试信号"
        )
        
        signal_str = str(signal)
        assert "T_LONG_BUY" in signal_str
        assert "300124" in signal_str
        assert "500" in signal_str


class TestMarketModule:
    """行情模块测试"""
    
    def setup_method(self):
        """测试前准备"""
        from src.config import Config
        
        self.config = Config()
        self.market = MarketModule(self.config)
        
    def test_market_init(self):
        """测试行情模块初始化"""
        assert self.market is not None
        assert self.market.config == self.config
        
    def test_mock_quote(self):
        """测试模拟行情"""
        self.market.set_mock_quote("300124", 25.50, -0.02)
        
        quote = self.market.get_quote("300124")
        
        assert quote is not None
        assert quote.stock_code == "300124"
        assert quote.last_price == 25.50
        assert quote.change_pct == -0.02
        
    def test_mock_minute_data(self):
        """测试模拟分时数据"""
        prices = [25.0, 25.1, 25.2, 25.15, 25.1]
        self.market.set_mock_minute_data("300124", prices)
        
        # VWAP计算
        vwap = self.market.get_vwap("300124")
        
        assert vwap is not None
        assert vwap.vwap > 0


class TestTStrategy:
    """做T策略测试"""
    
    def setup_method(self):
        """测试前准备"""
        from src.config import Config
        from src.market_data import MarketModule
        from src.state.state_manager import StateManager
        
        self.config = Config()
        self.market = MarketModule(self.config)
        self.state_manager = StateManager(self.config)
        self.t_strategy = TStrategy(self.config, self.market, self.state_manager)
        
    def test_strategy_init(self):
        """测试策略初始化"""
        assert self.t_strategy is not None
        assert self.t_strategy.config == self.config
        
    def test_long_t_open_condition_prd(self):
        """
        测试做多T开仓条件（PRD规则验证）
        
        PRD规则：
        - 条件1: 当前价格 ≤ 分时均线 - 0.3%
        - 条件2: 股价跌幅 ≥ 2%
        """
        # 设置满足条件的行情：跌幅2.5% > 2%
        self.market.set_mock_quote("300124", 24.50, -0.025)
        
        # 设置分时均线（当前价格24.50 < 均线24.70 - 0.3%）
        prices = [25.0] * 30
        prices[-1] = 24.50  # 当前价格低于均线
        self.market.set_mock_minute_data("300124", prices)
        
        # 设置波段持仓（做空T需要，但做多T不需要）
        self.state_manager._band_position.has_position = True
        self.state_manager._band_position.quantity = 3000
        
        # 检查信号
        quote = self.market.get_quote("300124")
        signal = self.t_strategy._check_long_t_open(quote, self.state_manager.get_t_position())
        
        # 满足条件，应该返回信号
        assert signal is not None, "满足做多T开仓条件时应返回信号"
        assert signal.signal_type == "T_LONG_BUY", "信号类型应为T_LONG_BUY"
        
    def test_long_t_open_not_triggered_by_insufficient_drop(self):
        """测试跌幅不足2%时不触发做多T开仓"""
        # 设置跌幅不足的行情：跌幅1.5% < 2%
        self.market.set_mock_quote("300124", 24.75, -0.015)
        
        # 设置分时均线
        prices = [25.0] * 30
        prices[-1] = 24.75
        self.market.set_mock_minute_data("300124", prices)
        
        self.state_manager._band_position.has_position = True
        self.state_manager._band_position.quantity = 3000
        
        quote = self.market.get_quote("300124")
        signal = self.t_strategy._check_long_t_open(quote, self.state_manager.get_t_position())
        
        # 不满足跌幅条件，不应返回信号
        assert signal is None, "跌幅不足2%时不应触发做多T开仓"
        
    def test_long_t_open_not_triggered_by_price_above_vwap(self):
        """测试价格高于均线时不触发做多T开仓"""
        # 设置满足跌幅但价格高于均线
        self.market.set_mock_quote("300124", 25.20, -0.025)
        
        # 设置分时均线（当前价格25.20 > 均线25.00）
        prices = [25.0] * 30
        prices[-1] = 25.20
        self.market.set_mock_minute_data("300124", prices)
        
        self.state_manager._band_position.has_position = True
        self.state_manager._band_position.quantity = 3000
        
        quote = self.market.get_quote("300124")
        signal = self.t_strategy._check_long_t_open(quote, self.state_manager.get_t_position())
        
        # 不满足价格条件，不应返回信号
        assert signal is None, "价格高于均线时不应触发做多T开仓"
        
    def test_long_t_close_profit(self):
        """测试做多T止盈平仓 PRD规则：≥买入价+0.5%"""
        # 设置做多T持仓
        t_position = self.state_manager.get_t_position()
        t_position.has_long_position = True
        t_position.long_buy_price = 25.00
        t_position.long_quantity = 500
        
        # 设置满足止盈条件的行情：25.20 - 25.00 = 0.20 = 0.8% > 0.5%
        self.market.set_mock_quote("300124", 25.20, 0.01)
        
        # 检查信号
        quote = self.market.get_quote("300124")
        signal = self.t_strategy._check_long_t_close(quote, t_position)
        
        # 满足止盈条件
        assert signal is not None, "满足止盈条件时应触发平仓"
        assert signal.signal_type == "T_LONG_SELL"
        
    def test_long_t_stop_loss(self):
        """测试做多T止损平仓 PRD规则：≤买入价-1.0%"""
        # 设置做多T持仓
        t_position = self.state_manager.get_t_position()
        t_position.has_long_position = True
        t_position.long_buy_price = 25.50
        t_position.long_quantity = 500
        
        # 设置满足止损条件的行情：25.00 - 25.50 = -0.50 = -1.96% < -1.0%
        self.market.set_mock_quote("300124", 25.00, -0.02)
        
        # 检查信号
        quote = self.market.get_quote("300124")
        signal = self.t_strategy._check_long_t_close(quote, t_position)
        
        # 满足止损条件
        assert signal is not None, "满足止损条件时应触发平仓"
        assert signal.signal_type == "T_LONG_SELL"
        
    def test_quantity_calculation(self):
        """测试数量计算 1:1对冲"""
        # 设置账户和持仓
        self.state_manager._account.available = 50000
        self.state_manager._band_position.has_position = True
        self.state_manager._band_position.quantity = 3000
        
        # 计算做多T数量
        quantity = self.t_strategy._calculate_long_t_quantity(25.00)
        
        # 按资金: min(200000*10%, 20000)/25 = 800
        # 按底仓: 3000*30% = 900
        # 取最小并取整: 800
        assert quantity == 800, f"做多T数量计算错误，预期800，实际{quantity}"


class TestBandStrategy:
    """波段策略测试"""
    
    def setup_method(self):
        """测试前准备"""
        from src.config import Config
        from src.market_data import MarketModule
        from src.state.state_manager import StateManager
        
        self.config = Config()
        self.market = MarketModule(self.config)
        self.state_manager = StateManager(self.config)
        self.band_strategy = BandStrategy(self.config, self.market, self.state_manager)
        
    def test_strategy_init(self):
        """测试策略初始化"""
        assert self.band_strategy is not None
        
    def test_entry_signal(self):
        """测试建仓信号 PRD规则：初始建仓60%"""
        # 无持仓，应该检查建仓
        position = self.state_manager.get_band_position()
        assert position.has_position == False
        
        # 设置行情
        self.market.set_mock_quote("300124", 25.00, 0.01)
        
        # 检查信号
        signal = self.band_strategy._check_entry_signals()
        
        # 应该有建仓信号
        assert signal is not None, "无持仓时应触发建仓信号"
        assert signal.signal_type == "BAND_BUY"
        
    def test_holding_days_calculation(self):
        """测试持仓天数计算"""
        entry_date = datetime.now().strftime("%Y%m%d")
        days = self.band_strategy.calculate_holding_days(entry_date)
        assert days == 0
        
        # 5天前
        from datetime import timedelta
        old_date = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")
        days = self.band_strategy.calculate_holding_days(old_date)
        assert days >= 5
        
    def test_band_stop_loss_fixed(self):
        """测试波段固定止损 PRD规则：-5%"""
        # 设置持仓
        position = self.state_manager.get_band_position()
        position.has_position = True
        position.quantity = 3000
        position.avg_cost = 25.00
        position.holding_days = 5
        
        # 设置满足止损条件：跌幅5.5% > 5%
        self.market.set_mock_quote("300124", 23.625, -0.055)
        
        # 检查信号
        quote = self.market.get_quote("300124")
        signal = self.band_strategy._check_stop_loss(
            (quote.last_price - position.avg_cost) / position.avg_cost,
            position,
            quote
        )
        
        assert signal is not None, "满足固定止损条件时应触发止损"
        assert signal.signal_type == "BAND_SELL"


class TestRiskEngine:
    """风控引擎测试"""
    
    def setup_method(self):
        """测试前准备"""
        from src.config import Config
        from src.market_data import MarketModule
        from src.state.state_manager import StateManager
        
        self.config = Config()
        self.market = MarketModule(self.config)
        self.state_manager = StateManager(self.config)
        self.risk_engine = RiskEngine(self.config, self.state_manager, self.market)
        
    def test_risk_init(self):
        """测试风控初始化"""
        assert self.risk_engine is not None
        assert self.risk_engine.t_circuit_broken == False
        assert self.risk_engine.band_circuit_broken == False
        
    def test_time_check(self):
        """测试时间检查"""
        from src.strategy.signal import TradingSignal, SignalType, Direction
        
        # 设置当前时间在交易时段内（需要mock）
        signal = TradingSignal(
            signal_type=SignalType.T_LONG_BUY.value,
            direction=Direction.BUY.value,
            stock_code="300124",
            quantity=500,
            price=25.00,
            reason="测试",
            is_open_position=True
        )

    def test_fund_check(self):
        """测试资金检查"""
        from src.strategy.signal import TradingSignal, SignalType, Direction
        
        # 设置充足资金
        self.state_manager._account.available = 50000
        
        signal = TradingSignal(
            signal_type=SignalType.T_LONG_BUY.value,
            direction=Direction.BUY.value,
            stock_code="300124",
            quantity=500,
            price=25.00,
            reason="测试",
            is_open_position=True
        )
        
        # 资金充足，应该通过
        result = self.risk_engine._check_fund_available(signal)
        assert result == True
        
    def test_position_check(self):
        """测试持仓检查"""
        from src.strategy.signal import TradingSignal, SignalType, Direction
        
        # 设置持仓
        self.state_manager._band_position.has_position = True
        self.state_manager._band_position.quantity = 3000
        
        signal = TradingSignal(
            signal_type=SignalType.T_SHORT_SELL.value,
            direction=Direction.SELL.value,
            stock_code="300124",
            quantity=500,
            price=25.00,
            reason="测试",
            is_open_position=True
        )
        
        # 持仓充足，应该通过
        result = self.risk_engine._check_position_available(signal)
        assert result == True
        
    def test_market_drop_limit(self):
        """测试大盘跌幅限制 PRD规则：≥5%禁止开仓"""
        # 模拟大盘跌幅4% - 小于5%阈值
        self.market._market_index = MagicMock()
        self.market._market_index.change_pct = -0.04
        
        from src.strategy.signal import TradingSignal, SignalType, Direction
        signal = TradingSignal(
            signal_type=SignalType.T_LONG_BUY.value,
            direction=Direction.BUY.value,
            stock_code="300124",
            quantity=500,
            price=25.00,
            reason="测试",
            is_open_position=True
        )
        
        result = self.risk_engine._check_market_environment()
        assert result == True, "大盘跌幅4%应允许交易"
        
    def test_market_drop_block(self):
        """测试大盘跌幅≥5%禁止开仓"""
        # 模拟大盘跌幅6% - 大于5%阈值
        self.market._market_index = MagicMock()
        self.market._market_index.change_pct = -0.06
        
        result = self.risk_engine._check_market_environment()
        assert result == False, "大盘跌幅6%应禁止交易"


class TestStateManager:
    """状态管理器测试"""
    
    def setup_method(self):
        """测试前准备"""
        from src.config import Config
        
        # 使用测试配置文件
        test_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "test_config.yml"
        )
        
        # 如果测试配置不存在，使用默认配置
        if not os.path.exists(test_config_path):
            self.config = Config()
        else:
            self.config = Config(test_config_path)
            
        self.state_manager = StateManager(self.config)
        
    def test_state_init(self):
        """测试状态初始化"""
        assert self.state_manager is not None
        
        # 检查初始状态
        t_pos = self.state_manager.get_t_position()
        assert t_pos.has_long_position == False
        assert t_pos.has_short_position == False
        
        band_pos = self.state_manager.get_band_position()
        assert band_pos.has_position == False
        
    def test_t_position_update(self):
        """测试做T仓位更新"""
        self.state_manager.update_long_t_position(
            buy_price=25.00,
            buy_time="10:30:00",
            quantity=500
        )
        
        t_pos = self.state_manager.get_t_position()
        assert t_pos.has_long_position == True
        assert t_pos.long_buy_price == 25.00
        assert t_pos.long_quantity == 500
        
    def test_band_position_update(self):
        """测试波段仓位更新"""
        self.state_manager.update_band_position(
            quantity=3000,
            avg_cost=24.50,
            direction="BUY"
        )
        
        band_pos = self.state_manager.get_band_position()
        assert band_pos.has_position == True
        assert band_pos.quantity == 3000
        assert band_pos.avg_cost == 24.50
        
    def test_account_update(self):
        """测试账户更新"""
        self.state_manager.update_account(
            available=180000,
            total=200000,
            market_value=20000
        )
        
        account = self.state_manager.get_account()
        assert account.available == 180000
        assert account.total == 200000
        
    def test_state_save(self):
        """测试状态保存"""
        # 设置一些状态
        self.state_manager.update_account(available=150000)
        
        # 保存
        self.state_manager.save_state()
        
        # 检查文件是否存在
        assert self.config.state_file.exists()


# ==================== 缺失的导入 ====================
# 为了让测试能够正确导入，添加必要的导入
from src.market_data import MarketModule
from src.strategy.t_strategy import TStrategy
from src.strategy.band_strategy import BandStrategy
from src.risk.risk_engine import RiskEngine
from src.state.state_manager import StateManager


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

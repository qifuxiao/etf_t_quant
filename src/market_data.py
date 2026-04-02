"""
行情模块
负责获取和处理实时行情数据，包括：
- 实时行情获取
- VWAP分时均线计算
- 波动率计算
- K线数据处理
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np

try:
    from .log.logger import Logger
except ImportError:
    from log.logger import Logger


@dataclass
class QuoteData:
    """行情数据"""
    stock_code: str = ""              # 股票代码
    last_price: float = 0.0          # 最新价
    open: float = 0.0                 # 开盘价
    high: float = 0.0                 # 最高价
    low: float = 0.0                  # 最低价
    volume: int = 0                   # 成交量
    amount: float = 0.0               # 成交额
    change: float = 0.0               # 涨跌额
    change_pct: float = 0.0           # 涨跌幅
    bid: List[float] = field(default_factory=list)    # 买价
    ask: List[float] = field(default_factory=list)    # 卖价
    update_time: str = ""             # 更新时间
    
    
@dataclass
class VWAPData:
    """VWAP分时均线数据"""
    stock_code: str = ""              # 股票代码
    current_price: float = 0.0       # 当前价格
    vwap: float = 0.0                 # 当日VWAP
    vwap_5min: float = 0.0            # 5分钟均线
    vwap_slope: float = 0.0           # 均线斜率
    is_flat: bool = False             # 是否走平
    amplitude_5min: float = 0.0       # 5分钟振幅
    update_time: str = ""             # 更新时间
    
    
@dataclass
class MinuteData:
    """分时数据"""
    time: str = ""                    # 时间 HH:MM:SS
    price: float = 0.0                # 价格
    volume: int = 0                   # 成交量
    amount: float = 0.0               # 成交额
    
    
@dataclass 
class MarketIndex:
    """市场指数（大盘）"""
    index_code: str = ""              # 指数代码
    close: float = 0.0                # 收盘价
    change_pct: float = 0.0           # 涨跌幅


class MarketModule:
    """行情模块"""
    
    def __init__(self, config, executor=None, executor_type: str = None):
        """
        初始化行情模块
        
        Args:
            config: 配置对象
            executor: 执行器对象 (QMTExecutor 或 GMExecutor)
            executor_type: 执行器类型 ('qmt' 或 'gm')，优先级高于 executor 参数
        """
        self.config = config
        self._executor = executor
        
        # 确定数据源类型
        if executor_type:
            self._data_source = executor_type
        elif executor:
            # 从 executor 类名推断
            if 'GM' in executor.__class__.__name__.upper():
                self._data_source = 'gm'
            else:
                self._data_source = 'qmt'
        else:
            # 默认使用配置中的数据源
            self._data_source = config.data_source if hasattr(config, 'data_source') else 'gm'
        
        # 初始化数据执行器
        if not self._executor and self._data_source == 'gm':
            from .executor.gm_executor import GMExecutor
            self._executor = GMExecutor(config)
            self._executor.setup()
        
        Logger.info(f"行情模块初始化完成 | 标的:{config.stock_code} | 数据源:{self._data_source}")
        
        # 行情缓存
        self._quote_cache: Dict[str, QuoteData] = {}
        self._vwap_cache: Dict[str, VWAPData] = {}
        self._minute_data_cache: Dict[str, List[MinuteData]] = {}
        self._kline_cache: Dict[str, List[dict]] = {}
        
        # 波动率计算
        self._amplitude_history: Dict[str, List[float]] = {}  # 振幅历史
        self._low_amplitude_start: Dict[str, datetime] = {}   # 低振幅开始时间
        
        # 市场指数
        self._market_index: Optional[MarketIndex] = None
        
        # 回调函数
        self._subscribers: List[callable] = []
        
        Logger.info(f"行情模块初始化完成 | 标的:{config.stock_code}")
        
    def subscribe(self, stock_code: str):
        """
        订阅行情
        
        Args:
            stock_code: 股票代码
        """
        if self._executor:
            self._executor.subscribe(stock_code)
            Logger.info(f"已订阅行情 | 标的:{stock_code}")
            
    def unsubscribe(self, stock_code: str):
        """
        取消订阅行情
        
        Args:
            stock_code: 股票代码
        """
        if self._executor:
            self._executor.unsubscribe(stock_code)
            Logger.info(f"已取消订阅行情 | 标的:{stock_code}")
            
    def add_subscriber(self, callback: callable):
        """添加行情回调订阅者"""
        self._subscribers.append(callback)
        
    def remove_subscriber(self, callback: callable):
        """移除行情回调订阅者"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            
    def _notify_subscribers(self, quote: QuoteData):
        """通知订阅者"""
        for callback in self._subscribers:
            try:
                callback(quote)
            except Exception as e:
                Logger.error(f"行情回调执行异常: {e}")
                
    # ==================== 行情获取 ====================
    
    def get_quote(self, stock_code: str) -> Optional[QuoteData]:
        """
        获取实时行情
        
        Args:
            stock_code: 股票代码
            
        Returns:
            行情数据
        """
        # 从数据执行器获取
        if self._executor:
            try:
                quote_dict = self._executor.get_quote(stock_code)
                if quote_dict:
                    quote = self._parse_quote(quote_dict)
                    self._quote_cache[stock_code] = quote
                    return quote
            except Exception as e:
                Logger.error(f"获取行情失败 | 标的:{stock_code} | 错误:{e}")
                
        # 返回缓存数据
        return self._quote_cache.get(stock_code)
        
    def _parse_quote(self, quote_dict: dict) -> QuoteData:
        """解析行情数据"""
        quote = QuoteData()
        quote.stock_code = quote_dict.get('stock_code', '')
        quote.last_price = float(quote_dict.get('last_price', 0))
        quote.open = float(quote_dict.get('open', 0))
        quote.high = float(quote_dict.get('high', 0))
        quote.low = float(quote_dict.get('low', 0))
        quote.volume = int(quote_dict.get('volume', 0))
        quote.amount = float(quote_dict.get('amount', 0))
        quote.change = float(quote_dict.get('change', 0))
        quote.change_pct = float(quote_dict.get('change_pct', 0))
        quote.bid = quote_dict.get('bid', [])
        quote.ask = quote_dict.get('ask', [])
        quote.update_time = quote_dict.get('update_time', '')
        
        return quote
        
    # ==================== VWAP计算 ====================
    
    def get_vwap(self, stock_code: str) -> Optional[VWAPData]:
        """
        获取VWAP分时均线数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            VWAP数据
        """
        # 先获取最新行情
        quote = self.get_quote(stock_code)
        if not quote:
            return None
            
        # 获取分时数据
        minute_data = self._get_or_update_minute_data(stock_code)
        if not minute_data:
            return None
            
        # 计算VWAP
        vwap_data = self._calculate_vwap(stock_code, quote, minute_data)
        
        # 检查均线走平
        vwap_data.is_flat = self._check_vwap_flat(stock_code, vwap_data)
        
        # 计算5分钟振幅
        vwap_data.amplitude_5min = self._calculate_5min_amplitude(stock_code)
        
        # 更新缓存
        self._vwap_cache[stock_code] = vwap_data
        
        return vwap_data
        
    def _get_or_update_minute_data(self, stock_code: str) -> List[MinuteData]:
        """获取或更新分时数据"""
        today = datetime.now().strftime("%Y%m%d")
        
        # 检查缓存
        cache_key = f"{stock_code}_{today}"
        if cache_key in self._minute_data_cache:
            return self._minute_data_cache[cache_key]
            
        # 从数据执行器获取分时数据
        if self._executor:
            try:
                minute_list = self._executor.get_minute_data(stock_code, today)
                if minute_list:
                    minute_data = [self._parse_minute_data(m) for m in minute_list]
                    self._minute_data_cache[cache_key] = minute_data
                    return minute_data
            except Exception as e:
                Logger.error(f"获取分时数据失败 | 标的:{stock_code} | 错误:{e}")
                
        return []
        
    def _parse_minute_data(self, minute_dict: dict) -> MinuteData:
        """解析分时数据"""
        return MinuteData(
            time=minute_dict.get('time', ''),
            price=float(minute_dict.get('price', 0)),
            volume=int(minute_dict.get('volume', 0)),
            amount=float(minute_dict.get('amount', 0))
        )
        
    def _calculate_vwap(self, stock_code: str, quote: QuoteData, 
                       minute_data: List[MinuteData]) -> VWAPData:
        """计算VWAP"""
        vwap_data = VWAPData()
        vwap_data.stock_code = stock_code
        vwap_data.current_price = quote.last_price
        vwap_data.update_time = quote.update_time
        
        if not minute_data:
            vwap_data.vwap = quote.last_price
            return vwap_data
            
        # 计算累计成交额/累计成交量
        total_amount = sum(m.amount for m in minute_data)
        total_volume = sum(m.volume for m in minute_data)
        
        if total_volume > 0:
            vwap_data.vwap = total_amount / total_volume
        else:
            vwap_data.vwap = quote.last_price
            
        # 计算5分钟均线（最近5个周期的均价）
        recent_5min = minute_data[-5:] if len(minute_data) >= 5 else minute_data
        recent_amount = sum(m.amount for m in recent_5min)
        recent_volume = sum(m.volume for m in recent_5min)
        
        if recent_volume > 0:
            vwap_data.vwap_5min = recent_amount / recent_volume
        else:
            vwap_data.vwap_5min = vwap_data.vwap
            
        # 计算均线斜率（简单线性回归斜率）
        if len(minute_data) >= 3:
            prices = np.array([m.price for m in minute_data[-3:]])
            x = np.arange(len(prices))
            slope = np.polyfit(x, prices, 1)[0]
            vwap_data.vwap_slope = slope / quote.last_price  # 归一化
        else:
            vwap_data.vwap_slope = 0
            
        return vwap_data
        
    def _check_vwap_flat(self, stock_code: str, vwap_data: VWAPData) -> bool:
        """
        检查分时均线是否走平
        
        PRD量化定义：ABS(当前均线斜率) < 0.001 且 连续3个5分钟周期均线变化率 < 0.1%
        
        边界情况处理：
        1. 数据不足时返回False（避免误判）
        2. 斜率检查使用配置的阈值
        3. 连续变化率必须全部满足条件
        """
        # 边界情况1：斜率为0或无有效数据
        if vwap_data.vwap_slope == 0 and abs(vwap_data.vwap_slope) >= self.config.t_vwap_flat_slope:
            return False
            
        # 检查斜率条件：ABS(当前均线斜率) < 0.001
        if abs(vwap_data.vwap_slope) >= self.config.t_vwap_flat_slope:
            return False
            
        # 边界情况2：数据不足时返回False
        minute_data = self._get_or_update_minute_data(stock_code)
        if len(minute_data) < 15:
            Logger.debug(f"VWAP走平判断数据不足: {len(minute_data)} < 15个周期")
            return False
            
        # 检查连续变化率条件：连续3个5分钟周期均线变化率 < 0.1%
        prices = [m.price for m in minute_data[-15:]]  # 最近15分钟
        
        # 边界情况3：价格数据异常（包含0或负值）
        if not prices or any(p <= 0 for p in prices):
            Logger.debug("VWAP走平判断: 价格数据异常")
            return False
            
        # 分成3组计算变化率（每组5分钟）
        group_size = 5
        groups = [prices[i*group_size:(i+1)*group_size] for i in range(3)]
        
        # 边界情况4：分组数据不完整
        if len(groups) < 3 or any(not g for g in groups):
            Logger.debug("VWAP走平判断: 分组数据不完整")
            return False
        
        # 计算每组的均价
        avg_prices = []
        for g in groups:
            if g:
                avg_prices.append(sum(g) / len(g))
        
        # 边界情况5：均价计算结果异常
        if len(avg_prices) < 3:
            Logger.debug("VWAP走平判断: 均价数据不足")
            return False
            
        # 计算连续3个周期的变化率
        change_rates = []
        for i in range(1, len(avg_prices)):
            if avg_prices[i-1] != 0:
                rate = abs(avg_prices[i] - avg_prices[i-1]) / avg_prices[i-1]
                change_rates.append(rate)
                
        # 边界情况6：无有效变化率数据
        if not change_rates:
            Logger.debug("VWAP走平判断: 无有效变化率数据")
            return False
            
        # 边界情况7：需要连续3个周期都满足变化率<0.1%的条件
        # PRD要求：连续3个5分钟周期均线变化率 < 0.1%
        for rate in change_rates:
            if rate >= self.config.t_vwap_flat_change_rate:
                Logger.debug(f"VWAP走平判断: 变化率{rate*100:.3f}% >= {self.config.t_vwap_flat_change_rate*100}%")
                return False
                
        # 所有条件都满足，返回True
        Logger.debug(
            f"VWAP走平判断通过 | 斜率:{vwap_data.vwap_slope:.6f} | "
            f"变化率:{[f'{r*100:.3f}%' for r in change_rates]}"
        )
        return True
        
    def _calculate_5min_amplitude(self, stock_code: str) -> float:
        """计算5分钟振幅"""
        minute_data = self._get_or_update_minute_data(stock_code)
        
        if len(minute_data) < 5:
            return 0.0
            
        # 最近5分钟
        recent = minute_data[-5:]
        high = max(m.price for m in recent)
        low = min(m.price for m in recent)
        
        if low == 0:
            return 0.0
            
        return (high - low) / low
        
    # ==================== 波动率计算 ====================
    
    def check_low_amplitude(self, stock_code: str) -> bool:
        """
        检查是否低振幅持续（用于风控）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            是否低振幅持续
        """
        amplitude = self._calculate_5min_amplitude(stock_code)
        
        if amplitude < self.config.t_amplitude_limit:
            # 记录低振幅开始时间
            if stock_code not in self._low_amplitude_start:
                self._low_amplitude_start[stock_code] = datetime.now()
                
            # 检查持续时间
            start_time = self._low_amplitude_start.get(stock_code)
            if start_time:
                duration = (datetime.now() - start_time).total_seconds() / 60
                if duration >= self.config.t_amplitude_duration:
                    return True
        else:
            # 恢复振幅，清除记录
            if stock_code in self._low_amplitude_start:
                del self._low_amplitude_start[stock_code]
                
        return False
        
    def calculate_volatility_20d(self, stock_code: str) -> float:
        """
        计算20日历史波动率
        
        Args:
            stock_code: 股票代码
            
        Returns:
            波动率
        """
        # 获取K线数据计算波动率
        kline_data = self.get_kline(stock_code, days=20)
        if not kline_data or len(kline_data) < 20:
            return 0.0
            
        # 计算日收益率标准差作为波动率
        returns = []
        for i in range(1, len(kline_data)):
            prev_close = kline_data[i-1].get('close', 0)
            curr_close = kline_data[i].get('close', 0)
            if prev_close > 0:
                ret = (curr_close - prev_close) / prev_close
                returns.append(ret)
                
        if not returns:
            return 0.0
            
        # 计算标准差
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5
        
        return volatility
    
    def get_kline(self, stock_code: str, days: int = 30) -> List[dict]:
        """
        获取K线数据
        
        Args:
            stock_code: 股票代码
            days: 获取天数
            
        Returns:
            K线数据列表，每条包含 date, open, high, low, close, volume
        """
        # 缓存Key
        cache_key = f"{stock_code}_kline_{days}"
        
        # 从数据执行器获取
        if self._executor:
            try:
                # 计算日期范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days + 10)
                
                kline_list = self._executor.get_kline(
                    stock_code, 
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d")
                )
                
                if kline_list:
                    # 解析K线数据
                    kline_data = []
                    for k in kline_list:
                        kline_data.append({
                            'date': k.get('date', ''),
                            'open': float(k.get('open', 0)),
                            'high': float(k.get('high', 0)),
                            'low': float(k.get('low', 0)),
                            'close': float(k.get('close', 0)),
                            'volume': int(k.get('volume', 0)),
                            'amount': float(k.get('amount', 0))
                        })
                    
                    # 缓存结果
                    self._kline_cache[cache_key] = kline_data
                    return kline_data[-days:]  # 返回最近days天的数据
                    
            except Exception as e:
                Logger.error(f"获取K线数据失败 | 标的:{stock_code} | 错误:{e}")
        
        # 返回缓存数据
        cached = self._kline_cache.get(cache_key, [])
        if cached:
            return cached[-days:]
            
        return []
        
    # K线数据缓存
    _kline_cache: Dict[str, List[dict]] = {}
        
    # ==================== 市场指数 ====================
    
    def get_market_index(self, index_code: str = "000300") -> Optional[MarketIndex]:
        """
        获取市场指数
        
        Args:
            index_code: 指数代码，默认沪深300
            
        Returns:
            市场指数数据
        """
        if self._executor:
            try:
                index_dict = self._executor.get_quote(index_code)
                if index_dict:
                    self._market_index = MarketIndex(
                        index_code=index_code,
                        close=float(index_dict.get('close', 0)),
                        change_pct=float(index_dict.get('change_pct', 0))
                    )
                    return self._market_index
            except Exception as e:
                Logger.error(f"获取市场指数失败 | 错误:{e}")
                
        return self._market_index
        
    def get_market_drop(self) -> float:
        """
        获取大盘跌幅
        
        Returns:
            大盘跌幅（正数表示下跌）
        """
        index = self.get_market_index()
        if index:
            return max(0, -index.change_pct)
        return 0.0
        
    # ==================== 模拟数据（用于测试） ====================
    
    def set_mock_quote(self, stock_code: str, price: float, change_pct: float):
        """设置模拟行情（用于测试）"""
        quote = QuoteData()
        quote.stock_code = stock_code
        quote.last_price = price
        quote.open = price * 0.98
        quote.high = price * 1.01
        quote.low = price * 0.97
        quote.volume = 1000000
        quote.amount = price * 1000000
        quote.change = price * change_pct
        quote.change_pct = change_pct
        quote.update_time = datetime.now().strftime("%H:%M:%S")
        
        self._quote_cache[stock_code] = quote
        
    def set_mock_minute_data(self, stock_code: str, prices: List[float]):
        """设置模拟分时数据（用于测试）"""
        minute_data = []
        base_time = datetime.now().replace(hour=9, minute=30, second=0)
        
        for i, price in enumerate(prices):
            minute = MinuteData()
            minute.time = (base_time + timedelta(minutes=i)).strftime("%H:%M:%S")
            minute.price = price
            minute.volume = 10000
            minute.amount = price * 10000
            minute_data.append(minute)
            
        today = datetime.now().strftime("%Y%m%d")
        cache_key = f"{stock_code}_{today}"
        self._minute_data_cache[cache_key] = minute_data

"""
GM 执行器模块
负责与 GM (掘金) API 交互获取行情数据

注意：GM API 仅用于数据获取，交易下单仍使用 QMT
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

try:
    from gm.api import set_serv_addr, set_token, current, history
    _GM_AVAILABLE = True
except ImportError as e:
    _GM_AVAILABLE = False
    print(f"⚠️ gm.api 导入失败: {e}")

try:
    from ..log.logger import Logger
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from log.logger import Logger


def format_gm_symbol(stock_code: str) -> str:
    """
    将股票代码转换为 GM 需要的格式
    
    Args:
        stock_code: 股票代码，支持以下格式：
            - "300124" -> "SZSE.300124"
            - "600000" -> "SHSE.600000" 
            - "300124.SZ" -> "SZSE.300124"
            - "600000.SH" -> "SHSE.600000"
    
    Returns:
        格式化后的股票代码，如 "SZSE.300124"
    """
    if not stock_code:
        return stock_code
    
    # 移除已有的市场后缀
    if '.' in stock_code:
        code, market = stock_code.split('.')
    else:
        code = stock_code
        market = None
    
    # 根据股票代码前缀判断市场
    # 6开头：上海证券交易所 (SHSE)
    # 0/3/8/4开头：深圳证券交易所 (SZSE)
    if market:
        if market == 'SH':
            return f"SHSE.{code}"
        elif market == 'SZ':
            return f"SZSE.{code}"
    
    # 无后缀时根据代码前缀判断
    if code.startswith('6'):
        return f"SHSE.{code}"
    else:
        return f"SZSE.{code}"


@dataclass
class GMQuoteData:
    """GM 行情数据"""
    symbol: str = ""           # 股票代码 (GM格式)
    stock_code: str = ""       # 股票代码 (原始格式)
    price: float = 0.0         # 最新价
    open: float = 0.0          # 开盘价
    high: float = 0.0          # 最高价
    low: float = 0.0           # 最低价
    volume: int = 0            # 成交量
    amount: float = 0.0        # 成交额
    change: float = 0.0        # 涨跌额
    change_pct: float = 0.0    # 涨跌幅
    bid: List[float] = None     # 买价
    ask: List[float] = None     # 卖价
    update_time: str = ""      # 更新时间
    
    def __post_init__(self):
        if self.bid is None:
            self.bid = []
        if self.ask is None:
            self.ask = []


class GMExecutor:
    """GM 数据获取执行器"""
    
    def __init__(self, config=None):
        """
        初始化 GM 执行器
        
        Args:
            config: 配置对象，需要包含 gm_token 和 gm_server
        """
        self.config = config
        self._connected = False
        
        # GM 配置
        self._gm_token = None
        self._gm_server = None
        
        # 解析配置
        if config:
            if hasattr(config, 'gm_token'):
                self._gm_token = config.gm_token
            if hasattr(config, 'gm_server'):
                self._gm_server = config.gm_server
        
        # 缓存
        self._quote_cache: Dict[str, GMQuoteData] = {}
        
        Logger.info("GM 执行器初始化完成")
    
    def setup(self) -> bool:
        """
        设置并连接 GM API
        
        Returns:
            是否连接成功
        """
        if not _GM_AVAILABLE:
            Logger.error("❌ gm.api 不可用，无法连接 GM")
            return False
        
        try:
            # 配置服务器
            if self._gm_server:
                set_serv_addr(addr=self._gm_server)
                Logger.info(f"✅ GM 服务器配置: {self._gm_server}")
            
            # 设置 token
            if self._gm_token:
                set_token(self._gm_token)
                Logger.info("✅ GM Token 设置成功")
            
            self._connected = True
            return True
            
        except Exception as e:
            Logger.error(f"❌ GM API 设置失败: {e}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    def connect(self) -> bool:
        """连接 GM API (兼容接口)"""
        return self.setup()
    
    def disconnect(self):
        """断开 GM 连接"""
        self._connected = False
        Logger.info("🛑 GM 已断开")
    
    def get_quote(self, stock_code: str) -> Optional[Dict]:
        """
        获取实时行情
        
        Args:
            stock_code: 股票代码 (如 300124)
            
        Returns:
            行情字典，字段与 QMTExecutor 保持一致
        """
        if not self._connected:
            # 尝试重新连接
            if not self.setup():
                Logger.warning("GM 未连接，无法获取行情")
                return None
        
        try:
            # 转换为 GM 格式
            gm_symbol = format_gm_symbol(stock_code)
            
            # 获取实时行情
            data = current(symbols=[gm_symbol])
            
            if not data or len(data) == 0:
                Logger.warning(f"GM 无行情数据 | 标的:{stock_code} | gm_symbol:{gm_symbol}")
                return None
            
            # 解析数据
            quote_data = data[0]
            
            # 提取买卖五档
            bid_list = []
            ask_list = []
            quotes = quote_data.get('quotes', [])
            for quote in quotes[:5]:  # 取前5档
                bid_list.append(quote.get('bid_p', 0))
                ask_list.append(quote.get('ask_p', 0))
            
            # 计算涨跌
            open_price = quote_data.get('open', 0)
            price = quote_data.get('price', 0)
            change = price - open_price if open_price else 0
            change_pct = (change / open_price * 100) if open_price else 0
            
            result = {
                'stock_code': stock_code,
                'last_price': self._safe_float(quote_data.get('price')),
                'open': self._safe_float(quote_data.get('open')),
                'high': self._safe_float(quote_data.get('high')),
                'low': self._safe_float(quote_data.get('low')),
                'volume': self._safe_int(quote_data.get('cum_volume')),
                'amount': self._safe_float(quote_data.get('cum_amount')),
                'change': change,
                'change_pct': change_pct,
                'bid': bid_list,
                'ask': ask_list,
                'update_time': quote_data.get('created_at', '')
            }
            
            # 缓存
            self._quote_cache[stock_code] = self._parse_to_quote_data(result)
            
            return result
            
        except Exception as e:
            Logger.error(f"获取 GM 行情失败 | 标的:{stock_code} | 错误:{e}")
            import traceback
            Logger.error(traceback.format_exc())
            
        return None
    
    def get_minute_data(self, stock_code: str, date: str) -> List[Dict]:
        """
        获取分时数据
        
        Args:
            stock_code: 股票代码
            date: 日期，格式 YYYYMMDD
            
        Returns:
            分时数据列表
        """
        if not self._connected:
            if not self.setup():
                Logger.warning("GM 未连接，无法获取分时数据")
                return []
        
        try:
            # 转换为 GM 格式
            gm_symbol = format_gm_symbol(stock_code)
            
            # 转换日期格式
            if len(date) == 8:
                start_time = date + "093000"
                end_time = date + "150000"
            else:
                start_time = date
                end_time = date
            
            # 获取分时数据 (GM API: history)
            # fields: time, open, high, low, close, volume
            data = history(
                symbol=gm_symbol,
                start_time=start_time,
                end_time=end_time,
                fields="time,open,high,low,close,volume,amount",
                adjust="qfq"  # 前复权
            )
            
            if data is None or len(data) == 0:
                Logger.warning(f"GM 无分时数据 | 标的:{stock_code} | 日期:{date}")
                return []
            
            # 解析数据
            minute_list = []
            for item in data:
                time_str = self._format_time(item.get('time'))
                minute_list.append({
                    'time': time_str,
                    'open': self._safe_float(item.get('open')),
                    'high': self._safe_float(item.get('high')),
                    'low': self._safe_float(item.get('low')),
                    'close': self._safe_float(item.get('close')),
                    'price': self._safe_float(item.get('close')),
                    'volume': self._safe_int(item.get('volume')),
                    'amount': self._safe_float(item.get('amount'))
                })
            
            Logger.info(f"GM 分时数据获取成功 | 标的:{stock_code} | 条数:{len(minute_list)}")
            return minute_list
            
        except Exception as e:
            Logger.error(f"获取 GM 分时数据失败 | 标的:{stock_code} | 错误:{e}")
            import traceback
            Logger.error(traceback.format_exc())
            
        return []
    
    def get_kline(self, stock_code: str, start_date: str, end_date: str) -> List[Dict]:
        """
        获取K线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
            
        Returns:
            K线数据列表
        """
        if not self._connected:
            if not self.setup():
                Logger.warning("GM 未连接，无法获取K线数据")
                return []
        
        try:
            # 转换为 GM 格式
            gm_symbol = format_gm_symbol(stock_code)
            
            # 转换日期格式
            start_time = start_date + "090000"
            end_time = end_date + "150000"
            
            # 获取日K线数据
            data = history(
                symbol=gm_symbol,
                start_time=start_time,
                end_time=end_time,
                fields="time,open,high,low,close,volume,amount",
                adjust="qfq"
            )
            
            if data is None or len(data) == 0:
                Logger.warning(f"GM 无K线数据 | 标的:{stock_code} | {start_date}~{end_date}")
                return []
            
            # 解析数据
            kline_list = []
            for item in data:
                date_str = self._format_date(item.get('time'))
                kline_list.append({
                    'date': date_str,
                    'open': self._safe_float(item.get('open')),
                    'high': self._safe_float(item.get('high')),
                    'low': self._safe_float(item.get('low')),
                    'close': self._safe_float(item.get('close')),
                    'volume': self._safe_int(item.get('volume')),
                    'amount': self._safe_float(item.get('amount'))
                })
            
            Logger.info(f"GM K线数据获取成功 | 标的:{stock_code} | 条数:{len(kline_list)}")
            return kline_list
            
        except Exception as e:
            Logger.error(f"获取 GM K线数据失败 | 标的:{stock_code} | 错误:{e}")
            
        return []
    
    def subscribe(self, stock_code: str):
        """
        订阅行情 (GM API 不需要主动订阅，current() 会自动获取最新数据)
        """
        Logger.debug(f"GM 订阅行情请求 | 标的:{stock_code} (GM API 自动推送)")
    
    def unsubscribe(self, stock_code: str):
        """取消订阅行情"""
        Logger.debug(f"GM 取消订阅行情 | 标的:{stock_code}")
    
    # ==================== 辅助方法 ====================
    
    def _parse_to_quote_data(self, quote_dict: dict) -> GMQuoteData:
        """解析为 GMQuoteData"""
        return GMQuoteData(
            symbol=quote_dict.get('stock_code', ''),
            stock_code=quote_dict.get('stock_code', ''),
            price=quote_dict.get('last_price', 0),
            open=quote_dict.get('open', 0),
            high=quote_dict.get('high', 0),
            low=quote_dict.get('low', 0),
            volume=quote_dict.get('volume', 0),
            amount=quote_dict.get('amount', 0),
            change=quote_dict.get('change', 0),
            change_pct=quote_dict.get('change_pct', 0),
            bid=quote_dict.get('bid', []),
            ask=quote_dict.get('ask', []),
            update_time=quote_dict.get('update_time', '')
        )
    
    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """安全转换为 float"""
        try:
            if value in (None, ""):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        """安全转换为 int"""
        try:
            if value in (None, ""):
                return default
            return int(value)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def _format_time(value: Any) -> str:
        """格式化时间为 HH:MM:SS"""
        try:
            if isinstance(value, (int, float)):
                # 毫秒时间戳
                ts = value / 1000 if value > 10_000_000_000 else value
                dt = datetime.fromtimestamp(ts)
                return dt.strftime("%H:%M:%S")
            return str(value)
        except Exception:
            return str(value)
    
    @staticmethod
    def _format_date(value: Any) -> str:
        """格式化日期为 YYYYMMDD"""
        try:
            if isinstance(value, (int, float)):
                ts = value / 1000 if value > 10_000_000_000 else value
                dt = datetime.fromtimestamp(ts)
                return dt.strftime("%Y%m%d")
            return str(value)[:8]
        except Exception:
            return str(value)
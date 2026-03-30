"""
交易信号定义
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SignalType(Enum):
    """信号类型枚举"""
    # 做T信号
    T_LONG_BUY = "T_LONG_BUY"     # 做多T买入
    T_LONG_SELL = "T_LONG_SELL"   # 做多T卖出
    T_SHORT_SELL = "T_SHORT_SELL" # 做空T卖出
    T_SHORT_BUY = "T_SHORT_BUY"   # 做空T买回
    
    # 波段信号
    BAND_BUY = "BAND_BUY"         # 波段买入
    BAND_SELL = "BAND_SELL"       # 波段卖出
    
    
class Direction(Enum):
    """交易方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"           # 待提交
    SUBMITTED = "submitted"       # 已提交
    PARTIAL = "partial"           # 部分成交
    FILLED = "filled"             # 全部成交
    CANCELLED = "cancelled"       # 已撤单
    REJECTED = "rejected"         # 已拒绝
    FAILED = "failed"             # 失败


@dataclass
class TradingSignal:
    """交易信号"""
    signal_type: str              # 信号类型
    direction: str                # 交易方向 BUY/SELL
    stock_code: str               # 股票代码
    quantity: int                # 委托数量
    price: float                 # 委托价格
    reason: str                  # 触发原因
    is_open_position: bool = True  # 是否开仓（平仓=false）
    
    def __str__(self):
        return (
            f"Signal({self.signal_type} | {self.direction} | "
            f"{self.stock_code} | {self.quantity}@{self.price:.2f} | {self.reason})"
        )


@dataclass
class Order:
    """订单"""
    order_id: str = ""            # 订单ID
    stock_code: str = ""          # 股票代码
    direction: str = ""           # 交易方向
    price: float = 0.0            # 委托价格
    quantity: int = 0            # 委托数量
    filled_quantity: int = 0     # 已成交数量
    status: str = "pending"       # 订单状态
    order_type: str = "LIMIT"     # 订单类型
    submit_time: str = ""         # 提交时间
    update_time: str = ""         # 更新时间
    error_message: str = ""       # 错误信息
    signal_type: str = ""         # 对应信号类型
    
    def __str__(self):
        return (
            f"Order({self.order_id} | {self.direction} | "
            f"{self.stock_code} | {self.filled_quantity}/{self.quantity}@{self.price:.2f} | {self.status})"
        )


@dataclass
class PositionState:
    """持仓状态"""
    has_position: bool = False    # 是否有持仓
    quantity: int = 0             # 持仓数量
    avg_cost: float = 0.0         # 平均成本
    position_ratio: float = 0.0   # 持仓比例
    
    
@dataclass
class TPositionState:
    """做T仓位状态"""
    # 做多T仓位
    has_long_position: bool = False
    long_buy_price: float = 0.0
    long_buy_time: str = ""
    long_quantity: int = 0
    long_order_id: str = ""
    
    # 做空T仓位
    has_short_position: bool = False
    short_sell_price: float = 0.0
    short_sell_time: str = ""
    short_quantity: int = 0
    short_order_id: str = ""
    
    # 统计信息
    total_t_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    continuous_loss: int = 0
    total_profit: float = 0.0
    last_t_date: str = ""


@dataclass
class AccountInfo:
    """账户信息"""
    available: float = 0.0       # 可用资金
    total: float = 0.0           # 总资产
    market_value: float = 0.0    # 市值
    frozen: float = 0.0          # 冻结资金

"""
状态管理模块
负责持仓状态、订单状态、资金状态的维护和持久化
"""

import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

from src.strategy.signal import TPositionState, PositionState, AccountInfo
from src.log.logger import Logger


class StateManager:
    """状态管理器"""
    
    def __init__(self, config):
        """
        初始化状态管理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        
        # 创建状态目录
        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        
        # 运行时状态
        self._t_position = TPositionState()
        self._band_position = PositionState()
        self._account = AccountInfo()
        
        # 波段交易记录
        self._band_add_records: List[Dict] = []
        self._band_reduce_records: List[Dict] = []
        self._band_stats: Dict = {}
        
        # 订单记录
        self._orders: Dict[str, dict] = {}
        
        # 锁
        self._lock = threading.Lock()
        
        # 加载持久化状态
        self._load_state()
        
        Logger.info("状态管理器初始化完成")
        
    # ==================== 公共接口 ====================
    
    def load(self):
        """加载状态（公共接口）"""
        self._load_state()
        
    def get_state(self) -> Dict:
        """获取完整状态（公共接口）"""
        return {
            't_position': {
                'has_long_position': self._t_position.has_long_position,
                'long_buy_price': self._t_position.long_buy_price,
                'long_buy_time': self._t_position.long_buy_time,
                'long_quantity': self._t_position.long_quantity,
                'long_order_id': self._t_position.long_order_id,
                'has_short_position': self._t_position.has_short_position,
                'short_sell_price': self._t_position.short_sell_price,
                'short_sell_time': self._t_position.short_sell_time,
                'short_quantity': self._t_position.short_quantity,
                'short_order_id': self._t_position.short_order_id,
                'total_t_count': self._t_position.total_t_count,
                'success_count': self._t_position.success_count,
                'fail_count': self._t_position.fail_count,
                'continuous_loss': self._t_position.continuous_loss,
                'total_profit': self._t_position.total_profit,
                'last_t_date': self._t_position.last_t_date
            },
            'band_position': {
                'has_position': self._band_position.has_position,
                'quantity': self._band_position.quantity,
                'avg_cost': self._band_position.avg_cost,
                'position_ratio': self._band_position.position_ratio,
                'entry_date': getattr(self._band_position, 'entry_date', ''),
                'holding_days': getattr(self._band_position, 'holding_days', 0),
                'add_records': self._band_add_records,
                'reduce_records': self._band_reduce_records,
                'stats': self._band_stats
            },
            'trade_history': self._band_add_records + self._band_reduce_records,
            'orders': self._orders
        }
        
    # ==================== 加载/保存 ====================
    
    def _load_state(self):
        """从文件加载状态"""
        if not self.config.state_file.exists():
            Logger.info("状态文件不存在，使用默认状态")
            return
            
        try:
            with open(self.config.state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
                
            # 加载做T仓位
            t_position_data = state_data.get('t_position', {})
            self._t_position.has_long_position = t_position_data.get('has_long_position', False)
            self._t_position.long_buy_price = t_position_data.get('long_buy_price', 0.0)
            self._t_position.long_buy_time = t_position_data.get('long_buy_time', '')
            self._t_position.long_quantity = t_position_data.get('long_quantity', 0)
            self._t_position.long_order_id = t_position_data.get('long_order_id', '')
            
            self._t_position.has_short_position = t_position_data.get('has_short_position', False)
            self._t_position.short_sell_price = t_position_data.get('short_sell_price', 0.0)
            self._t_position.short_sell_time = t_position_data.get('short_sell_time', '')
            self._t_position.short_quantity = t_position_data.get('short_quantity', 0)
            self._t_position.short_order_id = t_position_data.get('short_order_id', '')
            
            self._t_position.total_t_count = t_position_data.get('total_t_count', 0)
            self._t_position.success_count = t_position_data.get('success_count', 0)
            self._t_position.fail_count = t_position_data.get('fail_count', 0)
            self._t_position.continuous_loss = t_position_data.get('continuous_loss', 0)
            self._t_position.total_profit = t_position_data.get('total_profit', 0.0)
            self._t_position.last_t_date = t_position_data.get('last_t_date', '')
            
            # 加载波段仓位
            band_position_data = state_data.get('band_position', {})
            self._band_position.has_position = band_position_data.get('has_position', False)
            self._band_position.quantity = band_position_data.get('quantity', 0)
            self._band_position.avg_cost = band_position_data.get('avg_cost', 0.0)
            self._band_position.position_ratio = band_position_data.get('position_ratio', 0.0)
            
            # 加载波段记录
            self._band_add_records = band_position_data.get('add_records', [])
            self._band_reduce_records = band_position_data.get('reduce_records', [])
            self._band_stats = band_position_data.get('stats', {})
            
            # 加载订单
            self._orders = state_data.get('orders', {})
            
            Logger.info(f"状态加载完成 | 做T次数:{self._t_position.total_t_count} | 波段持仓:{self._band_position.quantity}")
            
        except Exception as e:
            Logger.error(f"加载状态失败: {e}")
            
    def save_state(self):
        """保存状态到文件"""
        with self._lock:
            state_data = {
                't_position': {
                    'has_long_position': self._t_position.has_long_position,
                    'long_buy_price': self._t_position.long_buy_price,
                    'long_buy_time': self._t_position.long_buy_time,
                    'long_quantity': self._t_position.long_quantity,
                    'long_order_id': self._t_position.long_order_id,
                    'has_short_position': self._t_position.has_short_position,
                    'short_sell_price': self._t_position.short_sell_price,
                    'short_sell_time': self._t_position.short_sell_time,
                    'short_quantity': self._t_position.short_quantity,
                    'short_order_id': self._t_position.short_order_id,
                    'total_t_count': self._t_position.total_t_count,
                    'success_count': self._t_position.success_count,
                    'fail_count': self._t_position.fail_count,
                    'continuous_loss': self._t_position.continuous_loss,
                    'total_profit': self._t_position.total_profit,
                    'last_t_date': self._t_position.last_t_date
                },
                'band_position': {
                    'has_position': self._band_position.has_position,
                    'quantity': self._band_position.quantity,
                    'avg_cost': self._band_position.avg_cost,
                    'position_ratio': self._band_position.position_ratio,
                    'entry_date': getattr(self._band_position, 'entry_date', ''),
                    'holding_days': getattr(self._band_position, 'holding_days', 0),
                    'add_records': self._band_add_records,
                    'reduce_records': self._band_reduce_records,
                    'stats': self._band_stats
                },
                'orders': self._orders,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            try:
                with open(self.config.state_file, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, ensure_ascii=False, indent=2)
                    
                Logger.debug("状态已保存")
                
            except Exception as e:
                Logger.error(f"保存状态失败: {e}")
                
    # ==================== 做T仓位 ====================
    
    def get_t_position(self) -> TPositionState:
        """获取做T仓位"""
        return self._t_position
        
    def update_long_t_position(self, buy_price: float, buy_time: str, 
                                quantity: int, order_id: str = ""):
        """更新做多T仓位"""
        with self._lock:
            self._t_position.has_long_position = True
            self._t_position.long_buy_price = buy_price
            self._t_position.long_buy_time = buy_time
            self._t_position.long_quantity = quantity
            self._t_position.long_order_id = order_id
            
        Logger.log_position("做多T", quantity, buy_price)
        
    def close_long_t_position(self):
        """平仓做多T"""
        with self._lock:
            self._t_position.has_long_position = False
            self._t_position.long_quantity = 0
            
    def update_short_t_position(self, sell_price: float, sell_time: str,
                                 quantity: int, order_id: str = ""):
        """更新做空T仓位"""
        with self._lock:
            self._t_position.has_short_position = True
            self._t_position.short_sell_price = sell_price
            self._t_position.short_sell_time = sell_time
            self._t_position.short_quantity = quantity
            self._t_position.short_order_id = order_id
            
        Logger.log_position("做空T", quantity, sell_price)
        
    def close_short_t_position(self):
        """平仓做空T"""
        with self._lock:
            self._t_position.has_short_position = False
            self._t_position.short_quantity = 0
            
    # ==================== 波段仓位 ====================
    
    def get_band_position(self) -> PositionState:
        """获取波段仓位"""
        return self._band_position
        
    def update_band_position(self, quantity: int, avg_cost: float, 
                              direction: str = "BUY"):
        """
        更新波段仓位
        
        Args:
            quantity: 成交数量
            avg_cost: 成交价格
            direction: 方向 BUY/SELL
        """
        with self._lock:
            if direction == "BUY":
                # 买入，增加持仓
                if self._band_position.has_position:
                    # 计算新的平均成本
                    total_cost = self._band_position.avg_cost * self._band_position.quantity
                    total_cost += avg_cost * quantity
                    new_quantity = self._band_position.quantity + quantity
                    self._band_position.avg_cost = total_cost / new_quantity if new_quantity > 0 else 0
                    self._band_position.quantity = new_quantity
                else:
                    # 新建持仓
                    self._band_position.has_position = True
                    self._band_position.avg_cost = avg_cost
                    self._band_position.quantity = quantity
                    self._band_position.position_ratio = (avg_cost * quantity) / self.config.total_capital
                    
            else:
                # 卖出，减少持仓
                self._band_position.quantity -= quantity
                
                if self._band_position.quantity <= 0:
                    # 清仓
                    self._band_position.has_position = False
                    self._band_position.quantity = 0
                    self._band_position.avg_cost = 0
                    self._band_position.position_ratio = 0
                else:
                    # 更新持仓比例
                    self._band_position.position_ratio = (
                        self._band_position.avg_cost * self._band_position.quantity
                    ) / self.config.total_capital
                    
        Logger.log_position(
            "波段",
            self._band_position.quantity,
            self._band_position.avg_cost
        )
        
    def add_band_record(self, record_type: str, price: float, quantity: int):
        """
        添加波段交易记录
        
        Args:
            record_type: 记录类型 ADD/REDUCE
            price: 价格
            quantity: 数量
        """
        record = {
            "date": datetime.now().strftime("%Y%m%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "price": price,
            "quantity": quantity
        }
        
        with self._lock:
            if record_type == "ADD":
                self._band_add_records.append(record)
            elif record_type == "REDUCE":
                # 计算收益率
                if self._band_position.has_position and self._band_position.avg_cost > 0:
                    record["profit_ratio"] = (price - self._band_position.avg_cost) / self._band_position.avg_cost
                self._band_reduce_records.append(record)
                
    def get_band_add_records(self) -> List[Dict]:
        """获取波段加仓记录"""
        return self._band_add_records
        
    def get_band_reduce_records(self) -> List[Dict]:
        """获取波段减仓记录"""
        return self._band_reduce_records
        
    def get_band_stats(self) -> Dict:
        """获取波段统计"""
        return self._band_stats
        
    # ==================== 账户 ====================
    
    def get_account(self) -> AccountInfo:
        """获取账户信息"""
        return self._account
        
    def update_account(self, available: float = None, total: float = None,
                       market_value: float = None, frozen: float = None):
        """更新账户信息"""
        with self._lock:
            if available is not None:
                self._account.available = available
            if total is not None:
                self._account.total = total
            if market_value is not None:
                self._account.market_value = market_value
            if frozen is not None:
                self._account.frozen = frozen
                
    def sync_account_from_qmt(self, qmt_executor):
        """从QMT同步账户信息"""
        account_data = qmt_executor.get_account()
        if account_data:
            self.update_account(
                available=account_data.get('available', 0),
                total=account_data.get('total', 0),
                market_value=account_data.get('market_value', 0),
                frozen=account_data.get('frozen', 0)
            )
            
    # ==================== 订单 ====================
    
    def add_order(self, order_id: str, order_data: dict):
        """添加订单"""
        with self._lock:
            self._orders[order_id] = order_data
            
    def update_order(self, order_id: str, status: str = None, 
                    filled_quantity: int = None):
        """更新订单"""
        with self._lock:
            if order_id in self._orders:
                if status:
                    self._orders[order_id]['status'] = status
                if filled_quantity is not None:
                    self._orders[order_id]['filled_quantity'] = filled_quantity
                    
    def get_order(self, order_id: str) -> Optional[dict]:
        """获取订单"""
        with self._lock:
            return self._orders.get(order_id)
            
    def get_pending_orders(self) -> List[dict]:
        """获取待处理订单"""
        with self._lock:
            return [
                order for order in self._orders.values()
                if order.get('status') in ['submitted', 'partial']
            ]
            
    # ==================== 日终处理 ====================
    
    def daily_settlement(self):
        """日终结算"""
        # 清理当日无效状态
        today = datetime.now().strftime("%Y%m%d")
        
        # 检查做T最后交易日期
        if self._t_position.last_t_date != today:
            # 新的一天，重置某些状态（如需要）
            pass
            
        # 更新持仓天数
        if self._band_position.has_position:
            entry_date = self._band_position.get('entry_date', '')
            if entry_date:
                try:
                    entry = datetime.strptime(entry_date, "%Y%m%d")
                    holding_days = (datetime.now() - entry).days
                    self._band_position['holding_days'] = holding_days
                except:
                    pass
                    
        # 保存状态
        self.save_state()
        
        Logger.info(f"日终结算完成 | 日期:{today}")

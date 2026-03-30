"""
QMT执行引擎模块
负责与QMT交互完成下单、撤单、持仓查询等操作
"""

import time
import threading
from datetime import datetime
from typing import Optional, Dict, List
from queue import Queue

from src.strategy.signal import Order, OrderStatus, TradingSignal
from src.log.logger import Logger


class QMTExecutor:
    """QMT执行引擎"""
    
    def __init__(self, config):
        """
        初始化QMT执行引擎
        
        Args:
            config: 配置对象
        """
        self.config = config
        
        # QMT连接对象
        self._qmt = None
        self._connected = False
        
        # 订单管理
        self._pending_orders: Dict[str, Order] = {}
        self._order_lock = threading.Lock()
        
        # 回调处理
        self._callbacks = []
        
        # 订单队列
        self._order_queue = Queue()
        self._order_thread = None
        self._running = False
        
        Logger.info("QMT执行引擎初始化完成")
        
    def connect(self) -> bool:
        """
        连接QMT

        Returns:
            是否连接成功
        """
        try:
            # 尝试导入XtQuant
            from xtquant.xttrader import XtQuantTrader
            from xtquant.xttype import StockAccount

            # 获取QMT路径
            qmt_path = getattr(self.config, 'qmt_path', None) or getattr(self.config, 'qmt', {}).get('path', '')
            session_id = getattr(self.config, 'session_id', 123456)

            # 创建QMT交易对象
            self._qmt = XtQuantTrader(qmt_path, session_id)

            # 启动连接
            Logger.info(f"正在连接QMT | 路径:{qmt_path}")
            connect_result = self._qmt.start()

            if connect_result != 0:
                Logger.error(f"QMT启动失败: {connect_result}")
                return False

            # 连接QMT
            result = self._qmt.connect()

            if result == 0:
                self._connected = True
                Logger.info("QMT连接成功")

                # 创建账户对象
                self._account = StockAccount(self.config.qmt_account, "STOCK")

                # 启动订单处理线程
                self._start_order_processor()

                return True
            else:
                Logger.error(f"QMT连接失败: {result}")
                return False

        except ImportError as e:
            Logger.warning(f"XtQuant未安装，启用模拟模式: {e}")
            self._connected = True
            return True

        except Exception as e:
            Logger.error(f"QMT连接异常: {e}")
            return False
            
    def disconnect(self):
        """断开QMT连接"""
        self._running = False
        
        if self._order_thread:
            self._order_thread.join(timeout=5)
            
        if self._qmt and self._connected:
            try:
                self._qmt.disconnect()
                Logger.info("QMT已断开连接")
            except Exception as e:
                Logger.error(f"断开QMT连接异常: {e}")
                
        self._connected = False
        
    def is_connected(self) -> bool:
        """检查是否连接"""
        return self._connected
        
    # ==================== 行情订阅 ====================
    
    def subscribe(self, stock_code: str):
        """
        订阅行情
        
        Args:
            stock_code: 股票代码
        """
        if self._qmt and self._connected:
            try:
                self._qmt.subscribe(stock_code)
                Logger.info(f"已订阅行情 | 标的:{stock_code}")
            except Exception as e:
                Logger.error(f"订阅行情失败: {e}")
                
    def unsubscribe(self, stock_code: str):
        """
        取消订阅行情
        
        Args:
            stock_code: 股票代码
        """
        if self._qmt and self._connected:
            try:
                self._qmt.unsubscribe(stock_code)
                Logger.info(f"已取消订阅行情 | 标的:{stock_code}")
            except Exception as e:
                Logger.error(f"取消订阅行情失败: {e}")
                
    def get_quote(self, stock_code: str) -> Optional[Dict]:
        """
        获取实时行情
        
        Args:
            stock_code: 股票代码
            
        Returns:
            行情数据字典
        """
        if self._qmt and self._connected:
            try:
                quote = self._qmt.get_quote(stock_code)
                if quote:
                    return {
                        "stock_code": stock_code,
                        "last_price": quote.last_price,
                        "open": quote.open,
                        "high": quote.high,
                        "low": quote.low,
                        "volume": quote.volume,
                        "amount": quote.amount,
                        "change": quote.change,
                        "change_pct": quote.change_pct,
                        "bid": quote.bid,
                        "ask": quote.ask,
                        "update_time": quote.update_time
                    }
            except Exception as e:
                Logger.error(f"获取行情失败: {e}")
                
        return None
        
    def get_minute_data(self, stock_code: str, date: str) -> List[Dict]:
        """
        获取分时数据
        
        Args:
            stock_code: 股票代码
            date: 日期，格式YYYYMMDD
            
        Returns:
            分时数据列表
        """
        if self._qmt and self._connected:
            try:
                minute_data = self._qmt.get_minute_data(stock_code, date)
                return [
                    {
                        "time": m.time,
                        "price": m.price,
                        "volume": m.volume,
                        "amount": m.amount
                    }
                    for m in minute_data
                ]
            except Exception as e:
                Logger.error(f"获取分时数据失败: {e}")
                
        return []
        
    # ==================== 下单操作 ====================
    
    def submit_order(self, signal: TradingSignal) -> Optional[Order]:
        """
        提交订单
        
        Args:
            signal: 交易信号
            
        Returns:
            订单对象
        """
        # 创建订单
        order = Order()
        order.stock_code = signal.stock_code
        order.direction = signal.direction
        order.price = signal.price
        order.quantity = signal.quantity
        order.signal_type = signal.signal_type
        order.status = OrderStatus.PENDING.value
        order.submit_time = datetime.now().strftime("%H:%M:%S")
        
        # 加入订单队列
        self._order_queue.put(order)
        
        Logger.log_signal(
            signal.signal_type,
            signal.direction,
            signal.stock_code,
            signal.quantity,
            signal.price,
            signal.reason
        )
        
        return order
        
    def _process_order(self, order: Order) -> bool:
        """
        处理订单
        
        Args:
            order: 订单对象
            
        Returns:
            是否处理成功
        """
        if not self._connected:
            order.status = OrderStatus.FAILED.value
            order.error_message = "QMT未连接"
            return False
            
        try:
            # 调用QMT下单
            order_id = self._qmt.order_stock(
                stock_code=order.stock_code,
                direction=order.direction,
                price=order.price,
                quantity=order.quantity,
                order_type="STOCK",
                price_type="LIMIT"
            )
            
            if order_id:
                order.order_id = order_id
                order.status = OrderStatus.SUBMITTED.value
                order.update_time = datetime.now().strftime("%H:%M:%S")
                
                # 保存到待处理订单
                with self._order_lock:
                    self._pending_orders[order_id] = order
                    
                Logger.log_order(
                    order_id,
                    order.direction,
                    order.stock_code,
                    order.quantity,
                    order.price,
                    order.status
                )
                
                return True
            else:
                order.status = OrderStatus.FAILED.value
                order.error_message = "下单失败"
                return False
                
        except Exception as e:
            Logger.error(f"下单异常: {e}")
            order.status = OrderStatus.FAILED.value
            order.error_message = str(e)
            return False
            
    def cancel_order(self, order_id: str) -> bool:
        """
        撤单
        
        Args:
            order_id: 订单ID
            
        Returns:
            是否撤单成功
        """
        if not self._connected:
            return False
            
        try:
            result = self._qmt.cancel_order(order_id)
            if result:
                Logger.log_order_cancelled(order_id, "手动撤单")
                return True
            else:
                Logger.warning(f"撤单失败: {order_id}")
                return False
                
        except Exception as e:
            Logger.error(f"撤单异常: {e}")
            return False
            
    def cancel_all_pending(self):
        """撤销所有挂单"""
        with self._order_lock:
            for order_id in list(self._pending_orders.keys()):
                order = self._pending_orders.get(order_id)
                if order and order.status == OrderStatus.SUBMITTED.value:
                    self.cancel_order(order_id)
                    
    # ==================== 查询操作 ====================
    
    def get_account(self) -> Optional[Dict]:
        """
        获取账户资金信息

        Returns:
            账户资金字典
        """
        if self._qmt and self._connected and hasattr(self, '_account'):
            try:
                asset = self._qmt.query_stock_asset(self._account)
                if asset:
                    return {
                        "available": asset.cash,
                        "total": asset.total_asset,
                        "market_value": asset.market_value,
                        "frozen": asset.frozen_cash
                    }
            except Exception as e:
                Logger.error(f"获取账户信息失败: {e}")

        return None
        
    def get_position(self, stock_code: str = None) -> Dict:
        """
        获取持仓信息

        Args:
            stock_code: 股票代码，None表示查询所有持仓

        Returns:
            持仓字典
        """
        if self._qmt and self._connected and hasattr(self, '_account'):
            try:
                positions = self._qmt.query_stock_positions(self._account)
                result = {}
                for pos in positions:
                    # 如果指定了stock_code，只返回对应的持仓
                    if stock_code and pos.stock_code != stock_code:
                        continue
                    result[pos.stock_code] = {
                        "quantity": pos.volume,
                        "avg_cost": pos.avg_price,
                        "market_value": pos.market_value,
                        "frozen": pos.locked_quantity
                    }
                return result
            except Exception as e:
                Logger.error(f"获取持仓信息失败: {e}")

        return {}
        
    def get_order(self, order_id: str) -> Optional[Dict]:
        """
        查询订单状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单信息字典
        """
        if self._qmt and self._connected:
            try:
                order = self._qmt.get_order(order_id)
                if order:
                    return {
                        "order_id": order.order_id,
                        "status": order.status,
                        "filled_quantity": order.filled_quantity,
                        "remain_quantity": order.remain_quantity,
                        "price": order.price
                    }
            except Exception as e:
                Logger.error(f"查询订单失败: {e}")
                
        return None
        
    # ==================== 订单处理线程 ====================
    
    def _start_order_processor(self):
        """启动订单处理线程"""
        self._running = True
        self._order_thread = threading.Thread(target=self._order_processor_loop, daemon=True)
        self._order_thread.start()
        
    def _order_processor_loop(self):
        """订单处理循环"""
        while self._running:
            try:
                # 处理订单队列
                if not self._order_queue.empty():
                    order = self._order_queue.get_nowait()
                    self._process_order(order)
                    
                # 检查待处理订单状态
                self._check_pending_orders()
                
                time.sleep(0.5)
                
            except Exception as e:
                Logger.error(f"订单处理循环异常: {e}")
                
    def _check_pending_orders(self):
        """检查待处理订单状态"""
        with self._order_order_lock:
            order_ids = list(self._pending_orders.keys())
            
        for order_id in order_ids:
            order_info = self.get_order(order_id)
            if not order_info:
                continue
                
            order = self._pending_orders.get(order_id)
            if not order:
                continue
                
            status = order_info.get("status", "")
            filled = order_info.get("filled_quantity", 0)
            
            # 根据状态更新订单
            if status == "filled":
                order.status = OrderStatus.FILLED.value
                order.filled_quantity = filled
                order.update_time = datetime.now().strftime("%H:%M:%S")
                
                # 触发回调
                self._on_order_filled(order)
                
                # 移除待处理订单
                with self._order_lock:
                    del self._pending_orders[order_id]
                    
            elif status == "partial":
                if order.status != OrderStatus.PARTIAL.value:
                    order.status = OrderStatus.PARTIAL.value
                    order.filled_quantity = filled
                    order.update_time = datetime.now().strftime("%H:%M:%S")
                    self._on_order_partial(order)
                    
            elif status in ["cancelled", "rejected"]:
                order.status = OrderStatus.CANCELLED.value if status == "cancelled" else OrderStatus.REJECTED.value
                order.update_time = datetime.now().strftime("%H:%M:%S")
                
                if status == "cancelled":
                    self._on_order_cancelled(order)
                else:
                    self._on_order_rejected(order, order_info.get("error_msg", ""))
                    
                with self._order_lock:
                    del self._pending_orders[order_id]
                    
    # 临时属性用于锁
    _order_order_lock = property(lambda self: self._order_lock)
                    
    # ==================== 回调处理 ====================
    
    def register_callback(self, callback):
        """注册回调"""
        self._callbacks.append(callback)
        
    def _on_order_filled(self, order: Order):
        """订单成交回调"""
        Logger.log_order_filled(order.order_id, order.filled_quantity, order.price)
        
        for callback in self._callbacks:
            try:
                callback.on_order_filled(order)
            except Exception as e:
                Logger.error(f"成交回调执行异常: {e}")
                
    def _on_order_partial(self, order: Order):
        """订单部分成交回调"""
        Logger.log_order(order.order_id, order.direction, order.stock_code,
                        order.quantity, order.price, f"部分成交:{order.filled_quantity}")
        
        for callback in self._callbacks:
            try:
                callback.on_order_partial(order)
            except Exception as e:
                Logger.error(f"部分成交回调执行异常: {e}")
                
    def _on_order_cancelled(self, order: Order):
        """订单撤单回调"""
        Logger.log_order_cancelled(order.order_id)
        
        for callback in self._callbacks:
            try:
                callback.on_order_cancelled(order)
            except Exception as e:
                Logger.error(f"撤单回调执行异常: {e}")
                
    def _on_order_rejected(self, order: Order, reason: str):
        """订单拒绝回调"""
        Logger.log_order_rejected(order.order_id, reason)
        
        for callback in self._callbacks:
            try:
                callback.on_order_rejected(order, reason)
            except Exception as e:
                Logger.error(f"拒绝回调执行异常: {e}")
                
    # ==================== 模拟模式 ====================
    
    def set_mock_mode(self):
        """设置模拟模式（用于测试）"""
        Logger.info("启用模拟模式")
        self._connected = True
        
    def mock_submit_order(self, signal: TradingSignal) -> Order:
        """
        模拟下单（用于测试）
        
        Args:
            signal: 交易信号
            
        Returns:
            订单对象
        """
        order = Order()
        order.order_id = f"MOCK_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        order.stock_code = signal.stock_code
        order.direction = signal.direction
        order.price = signal.price
        order.quantity = signal.quantity
        order.signal_type = signal.signal_type
        order.status = OrderStatus.FILLED.value
        order.filled_quantity = signal.quantity
        order.submit_time = datetime.now().strftime("%H:%M:%S")
        order.update_time = datetime.now().strftime("%H:%M:%S")
        
        Logger.log_order_filled(order.order_id, order.filled_quantity, order.price)
        
        return order

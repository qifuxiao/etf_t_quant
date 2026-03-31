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
        self._trader = None
        self._account = None
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

    def start(self):
        """
        启动 QMT 并连接
        """
        from xtquant.xttrader import XtQuantTrader
        from xtquant.xttype import StockAccount

        # 获取QMT配置
        qmt_path = self.config.qmt_path if hasattr(self.config, 'qmt_path') else ''
        account_id = self.config.qmt_account if hasattr(self.config, 'qmt_account') else ''
        session_id = self.config.session_id if hasattr(self.config, 'session_id') else 123456

        Logger.info(f"🚀 启动 QMT: path={qmt_path}, account={account_id}")

        # 初始化 trader
        self._trader = XtQuantTrader(qmt_path, session_id)
        self._trader.start()

        # 连接 QMT
        result = self._trader.connect()
        if result != 0:
            Logger.error(f"❌ QMT 连接失败: {result}")
            raise RuntimeError(f"QMT 连接失败: {result}")

        Logger.info("✅ QMT 连接成功")

        # 初始化 account 对象（必须指定 STOCK）
        self._account = StockAccount(account_id, "STOCK")
        self._connected = True

        # 启动订单处理线程
        self._start_order_processor()

    def stop(self):
        """
        停止 QMT
        """
        self._running = False

        if self._order_thread:
            self._order_thread.join(timeout=5)

        if self._trader:
            self._trader.stop()
            Logger.info("🛑 QMT 已停止")

        self._connected = False

    def connect(self) -> bool:
        """
        连接QMT（兼容旧接口）
        """
        try:
            self.start()
            return True
        except Exception as e:
            Logger.error(f"QMT连接异常: {e}")
            return False

    def disconnect(self):
        """断开QMT连接"""
        self.stop()

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    # ========================
    # 查询资金
    # ========================
    def get_account(self) -> Optional[Dict]:
        """
        获取账户资金信息
        """
        if self._trader and self._connected and self._account:
            try:
                asset = self._trader.query_stock_asset(self._account)
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

    # ========================
    # 查询持仓
    # ========================
    def get_position(self, stock_code: str = None) -> Dict:
        """
        获取持仓信息
        """
        if self._trader and self._connected and self._account:
            try:
                positions = self._trader.query_stock_positions(self._account)
                result = {}
                for pos in positions:
                    # 如果指定了stock_code，只返回对应的持仓
                    if stock_code and pos.stock_code != stock_code:
                        continue
                    result[pos.stock_code] = {
                        "quantity": pos.volume,
                        "can_use_volume": pos.can_use_volume,
                        "avg_cost": pos.avg_price,
                        "market_value": pos.market_value,
                    }
                return result
            except Exception as e:
                Logger.error(f"获取持仓信息失败: {e}")

        return {}

    def subscribe(self, stock_code: str):
        """
        订阅行情
        
        注意：QMT的subscribe方法需要account对象而非stock_code。
        由于用户主要使用get_quote()获取行情，此处静默处理订阅请求。
        如需实时推送，可使用xtdata.subscribe_quote()实现。
        """
        # 静默处理：QMT的trader.subscribe需要account对象，不支持按股票订阅
        # 用户通过get_quote()轮询获取行情，不需要推送机制
        Logger.debug(f"行情订阅请求已记录 | 标的:{stock_code} (使用get_quote轮询)")

    def unsubscribe(self, stock_code: str):
        """取消订阅行情"""
        # 静默处理：与subscribe对应
        Logger.debug(f"取消订阅请求已记录 | 标的:{stock_code}")

    def get_quote(self, stock_code: str) -> Optional[Dict]:
        """获取实时行情"""
        try:
            # 使用 xtdata 获取实时行情
            import xtquant.xtdata as xtdata
            
            # 订阅行情
            xtdata.subscribe_quote(stock_code)
            
            # 获取最新行情
            data = xtdata.get_market_data(
                field_list=["lastPrice", "open", "high", "low", "volume", "amount", 
                           "change", "priceChange", "bid", "ask", "updateTime"],
                stock_list=[stock_code],
                period="tick",
                count=1
            )
            
            if stock_code in data and len(data[stock_code]) > 0:
                tick = data[stock_code][0]
                return {
                    "stock_code": stock_code,
                    "last_price": float(tick.get("lastPrice", 0)),
                    "open": float(tick.get("open", 0)),
                    "high": float(tick.get("high", 0)),
                    "low": float(tick.get("low", 0)),
                    "volume": int(tick.get("volume", 0)),
                    "amount": float(tick.get("amount", 0)),
                    "change": float(tick.get("priceChange", 0)),
                    "change_pct": float(tick.get("change", 0)) / 100 if tick.get("change") else 0,
                    "bid": tick.get("bid", []),
                    "ask": tick.get("ask", []),
                    "update_time": tick.get("updateTime", "")
                }
        except Exception as e:
            Logger.error(f"获取行情失败: {e}")
            
        return None

    # ========================
    # 订单操作
    # ========================
    def place_order(self, stock_code: str, direction: str, price: float, quantity: int) -> Optional[str]:
        """
        下单
        """
        if not self._connected:
            Logger.warning("QMT未连接，无法下单")
            return None

        try:
            from xtquant import xtconstant

            # 委托方向
            if direction == "buy":
                direction = xtconstant.DIRECTION_BUY
            else:
                direction = xtconstant.DIRECTION_SELL

            # 下单
            order_id = self._trader.place_order(
                stock_code,
                xtconstant.STOCK,
                direction,
                price,
                quantity,
                "".encode('utf-8')  # 策略ID
            )

            Logger.info(f"下单成功 | 股票:{stock_code} | 方向:{direction} | 价格:{price} | 数量:{quantity} | 订单ID:{order_id}")

            # 记录订单
            with self._order_lock:
                self._pending_orders[order_id] = Order(
                    order_id=order_id,
                    stock_code=stock_code,
                    direction=direction,
                    price=price,
                    quantity=quantity,
                    status=OrderStatus.SUBMITTED
                )

            return order_id

        except Exception as e:
            Logger.error(f"下单失败: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if not self._connected:
            Logger.warning("QMT未连接，无法撤单")
            return False

        try:
            self._trader.cancel_order(order_id)
            Logger.info(f"撤单成功 | 订单ID:{order_id}")
            return True
        except Exception as e:
            Logger.error(f"撤单失败: {e}")
            return False

    # ========================
    # 订单处理线程
    # ========================
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
                while not self._order_queue.empty():
                    order_task = self._order_queue.get_nowait()
                    self._process_order_task(order_task)

                time.sleep(0.1)

            except Exception as e:
                Logger.error(f"订单处理异常: {e}")

    def _process_order_task(self, task: Dict):
        """处理单个订单任务"""
        # 实现订单处理逻辑
        pass

    def register_callback(self, callback):
        """注册回调"""
        self._callbacks.append(callback)

    def _notify_callbacks(self, event_type: str, data: Dict):
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                Logger.error(f"回调通知失败: {e}")

    # ========================
    # 兼容旧接口
    # ========================
    def get_minute_data(self, stock_code: str, date: str) -> List[Dict]:
        """获取分时数据（兼容）"""
        try:
            # 使用 xtdata 获取分时数据
            import xtquant.xtdata as xtdata
            
            # 转换日期格式
            if len(date) == 8:
                # date 格式为 YYYYMMDD
                start_time = date + "093000"
                end_time = date + "150000"
            else:
                # 尝试直接使用
                start_time = date
                end_time = date
            
            # 获取1分钟K线数据
            data = xtdata.get_market_data(
                field_list=["time", "open", "high", "low", "close", "volume", "amount"],
                stock_list=[stock_code],
                period="1m",
                start_time=start_time,
                end_time=end_time,
                count=-1
            )
            
            if "time" in data:
                times = data["time"]
                opens = data.get("open", [])
                highs = data.get("high", [])
                lows = data.get("low", [])
                closes = data.get("close", [])
                volumes = data.get("volume", [])
                amounts = data.get("amount", [])
                
                result = []
                for i in range(len(times)):
                    # 转换时间戳
                    import datetime
                    try:
                        ts = times[i] / 1000  # 毫秒转秒
                        dt = datetime.datetime.fromtimestamp(ts)
                        time_str = dt.strftime("%H:%M:%S")
                    except:
                        time_str = str(times[i])
                    
                    result.append({
                        "time": time_str,
                        "price": float(closes[i]) if i < len(closes) else 0,
                        "volume": int(volumes[i]) if i < len(volumes) else 0,
                        "amount": float(amounts[i]) if i < len(amounts) else 0
                    })
                return result
                
        except Exception as e:
            Logger.error(f"获取分时数据失败: {e}")
            
        return []

    def get_order(self, order_id: str) -> Optional[Dict]:
        """查询订单状态"""
        if self._trader and self._connected:
            try:
                order = self._trader.query_order(order_id)
                if order:
                    return {
                        "order_id": order.order_id,
                        "stock_code": order.stock_code,
                        "direction": order.direction,
                        "price": order.price,
                        "quantity": order.volume,
                        "traded_volume": order.traded_volume,
                        "status": order.status
                    }
            except Exception as e:
                Logger.error(f"查询订单失败: {e}")

        return None

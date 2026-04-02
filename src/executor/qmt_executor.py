"""
QMT执行引擎模块
负责与QMT交互完成下单、撤单、持仓查询等操作
"""

import time
import threading
from datetime import datetime
from typing import Optional, Dict, List, Any
from queue import Queue

from src.strategy.signal import Order, OrderStatus, TradingSignal
from src.log.logger import Logger


def format_stock_code(stock_code: str) -> str:
    """
    将股票代码转换为 xtdata 需要的格式
    
    Args:
        stock_code: 股票代码，支持以下格式：
            - "300124" -> "300124.SZ"
            - "600000" -> "600000.SH" 
            - "300124.SZ" -> "300124.SZ" (已正确格式直接返回)
            - "600000.SH" -> "600000.SH"
    
    Returns:
        格式化后的股票代码，如 "300124.SZ"
    """
    if not stock_code:
        return stock_code
    
    # 如果已经是正确格式，直接返回
    if '.' in stock_code:
        return stock_code
    
    # 根据股票代码前缀判断市场
    # 6开头：上海证券交易所 (SH)
    # 0/3开头：深圳证券交易所 (SZ)
    if stock_code.startswith('6'):
        return f"{stock_code}.SH"
    else:
        # 0开头、3开头、8开头（北交所）、4开头（科创板）都是深圳
        return f"{stock_code}.SZ"


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
        # 尝试导入 xtquant，如果失败则记录警告
        try:
            from xtquant.xttrader import XtQuantTrader
            from xtquant.xttype import StockAccount
        except ImportError as e:
            Logger.error(f"❌ xtquant 导入失败: {e} | Python版本可能不兼容")
            Logger.warning("⚠️ 将以离线/模拟模式运行，部分功能可能不可用")
            self._connected = False
            return
        
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
            
            # 确保 xtdata 已连接
            try:
                xtdata.connect()
            except:
                pass  # 可能已经连接
            
            # 转换为QMT格式 (如 300124 -> SZ.300124)
            qmt_code = format_stock_code(stock_code)
            
            Logger.info(f"获取实时行情 | qmt_code={qmt_code}")
            
            # 先下载历史日K线数据（只有下载过历史数据后才能获取实时行情）
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            
            # 下载历史数据并等待完成
            try:
                Logger.info(f"下载历史数据 | qmt_code={qmt_code} | {start_date}~{end_date}")
                # download_history_data 可能返回下载结果，需要等待完成
                result = xtdata.download_history_data(qmt_code, "1d", start_date, end_date)
                Logger.info(f"历史数据下载结果: {result}")
                
                # 等待数据写入（xtdata是异步写入的）
                time.sleep(1)
            except Exception as e:
                Logger.warning(f"历史数据下载失败（可能已存在）: {e}")
            
            # 订阅行情
            xtdata.subscribe_quote(qmt_code)
            
            # 等待订阅数据返回（增加等待时间确保数据到达）
            time.sleep(0.5)
            
            # 重试获取最新行情（最多重试3次）
            # 使用 get_full_tick() 获取实时行情（官方推荐方式）
            max_retries = 3
            retry_delay = 0.5
            
            for retry in range(max_retries):
                # 获取实时行情 - 使用 get_full_tick (官方推荐方式)
                tick_data = xtdata.get_full_tick([qmt_code])
                
                Logger.info(f"get_full_tick返回数据类型: {type(tick_data)}")
                if isinstance(tick_data, dict):
                    Logger.info(f"get_full_tick返回keys: {tick_data.keys()}")
                    if qmt_code in tick_data:
                        Logger.info(f"标的行情数据: {tick_data[qmt_code]}")
                    else:
                        Logger.warning(f"标的 {qmt_code} 不在返回数据中")

                # 提取 tick 数据
                # get_full_tick 返回格式可能是: { "SZ.300124": [{tick_dict}, ...] } 或 { "SZ.300124": tick_dict }
                tick = None
                if isinstance(tick_data, dict) and qmt_code in tick_data:
                    ticks = tick_data[qmt_code]
                    if isinstance(ticks, list) and ticks:
                        tick = ticks[0]  # 取第一个tick
                    elif isinstance(ticks, dict):
                        # 某些版本直接返回 dict 而不是 list
                        tick = ticks
                
                if tick is not None:
                    Logger.info(f"行情获取成功 | 标的:{qmt_code} | 价格:{tick.get('lastPrice')}")
                    return {
                        "stock_code": stock_code,
                        "last_price": self._safe_float(tick.get("lastPrice")),
                        "open": self._safe_float(tick.get("open")),
                        "high": self._safe_float(tick.get("high")),
                        "low": self._safe_float(tick.get("low")),
                        "volume": self._safe_int(tick.get("volume")),
                        "amount": self._safe_float(tick.get("amount")),
                        "change": self._safe_float(tick.get("priceChange")),
                        "change_pct": self._safe_float(tick.get("change")) / 100 if tick.get("change") not in (None, "") else 0.0,
                        "bid": tick.get("bid", []),
                        "ask": tick.get("ask", []),
                        "update_time": tick.get("time") or tick.get("updateTime", "")
                    }
                
                # 重试前等待
                if retry < max_retries - 1:
                    Logger.warning(f"行情数据为空，重试 {retry+1}/{max_retries} | 标的:{qmt_code}")
                    time.sleep(retry_delay)
            
            # 所有重试都失败
            Logger.warning(f"行情数据为空 | 标的:{qmt_code} | 已重试{max_retries}次")
            return None
        except ImportError as e:
            Logger.error(f"xtquant 模块导入失败，可能是未安装或版本不兼容: {e}")
            return None
        except Exception as e:
            Logger.error(f"获取行情失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            
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
            
            # 确保 xtdata 已连接
            try:
                xtdata.connect()
            except:
                pass  # 可能已经连接
            
            # 转换为QMT格式 (如 300124 -> SZ.300124)
            qmt_code = format_stock_code(stock_code)
            
            # 转换日期格式
            if len(date) == 8:
                # date 格式为 YYYYMMDD
                start_time = date + "093000"
                end_time = date + "150000"
            else:
                # 尝试直接使用
                start_time = date
                end_time = date
            
            Logger.info(f"获取分时数据 | qmt_code={qmt_code} | date={date} | start={start_time} | end={end_time}")
            
            # 尝试下载数据（参考示例代码）
            Logger.info(f"尝试下载分时数据 | qmt_code={qmt_code} | date={date}")
            try:
                result = xtdata.download_history_data(qmt_code, "1m", date, date)
                Logger.info(f"数据下载结果: {result}")
            except Exception as e:
                Logger.warning(f"数据下载失败（可能已存在）: {e}")
            
            # 获取1分钟K线数据
            data = xtdata.get_market_data(
                field_list=["time", "open", "high", "low", "close", "volume", "amount"],
                stock_list=[qmt_code],
                period="1m",
                start_time=start_time,
                end_time=end_time,
                count=-1
            )
            
            Logger.info(f"xtdata返回数据类型: {type(data)} | keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
            
            minute_list = self._extract_minute_bars(data, qmt_code)
            if minute_list is None:
                Logger.warning(f"分时数据为空 | 标的:{qmt_code} | 日期:{date} | 原始数据={data}")
                return []
            Logger.info(f"分时数据获取成功 | 条数:{len(minute_list)}")
            return minute_list
                
        except Exception as e:
            Logger.error(f"获取分时数据失败: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            
        return []

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

    def _extract_tick(self, data: Any, qmt_code: str) -> Optional[Dict]:
        """兼容多种 xtdata tick 返回结构，提取最后一个 tick"""
        if data is None:
            return None

        # 结构1：{ "SZ.300124": [ {tick...}, ... ] }
        if isinstance(data, dict) and qmt_code in data:
            ticks = data.get(qmt_code)
            if isinstance(ticks, list) and ticks:
                last_tick = ticks[-1]
                if isinstance(last_tick, dict):
                    return last_tick

        # 结构2：{ "lastPrice": { "SZ.300124": [..] }, ... }
        if isinstance(data, dict):
            field_candidates = [
                "lastPrice", "open", "high", "low", "volume",
                "amount", "change", "priceChange", "bid", "ask", "updateTime"
            ]
            tick: Dict[str, Any] = {}
            found = False
            for field in field_candidates:
                field_data = data.get(field)
                if isinstance(field_data, dict) and qmt_code in field_data:
                    arr = field_data.get(qmt_code)
                    if isinstance(arr, (list, tuple)) and arr:
                        tick[field] = arr[-1]
                        found = True
                    elif arr is not None and not isinstance(arr, (list, tuple)):
                        tick[field] = arr
                        found = True
            if found:
                return tick

        return None

    def _extract_minute_bars(self, data: Any, qmt_code: str) -> Optional[List[Dict]]:
        """兼容多种 xtdata 分时返回结构，统一为 minute 列表
        
        xtdata get_market_data 返回的数据结构:
        - data 是一个字典，包含 'open', 'high', 'low', 'close', 'volume', 'amount' 等键
        - 每个键对应一个 DataFrame，索引是股票代码，列是时间戳
        - 时间从 data['close'].columns.tolist() 获取
        - 数据从 data['字段'].loc[qmt_code].values 获取
        """
        if data is None:
            return None

        times: List[Any] = []
        closes: List[Any] = []
        volumes: List[Any] = []
        amounts: List[Any] = []

        # 结构0：xtdata 返回的字典格式 { 'open': DataFrame, 'high': DataFrame, ... }
        # 每个 DataFrame 的索引是股票代码，列是时间戳
        try:
            import pandas as pd
            if isinstance(data, dict):
                # 检查是否是 xtdata 返回的字典格式（每个字段都是 DataFrame）
                if 'close' in data and isinstance(data['close'], pd.DataFrame):
                    close_df = data['close']
                    
                    # 获取时间列表（从 close DataFrame 的列获取）
                    if hasattr(close_df, 'columns'):
                        times = close_df.columns.tolist()
                        Logger.info(f"从 data['close'].columns 获取时间列表 | 条数:{len(times)}")
                        
                        # 检查 qmt_code 是否在 DataFrame 的索引中
                        if qmt_code in close_df.index:
                            # 从各字段 DataFrame 中提取该股票的数据
                            opens = data.get('open', pd.Series())
                            highs = data.get('high', pd.Series())
                            lows = data.get('low', pd.Series())
                            closes = data.get('close', pd.Series())
                            volumes = data.get('volume', pd.Series())
                            amounts = data.get('amount', pd.Series())
                            
                            # 使用 loc 获取对应股票的数据，并转换为列表
                            if isinstance(opens, pd.DataFrame) and qmt_code in opens.index:
                                opens = opens.loc[qmt_code].values
                            if isinstance(highs, pd.DataFrame) and qmt_code in highs.index:
                                highs = highs.loc[qmt_code].values
                            if isinstance(lows, pd.DataFrame) and qmt_code in lows.index:
                                lows = lows.loc[qmt_code].values
                            if isinstance(closes, pd.DataFrame) and qmt_code in closes.index:
                                closes = closes.loc[qmt_code].values
                            if isinstance(volumes, pd.DataFrame) and qmt_code in volumes.index:
                                volumes = volumes.loc[qmt_code].values
                            if isinstance(amounts, pd.DataFrame) and qmt_code in amounts.index:
                                amounts = amounts.loc[qmt_code].values
                            
                            Logger.info(f"xtdata分时数据提取成功 | 标的:{qmt_code} | 条数:{len(times)}")
                            return self._build_minute_result_full(times, opens, highs, lows, closes, volumes, amounts)
                        else:
                            Logger.warning(f"标的 {qmt_code} 不在 DataFrame 索引中，索引: {close_df.index.tolist()[:5]}...")
                            return None
        except ImportError:
            pass
        except Exception as e:
            Logger.warning(f"xtdata字典格式解析失败: {e}")

        # 结构1：pandas DataFrame（get_market_data 可能返回 DataFrame）
        try:
            import pandas as pd
            if isinstance(data, pd.DataFrame):
                if data.empty:
                    return None
                
                # 特殊处理 MultiIndex DataFrame (xtdata 返回的复杂结构)
                # 数据格式: 索引有股票代码，数据行有时间戳和值
                if hasattr(data, 'index') and hasattr(data, 'columns'):
                    # 尝试获取所有数据值
                    try:
                        all_values = data.values
                        if len(all_values) > 0:
                            # 跳过第一行（列标题）和股票代码行，提取数据
                            for row in all_values[2:]:  # 跳过前两行
                                if len(row) > 1:
                                    times.append(str(row[0]))  # 时间戳
                                    closes.append(float(row[4]) if row[4] else 0)  # close 是第5列
                                    volumes.append(int(row[5]) if row[5] else 0)   # volume 是第6列
                                    amounts.append(float(row[6]) if row[6] else 0)  # amount 是第7列
                            if times:
                                Logger.info(f"从DataFrame提取分时数据成功 | 条数:{len(times)}")
                                return self._build_minute_result(times, closes, volumes, amounts)
                    except Exception as e:
                        Logger.warning(f"DataFrame解析失败: {e}")
                
                # 简单 DataFrame 格式
                if "time" in data.columns:
                    try:
                        times = data["time"].tolist() if "time" in data.columns else []
                        closes = data["close"].tolist() if "close" in data.columns else []
                        volumes = data["volume"].tolist() if "volume" in data.columns else []
                        amounts = data["amount"].tolist() if "amount" in data.columns else []
                        if times:
                            return self._build_minute_result(times, closes, volumes, amounts)
                    except:
                        pass
                return None
        except ImportError:
            pass

        # 结构1：{ "time": [...], "close":[...], ... }
        if isinstance(data, dict) and "time" in data:
            time_val = data.get("time")
            # 处理 DataFrame 或其他非list类型
            if time_val is None:
                times = []
            elif isinstance(time_val, list):
                times = time_val
            else:
                # 可能是 DataFrame 或其他类型
                try:
                    import pandas as pd
                    if isinstance(time_val, pd.DataFrame):
                        times = time_val.tolist() if len(time_val) > 0 else []
                    else:
                        times = []
                except:
                    times = []
            
            close_val = data.get("close")
            if isinstance(close_val, list):
                closes = close_val
            else:
                try:
                    import pandas as pd
                    if isinstance(close_val, pd.DataFrame):
                        closes = close_val.tolist() if len(close_val) > 0 else []
                    else:
                        closes = []
                except:
                    closes = []
            
            volume_val = data.get("volume")
            if isinstance(volume_val, list):
                volumes = volume_val
            else:
                try:
                    import pandas as pd
                    if isinstance(volume_val, pd.DataFrame):
                        volumes = volume_val.tolist() if len(volume_val) > 0 else []
                    else:
                        volumes = []
                except:
                    volumes = []
                    
            amount_val = data.get("amount")
            if isinstance(amount_val, list):
                amounts = amount_val
            else:
                try:
                    import pandas as pd
                    if isinstance(amount_val, pd.DataFrame):
                        amounts = amount_val.tolist() if len(amount_val) > 0 else []
                    else:
                        amounts = []
                except:
                    amounts = []

        # 结构2：{ "time": {"SZ.300124":[...]}, "close": {"SZ.300124":[...]}, ... }
        elif isinstance(data, dict) and isinstance(data.get("time"), dict):
            time_map = data.get("time", {})
            if qmt_code not in time_map:
                return None
            times = time_map.get(qmt_code, []) or []
            close_map = data.get("close", {})
            volume_map = data.get("volume", {})
            amount_map = data.get("amount", {})
            closes = close_map.get(qmt_code, []) if isinstance(close_map, dict) else []
            volumes = volume_map.get(qmt_code, []) if isinstance(volume_map, dict) else []
            amounts = amount_map.get(qmt_code, []) if isinstance(amount_map, dict) else []
        else:
            return None

        if not isinstance(times, (list, tuple)) or len(times) == 0:
            return None

        return self._build_minute_result(times, closes, volumes, amounts)

    def _build_minute_result(
        self,
        times: List[Any],
        closes: List[Any],
        volumes: List[Any],
        amounts: List[Any]
    ) -> List[Dict]:
        """根据时间/价格等序列构造分时列表"""
        result = []
        for i in range(len(times)):
            time_str = self._format_time(times[i])
            price = self._safe_float(closes[i]) if i < len(closes) else 0.0
            volume = self._safe_int(volumes[i]) if i < len(volumes) else 0
            amount = self._safe_float(amounts[i]) if i < len(amounts) else 0.0
            result.append({
                "time": time_str,
                "price": price,
                "volume": volume,
                "amount": amount
            })
        return result

    def _build_minute_result_full(
        self,
        times: List[Any],
        opens: Any,
        highs: Any,
        lows: Any,
        closes: Any,
        volumes: Any,
        amounts: Any
    ) -> List[Dict]:
        """根据时间/价格等序列构造完整的分时列表（包含 OHLC）"""
        result = []
        # 确保所有数据都是列表
        if hasattr(opens, 'tolist'):
            opens = opens.tolist()
        if hasattr(highs, 'tolist'):
            highs = highs.tolist()
        if hasattr(lows, 'tolist'):
            lows = lows.tolist()
        if hasattr(closes, 'tolist'):
            closes = closes.tolist()
        if hasattr(volumes, 'tolist'):
            volumes = volumes.tolist()
        if hasattr(amounts, 'tolist'):
            amounts = amounts.tolist()
        
        for i in range(len(times)):
            time_str = self._format_time(times[i])
            open_price = self._safe_float(opens[i]) if isinstance(opens, list) and i < len(opens) else 0.0
            high_price = self._safe_float(highs[i]) if isinstance(highs, list) and i < len(highs) else 0.0
            low_price = self._safe_float(lows[i]) if isinstance(lows, list) and i < len(lows) else 0.0
            close_price = self._safe_float(closes[i]) if isinstance(closes, list) and i < len(closes) else 0.0
            volume = self._safe_int(volumes[i]) if isinstance(volumes, list) and i < len(volumes) else 0
            amount = self._safe_float(amounts[i]) if isinstance(amounts, list) and i < len(amounts) else 0.0
            result.append({
                "time": time_str,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "amount": amount
            })
        return result

    @staticmethod
    def _format_time(value: Any) -> str:
        """兼容时间戳/字符串格式为 HH:MM:SS"""
        import datetime
        try:
            if isinstance(value, (int, float)):
                ts = value / 1000 if value > 10_000_000_000 else value
                dt = datetime.datetime.fromtimestamp(ts)
                return dt.strftime("%H:%M:%S")
            return str(value)
        except Exception:
            return str(value)

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
        try:
            import xtquant.xtdata as xtdata
            
            # 转换为QMT格式 (如 300124 -> SZ.300124)
            qmt_code = format_stock_code(stock_code)
            
            # 获取日K线数据
            data = xtdata.get_market_data(
                field_list=["date", "open", "high", "low", "close", "volume", "amount"],
                stock_list=[qmt_code],
                period="1d",
                start_time=start_date,
                end_time=end_date,
                count=-1
            )
            
            if "date" in data:
                dates = data["date"]
                opens = data.get("open", [])
                highs = data.get("high", [])
                lows = data.get("low", [])
                closes = data.get("close", [])
                volumes = data.get("volume", [])
                amounts = data.get("amount", [])
                
                result = []
                for i in range(len(dates)):
                    # 转换日期格式
                    try:
                        ts = dates[i] / 1000  # 毫秒转秒
                        dt = datetime.fromtimestamp(ts)
                        date_str = dt.strftime("%Y%m%d")
                    except:
                        date_str = str(dates[i])
                    
                    result.append({
                        "date": date_str,
                        "open": float(opens[i]) if i < len(opens) else 0,
                        "high": float(highs[i]) if i < len(highs) else 0,
                        "low": float(lows[i]) if i < len(lows) else 0,
                        "close": float(closes[i]) if i < len(closes) else 0,
                        "volume": int(volumes[i]) if i < len(volumes) else 0,
                        "amount": float(amounts[i]) if i < len(amounts) else 0
                    })
                return result
                
        except Exception as e:
            Logger.error(f"获取K线数据失败: {e}")
            
        return []
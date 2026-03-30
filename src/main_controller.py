"""
主控模块
负责策略系统的启动、停止、调度和状态协调
"""

import time
import threading
import schedule
from datetime import datetime

from src.config import Config
from src.market_data import MarketModule
from src.strategy.t_strategy import TStrategy
from src.strategy.band_strategy import BandStrategy
from src.risk.risk_engine import RiskEngine
from src.executor.qmt_executor import QMTExecutor
from src.state.state_manager import StateManager
from src.log.logger import Logger, Logger as Log


class MainController:
    """主控模块"""
    
    def __init__(self, config: Config):
        """
        初始化主控模块
        
        Args:
            config: 配置对象
        """
        self.config = config
        
        # 系统状态
        self._status = "STOPPED"
        self._running = False
        
        # 模块初始化
        self.market = None
        self.executor = None
        self.state_manager = None
        self.risk_engine = None
        self.t_strategy = None
        self.band_strategy = None
        
        # 定时任务线程
        self._schedule_thread = None
        self._schedule_running = False
        
        # 主循环线程
        self._main_loop_thread = None
        
        # 日志模块初始化
        self._init_logging()
        
        Logger.info("主控模块初始化完成")
        
    def _init_logging(self):
        """初始化日志"""
        Log.init(
            log_dir=self.config.log_dir,
            log_level=self.config.log_level,
            rotation=self.config.log_rotation,
            retention=self.config.log_retention
        )
        
    def start(self):
        """启动策略系统"""
        if self._status == "RUNNING":
            Logger.warning("策略系统已在运行中")
            return
            
        self._status = "STARTING"
        
        try:
            # 1. 初始化QMT执行器
            self._init_executor()
            
            # 2. 初始化状态管理器
            self._init_state_manager()
            
            # 3. 初始化行情模块
            self._init_market()
            
            # 4. 初始化风控引擎
            self._init_risk_engine()
            
            # 5. 初始化策略
            self._init_strategies()
            
            # 6. 同步QMT数据
            self._sync_qmt_data()
            
            # 7. 订阅行情
            self._subscribe_market()
            
            # 8. 启动定时任务
            self._start_schedule()
            
            # 9. 启动主循环
            self._start_main_loop()
            
            self._status = "RUNNING"
            self._running = True
            
            Logger.info("=" * 50)
            Logger.info("策略系统启动成功")
            Logger.info(f"标的:{self.config.stock_code}")
            Logger.info(f"总资金:{self.config.total_capital}")
            Logger.info("=" * 50)
            
        except Exception as e:
            self._status = "ERROR"
            Logger.exception(f"策略系统启动失败: {e}")
            raise
            
    def stop(self):
        """停止策略系统"""
        if self._status != "RUNNING":
            Logger.warning("策略系统未在运行")
            return
            
        self._status = "STOPPING"
        self._running = False
        
        try:
            # 1. 停止主循环
            if self._main_loop_thread:
                self._main_loop_thread.join(timeout=5)
                
            # 2. 停止定时任务
            self._stop_schedule()
            
            # 3. 取消行情订阅
            if self.market:
                self.market.unsubscribe(self.config.stock_code)
                
            # 4. 撤销所有挂单
            if self.executor:
                self.executor.cancel_all_pending()
                
            # 5. 保存状态
            if self.state_manager:
                self.state_manager.save_state()
                
            # 6. 断开QMT连接
            if self.executor:
                self.executor.disconnect()
                
            self._status = "STOPPED"
            
            Logger.info("策略系统已停止")
            
        except Exception as e:
            Logger.exception(f"停止策略系统时发生异常: {e}")
            self._status = "ERROR"
            
    def run(self):
        """主循环（阻塞）"""
        while self._running:
            try:
                # 处理主循环任务
                time.sleep(1)
                
            except KeyboardInterrupt:
                Logger.info("收到中断信号")
                break
                
            except Exception as e:
                Logger.exception(f"主循环异常: {e}")
                
    def _init_executor(self):
        """初始化执行器"""
        Logger.info("初始化QMT执行器...")
        
        self.executor = QMTExecutor(self.config)
        
        # 注册订单回调
        self.executor.register_callback(self)
        
        # 连接QMT
        if not self.executor.connect():
            # 如果QMT连接失败，使用模拟模式
            Logger.warning("QMT连接失败，启用模拟模式")
            self.executor.set_mock_mode()
            
    def _init_state_manager(self):
        """初始化状态管理器"""
        Logger.info("初始化状态管理器...")
        
        self.state_manager = StateManager(self.config)
        
    def _init_market(self):
        """初始化行情模块"""
        Logger.info("初始化行情模块...")
        
        self.market = MarketModule(self.config, self.executor)
        
    def _init_risk_engine(self):
        """初始化风控引擎"""
        Logger.info("初始化风控引擎...")
        
        self.risk_engine = RiskEngine(
            self.config,
            self.state_manager,
            self.market
        )
        
    def _init_strategies(self):
        """初始化策略"""
        Logger.info("初始化策略...")
        
        # 做T策略
        self.t_strategy = TStrategy(
            self.config,
            self.market,
            self.state_manager
        )
        
        # 波段策略
        self.band_strategy = BandStrategy(
            self.config,
            self.market,
            self.state_manager
        )
        
    def _sync_qmt_data(self):
        """同步QMT数据"""
        Logger.info("同步QMT数据...")
        
        # 同步账户信息
        if self.executor.is_connected():
            self.state_manager.sync_account_from_qmt(self.executor)
            account = self.state_manager.get_account()
            Logger.info(f"账户信息 | 可用资金:{account.available:.2f} | 总资产:{account.total:.2f}")
            
        # 同步持仓信息
        if self.executor.is_connected():
            positions = self.executor.get_position(self.config.stock_code)
            if self.config.stock_code in positions:
                pos = positions[self.config.stock_code]
                self.state_manager.update_band_position(
                    quantity=pos['quantity'],
                    avg_cost=pos['avg_cost'],
                    direction="BUY"
                )
                Logger.info(f"持仓信息 | 数量:{pos['quantity']} | 成本:{pos['avg_cost']:.2f}")
                
    def _subscribe_market(self):
        """订阅行情"""
        Logger.info("订阅行情...")
        
        self.market.subscribe(self.config.stock_code)
        
        # 添加行情回调
        self.market.add_subscriber(self._on_quote_update)
        
    def _start_schedule(self):
        """启动定时任务"""
        Logger.info("启动定时任务...")
        
        self._schedule_running = True
        
        # 日终对账（15:00）
        schedule.every().day.at("15:05").do(self._daily_settlement)
        
        # 状态自动保存
        schedule.every(self.config.state_auto_save_interval).seconds.do(self._auto_save)
        
        # 启动定时任务线程
        self._schedule_thread = threading.Thread(
            target=self._schedule_loop,
            daemon=True
        )
        self._schedule_thread.start()
        
    def _stop_schedule(self):
        """停止定时任务"""
        self._schedule_running = False
        schedule.clear()
        
        if self._schedule_thread:
            self._schedule_thread.join(timeout=5)
            
    def _schedule_loop(self):
        """定时任务循环"""
        while self._schedule_running:
            schedule.run_pending()
            time.sleep(1)
            
    def _start_main_loop(self):
        """启动主循环"""
        # 主循环逻辑已在 run() 方法中实现
        # 这里可以添加其他定时检查
        
        pass
        
    # ==================== 回调处理 ====================
    
    def _on_quote_update(self, quote):
        """
        行情更新回调
        
        Args:
            quote: 行情数据
        """
        try:
            # 执行做T策略检查
            if self.config.t_strategy_enabled:
                signal = self.t_strategy.check_signals(quote)
                if signal:
                    # 风控检查
                    if self.risk_engine.check_signal(signal):
                        # 执行下单
                        self._execute_signal(signal)
                    else:
                        Logger.log_risk_block(signal.signal_type, "风控拦截")
                        
            # 执行波段策略检查（降低频率，每分钟检查一次）
            # 可以在定时任务中处理
            
        except Exception as e:
            Logger.exception(f"行情更新回调异常: {e}")
            
    def _execute_signal(self, signal):
        """
        执行交易信号
        
        Args:
            signal: 交易信号
        """
        try:
            # 提交订单
            order = self.executor.submit_order(signal)
            
            if order:
                Logger.log_order(
                    order.order_id,
                    signal.direction,
                    signal.stock_code,
                    signal.quantity,
                    signal.price,
                    "已提交"
                )
                
                # 更新状态
                self._update_position_on_order(signal, order)
                
        except Exception as e:
            Logger.exception(f"执行信号失败: {e}")
            
    def _update_position_on_order(self, signal, order):
        """
        根据订单更新持仓状态
        
        Args:
            signal: 交易信号
            order: 订单
        """
        # 在订单成交后更新
        # 这里只做预记录，实际更新在成交回调中处理
        pass
        
    def on_order_filled(self, order):
        """
        订单成交回调
        
        Args:
            order: 订单对象
        """
        try:
            # 获取信号类型
            signal_type = order.signal_type
            
            # 根据信号类型更新持仓
            if "T_LONG" in signal_type:
                if order.direction == "BUY":
                    # 做多T买入开仓
                    self.state_manager.update_long_t_position(
                        buy_price=order.price,
                        buy_time=order.submit_time,
                        quantity=order.filled_quantity,
                        order_id=order.order_id
                    )
                else:
                    # 做多T卖出平仓
                    profit = (order.price - self.state_manager.get_t_position().long_buy_price) * order.filled_quantity
                    self.state_manager.close_long_t_position()
                    
                    # 更新统计
                    self.t_strategy.update_t_stats(signal_type, profit)
                    
                    # 检查熔断条件
                    self.risk_engine.check_circuit_condition()
                    
            elif "T_SHORT" in signal_type:
                if order.direction == "SELL":
                    # 做空T卖出开仓
                    self.state_manager.update_short_t_position(
                        sell_price=order.price,
                        sell_time=order.submit_time,
                        quantity=order.filled_quantity,
                        order_id=order.order_id
                    )
                else:
                    # 做空T买回平仓
                    profit = (self.state_manager.get_t_position().short_sell_price - order.price) * order.filled_quantity
                    self.state_manager.close_short_t_position()
                    
                    # 更新统计
                    self.t_strategy.update_t_stats(signal_type, profit)
                    
                    # 检查熔断条件
                    self.risk_engine.check_circuit_condition()
                    
            elif "BAND" in signal_type:
                if order.direction == "BUY":
                    # 波段买入
                    self.state_manager.update_band_position(
                        quantity=order.filled_quantity,
                        avg_cost=order.price,
                        direction="BUY"
                    )
                    self.state_manager.add_band_record("ADD", order.price, order.filled_quantity)
                else:
                    # 波段卖出
                    position = self.state_manager.get_band_position()
                    profit = (order.price - position.avg_cost) * order.filled_quantity
                    
                    self.state_manager.update_band_position(
                        quantity=order.filled_quantity,
                        avg_cost=order.price,
                        direction="SELL"
                    )
                    self.state_manager.add_band_record("REDUCE", order.price, order.filled_quantity)
                    
                    # 更新统计
                    self.band_strategy.update_band_stats(signal_type, profit)
                    
                    # 检查熔断条件
                    self.risk_engine.check_circuit_condition()
                    
            # 保存状态
            self.state_manager.save_state()
            
            # 同步账户信息
            if self.executor.is_connected():
                self.state_manager.sync_account_from_qmt(self.executor)
                
        except Exception as e:
            Logger.exception(f"订单成交回调处理异常: {e}")
            
    def on_order_partial(self, order):
        """订单部分成交回调"""
        Logger.info(f"订单部分成交 | ID:{order.order_id} | 成交:{order.filled_quantity}/{order.quantity}")
        
    def on_order_cancelled(self, order):
        """订单撤单回调"""
        Logger.warning(f"订单已撤单 | ID:{order.order_id}")
        
    def on_order_rejected(self, order, reason):
        """订单拒绝回调"""
        Logger.error(f"订单被拒绝 | ID:{order.order_id} | 原因:{reason}")
        
    # ==================== 定时任务 ====================
    
    def _daily_settlement(self):
        """日终结算"""
        Logger.info("执行日终对账...")
        
        try:
            # 同步QMT数据
            self.state_manager.sync_account_from_qmt(self.executor)
            
            # 同步持仓
            if self.executor.is_connected():
                positions = self.executor.get_position(self.config.stock_code)
                if self.config.stock_code in positions:
                    pos = positions[self.config.stock_code]
                    self.state_manager.update_band_position(
                        quantity=pos['quantity'],
                        avg_cost=pos['avg_cost'],
                        direction="BUY"
                    )
                    
            # 执行日终结算
            self.state_manager.daily_settlement()
            
            # 执行波段策略检查
            if self.config.band_strategy_enabled:
                signal = self.band_strategy.check_signals()
                if signal:
                    if self.risk_engine.check_signal(signal):
                        self._execute_signal(signal)
                        
            Logger.info("日终对账完成")
            
        except Exception as e:
            Logger.exception(f"日终对账异常: {e}")
            
    def _auto_save(self):
        """自动保存状态"""
        try:
            self.state_manager.save_state()
            Logger.debug("状态已自动保存")
        except Exception as e:
            Logger.error(f"自动保存失败: {e}")
            
    # ==================== 属性 ====================
    
    @property
    def status(self) -> str:
        """获取系统状态"""
        return self._status
        
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

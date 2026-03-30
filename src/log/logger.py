"""
日志模块
使用 loguru 库进行日志记录
"""

import sys
from pathlib import Path
from loguru import logger


class Logger:
    """日志管理类"""
    
    _initialized = False
    
    @classmethod
    def init(cls, log_dir: Path, log_level: str = "INFO", 
             rotation: str = "00:00", retention: str = "30 days",
             format_str: str = None):
        """
        初始化日志系统
        
        Args:
            log_dir: 日志目录
            log_level: 日志级别
            rotation: 日志分割时间
            retention: 日志保留时间
            format_str: 日志格式
        """
        if cls._initialized:
            return
            
        # 创建日志目录
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 移除默认处理器
        logger.remove()
        
        # 默认格式
        if format_str is None:
            format_str = (
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} - {message}"
            )
        
        # 添加控制台输出
        logger.add(
            sys.stdout,
            level=log_level,
            format=format_str,
            colorize=True
        )
        
        # 添加交易日志文件
        logger.add(
            log_dir / "trade_{time}.log",
            level="INFO",
            format=format_str,
            rotation=rotation,
            retention=retention,
            encoding="utf-8"
        )
        
        # 添加错误日志文件
        logger.add(
            log_dir / "error_{time}.log",
            level="ERROR",
            format=format_str,
            rotation=rotation,
            retention=retention,
            encoding="utf-8"
        )
        
        cls._initialized = True
        
    @classmethod
    def debug(cls, message: str):
        """Debug级别日志"""
        logger.debug(message)
        
    @classmethod
    def info(cls, message: str):
        """Info级别日志"""
        logger.info(message)
        
    @classmethod
    def warning(cls, message: str):
        """Warning级别日志"""
        logger.warning(message)
        
    @classmethod
    def error(cls, message: str):
        """Error级别日志"""
        logger.error(message)
        
    @classmethod
    def exception(cls, message: str):
        """Exception级别日志（包含堆栈信息）"""
        logger.exception(message)
        
    @classmethod
    def critical(cls, message: str):
        """Critical级别日志"""
        logger.critical(message)
        
    # ==================== 交易专用日志 ====================
    
    @classmethod
    def log_signal(cls, signal_type: str, direction: str, 
                   stock_code: str, quantity: int, price: float, reason: str):
        """记录交易信号"""
        cls.info(
            f"交易信号 | 类型:{signal_type} | 方向:{direction} | "
            f"标的:{stock_code} | 数量:{quantity} | 价格:{price:.2f} | 原因:{reason}"
        )
        
    @classmethod
    def log_order(cls, order_id: str, direction: str, 
                  stock_code: str, quantity: int, price: float, status: str):
        """记录订单信息"""
        cls.info(
            f"订单信息 | ID:{order_id} | 方向:{direction} | "
            f"标的:{stock_code} | 数量:{quantity} | 价格:{price:.2f} | 状态:{status}"
        )
        
    @classmethod
    def log_order_filled(cls, order_id: str, filled_quantity: int, 
                        avg_price: float, profit: float = None):
        """记录订单成交"""
        msg = f"订单成交 | ID:{order_id} | 成交数量:{filled_quantity} | 成交均价:{avg_price:.2f}"
        if profit is not None:
            msg += f" | 收益:{profit:.2f}"
        cls.info(msg)
        
    @classmethod
    def log_order_cancelled(cls, order_id: str, reason: str = ""):
        """记录订单撤单"""
        cls.info(f"订单撤单 | ID:{order_id} | 原因:{reason}")
        
    @classmethod
    def log_order_rejected(cls, order_id: str, reason: str):
        """记录订单拒绝"""
        cls.warning(f"订单拒绝 | ID:{order_id} | 原因:{reason}")
        
    @classmethod
    def log_risk_block(cls, check_type: str, reason: str):
        """记录风控拦截"""
        cls.warning(f"风控拦截 | 类型:{check_type} | 原因:{reason}")
        
    @classmethod
    def log_circuit_triggered(cls, circuit_type: str, reason: str):
        """记录熔断触发"""
        cls.warning(f"熔断触发 | 类型:{circuit_type} | 原因:{reason}")
        
    @classmethod
    def log_position(cls, position_type: str, quantity: int, 
                    avg_cost: float, profit: float = None):
        """记录持仓信息"""
        msg = f"持仓更新 | 类型:{position_type} | 数量:{quantity} | 成本:{avg_cost:.2f}"
        if profit is not None:
            msg += f" | 盈亏:{profit:.2f}"
        cls.info(msg)
        
    @classmethod
    def log_market_data(cls, stock_code: str, price: float, 
                       change_pct: float, vwap: float = None):
        """记录行情数据"""
        msg = f"行情数据 | 标的:{stock_code} | 价格:{price:.2f} | 涨跌:{change_pct*100:.2f}%"
        if vwap is not None:
            msg += f" | VWAP:{vwap:.2f}"
        cls.debug(msg)


# 导出便捷方法
debug = Logger.debug
info = Logger.info
warning = Logger.warning
error = Logger.error
exception = Logger.exception
critical = Logger.critical

log_signal = Logger.log_signal
log_order = Logger.log_order
log_order_filled = Logger.log_order_filled
log_order_cancelled = Logger.log_order_cancelled
log_order_rejected = Logger.log_order_rejected
log_risk_block = Logger.log_risk_block
log_circuit_triggered = Logger.log_circuit_triggered
log_position = Logger.log_position
log_market_data = Logger.log_market_data

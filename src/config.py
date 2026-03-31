"""
配置管理模块
负责加载和解析 config.yml 配置文件
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径，默认为项目根目录下的 config.yml
        """
        # 获取项目根目录
        self.base_dir = Path(__file__).parent.parent
        
        # 设置配置文件路径
        if config_path is None:
            self.config_path = self.base_dir / "config.yml"
        else:
            self.config_path = Path(config_path)
        
        # 加载配置
        self._config: Dict[str, Any] = {}
        self._load_config()
        
        # 设置日志目录
        self._setup_logging()
        
    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
            
    def _setup_logging(self):
        """设置日志目录"""
        log_dir = self.base_dir / self._config.get('logging', {}).get('dir', 'logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        
    # ==================== 标的配置 ====================
    @property
    def stock_code(self) -> str:
        """股票代码"""
        return self._config.get('stock', {}).get('code', '300124')
    
    @property
    def stock_name(self) -> str:
        """股票名称"""
        return self._config.get('stock', {}).get('name', '汇川技术')
    
    # ==================== 资金配置 ====================
    @property
    def total_capital(self) -> float:
        """总资金"""
        return float(self._config.get('capital', {}).get('total', 200000))
    
    @property
    def band_position_ratio(self) -> float:
        """波段底仓比例"""
        return float(self._config.get('capital', {}).get('band_position_ratio', 0.6))
    
    @property
    def t_position_fund(self) -> float:
        """做T资金池"""
        return float(self._config.get('capital', {}).get('t_position_fund', 20000))
    
    @property
    def reserve_ratio(self) -> float:
        """预留资金比例"""
        return float(self._config.get('capital', {}).get('reserve_ratio', 0.3))
    
    # ==================== QMT配置 ====================
    @property
    def qmt_account(self) -> str:
        """QMT账号"""
        return self._config.get('qmt', {}).get('account', '')
    
    @property
    def qmt_password(self) -> str:
        """QMT密码（优先从环境变量读取）"""
        # 优先从环境变量读取
        env_password = os.environ.get('QMT_PASSWORD')
        if env_password:
            return env_password
        # 回退到配置文件
        return self._config.get('qmt', {}).get('password', '')
    
    @property
    def qmt_host(self) -> str:
        """QMT服务地址"""
        return self._config.get('qmt', {}).get('host', '127.0.0.1')
    
    @property
    def qmt_port(self) -> int:
        """QMT服务端口"""
        return int(self._config.get('qmt', {}).get('port', 5910))
    
    @property
    def qmt_timeout(self) -> int:
        """QMT超时时间"""
        return int(self._config.get('qmt', {}).get('timeout', 30))
    
    @property
    def qmt_max_retries(self) -> int:
        """QMT最大重试次数"""
        return int(self._config.get('qmt', {}).get('retry', {}).get('max_attempts', 3))
    
    @property
    def qmt_retry_interval(self) -> int:
        """QMT重试间隔"""
        return int(self._config.get('qmt', {}).get('retry', {}).get('interval_seconds', 5))
    
    @property
    def qmt_path(self) -> str:
        """QMT路径"""
        return self._config.get('qmt', {}).get('path', '')
    
    @property
    def session_id(self) -> int:
        """QMT会话ID"""
        return int(self._config.get('qmt', {}).get('session_id', 123456))
    
    # ==================== 交易时间段 ====================
    @property
    def trading_morning_start(self) -> str:
        """上午交易开始时间"""
        return self._config.get('trading', {}).get('morning_start', '09:30')
    
    @property
    def trading_morning_end(self) -> str:
        """上午交易结束时间"""
        return self._config.get('trading', {}).get('morning_end', '11:30')
    
    @property
    def trading_afternoon_start(self) -> str:
        """下午交易开始时间"""
        return self._config.get('trading', {}).get('afternoon_start', '13:00')
    
    @property
    def trading_afternoon_end(self) -> str:
        """下午交易结束时间（开仓截止）"""
        return self._config.get('trading', {}).get('afternoon_end', '14:55')
    
    @property
    def trading_day_end(self) -> str:
        """交易日结束时间"""
        return self._config.get('trading', {}).get('day_end', '15:00')
    
    # ==================== 做T策略参数 ====================
    @property
    def t_strategy_enabled(self) -> bool:
        """做T策略是否启用"""
        return self._config.get('t_strategy', {}).get('enabled', True)
    
    @property
    def t_max_fund(self) -> float:
        """做T最大资金"""
        return float(self._config.get('t_strategy', {}).get('max_fund', 20000))
    
    @property
    def t_max_ratio(self) -> float:
        """做T最大比例"""
        return float(self._config.get('t_strategy', {}).get('max_ratio', 0.3))
    
    @property
    def t_trigger_drop(self) -> float:
        """做多T买入触发跌幅"""
        return float(self._config.get('t_strategy', {}).get('trigger_drop', 0.02))
    
    @property
    def t_trigger_deviation(self) -> float:
        """做多T买入触发偏离"""
        return float(self._config.get('t_strategy', {}).get('trigger_deviation', 0.003))
    
    @property
    def t_profit_target(self) -> float:
        """做T止盈比例"""
        return float(self._config.get('t_strategy', {}).get('profit_target', 0.005))
    
    @property
    def t_loss_stop(self) -> float:
        """做T止损比例"""
        return float(self._config.get('t_strategy', {}).get('loss_stop', 0.01))
    
    @property
    def t_max_single_quantity(self) -> int:
        """单次做空T最大数量"""
        return int(self._config.get('t_strategy', {}).get('max_single_quantity', 1000))
    
    @property
    def t_min_position(self) -> int:
        """最低持仓要求"""
        return int(self._config.get('t_strategy', {}).get('min_position', 100))
    
    @property
    def t_min_fund(self) -> float:
        """最低资金要求"""
        return float(self._config.get('t_strategy', {}).get('min_fund', 1000))
    
    @property
    def t_vwap_flat_slope(self) -> float:
        """分时均线走平斜率阈值"""
        return float(self._config.get('t_strategy', {}).get('vwap_flat_slope', 0.001))
    
    @property
    def t_vwap_flat_change_rate(self) -> float:
        """分时均线走平变化率阈值"""
        return float(self._config.get('t_strategy', {}).get('vwap_flat_change_rate', 0.001))
    
    @property
    def t_amplitude_limit(self) -> float:
        """5分钟振幅限制"""
        return float(self._config.get('t_strategy', {}).get('amplitude_limit', 0.01))
    
    @property
    def t_amplitude_duration(self) -> int:
        """波动率限制持续时间（分钟）"""
        return int(self._config.get('t_strategy', {}).get('amplitude_duration', 30))
    
    # ==================== 波段策略参数 ====================
    @property
    def band_strategy_enabled(self) -> bool:
        """波段策略是否启用"""
        return self._config.get('band_strategy', {}).get('enabled', True)
    
    @property
    def band_initial_ratio(self) -> float:
        """波段初始建仓比例"""
        return float(self._config.get('band_strategy', {}).get('initial_ratio', 0.6))
    
    @property
    def band_max_ratio(self) -> float:
        """波段最大仓位"""
        return float(self._config.get('band_strategy', {}).get('max_ratio', 0.8))
    
    @property
    def band_min_ratio(self) -> float:
        """波段最小仓位"""
        return float(self._config.get('band_strategy', {}).get('min_ratio', 0.3))
    
    @property
    def band_profit_target(self) -> float:
        """波段止盈目标"""
        return float(self._config.get('band_strategy', {}).get('profit_target', 0.15))
    
    @property
    def band_stop_loss_fixed(self) -> float:
        """波段固定止损"""
        return float(self._config.get('band_strategy', {}).get('stop_loss_fixed', 0.05))
    
    # ==================== 风控参数 ====================
    @property
    def risk_market_drop_limit(self) -> float:
        """大盘跌幅限制"""
        return float(self._config.get('risk', {}).get('market_drop_limit', 0.05))
    
    @property
    def risk_sector_drop_limit(self) -> float:
        """板块跌幅限制"""
        return float(self._config.get('risk', {}).get('sector_drop_limit', 0.06))
    
    @property
    def risk_t_continuous_loss_limit(self) -> int:
        """做T连续亏损熔断次数"""
        return int(self._config.get('risk', {}).get('t_continuous_loss_limit', 3))
    
    @property
    def risk_t_circuit_duration(self) -> int:
        """做T熔断持续天数"""
        return int(self._config.get('risk', {}).get('t_circuit_duration', 1))
    
    @property
    def risk_band_continuous_loss_limit(self) -> int:
        """波段连续亏损熔断次数"""
        return int(self._config.get('risk', {}).get('band_continuous_loss_limit', 2))
    
    @property
    def risk_band_circuit_duration(self) -> int:
        """波段熔断持续天数"""
        return int(self._config.get('risk', {}).get('band_circuit_duration', 3))
    
    @property
    def risk_band_volatility_limit(self) -> float:
        """20日波动率限制"""
        return float(self._config.get('risk', {}).get('band_volatility_limit', 0.02))
    
    # ==================== 日志配置 ====================
    @property
    def log_level(self) -> str:
        """日志级别"""
        return self._config.get('logging', {}).get('level', 'INFO')
    
    @property
    def log_dir(self) -> Path:
        """日志目录"""
        return self.base_dir / self._config.get('logging', {}).get('dir', 'logs')
    
    @property
    def log_rotation(self) -> str:
        """日志分割时间"""
        return self._config.get('logging', {}).get('rotation', '00:00')
    
    @property
    def log_retention(self) -> str:
        """日志保留时间"""
        return self._config.get('logging', {}).get('retention', '30 days')
    
    # ==================== 状态持久化配置 ====================
    @property
    def state_dir(self) -> Path:
        """状态文件目录"""
        return self.base_dir / self._config.get('state', {}).get('dir', 'data')
    
    @property
    def state_file(self) -> Path:
        """状态文件路径"""
        return self.state_dir / self._config.get('state', {}).get('file', 'state.json')
    
    @property
    def state_auto_save_interval(self) -> int:
        """状态自动保存间隔（秒）"""
        return int(self._config.get('state', {}).get('auto_save_interval', 60))
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._config.get(key, default)

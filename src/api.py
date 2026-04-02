"""
API 服务模块
为前端提供 HTTP API 接口，获取真实市场数据

使用 FastAPI 构建，支持：
- 实时行情查询
- 历史分时数据查询
- 交易信号查询
- 股票基本信息查询

启动方式：
    python -m uvicorn src.api:app --reload --port 8080

或运行 api_server.py 脚本
"""

import sys
import os
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 检测数据源可用性
# GM API (掘金)
_GM_AVAILABLE = False
_GM_ERROR = ""

try:
    from gm.api import set_serv_addr, set_token
    _GM_AVAILABLE = True
except ImportError as e:
    _GM_ERROR = str(e)
    print(f"⚠️ gm.api 导入失败: {e}")

# xtquant (QMT)
_XTQUANT_AVAILABLE = False
_XTQUANT_ERROR = ""

try:
    import xtquant
    _XTQUANT_AVAILABLE = True
except ImportError as e:
    _XTQUANT_ERROR = str(e)
    print(f"⚠️ xtquant 导入失败: {e}")
    print(f"⚠️ Python 版本可能不兼容，API 将以模拟模式运行")

# 导入配置和数据模块
try:
    from src.config import Config
    from src.market_data import MarketModule, QuoteData, VWAPData, MinuteData
    from src.executor.qmt_executor import QMTExecutor, format_stock_code
    from src.strategy.signal import SignalType
    from src.state.state_manager import StateManager
    from src.log.logger import Logger
except ImportError as e:
    print(f"导入模块失败: {e}")
    # 如果导入失败，提供降级的 API 服务
    Config = None
    MarketModule = None
    QMTExecutor = None
    format_stock_code = None
    Logger = None


# ==================== 数据模型 ====================

class StockInfo(BaseModel):
    """股票信息响应"""
    code: str
    name: str
    price: float
    change: float
    changePercent: float


class MinuteBar(BaseModel):
    """分时K线"""
    time: str
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    price: float = 0.0
    volume: int = 0
    amount: float = 0.0
    vwap: float = 0.0


class Signal(BaseModel):
    """交易信号"""
    time: str
    type: str
    price: float
    reason: str


class RealtimeResponse(BaseModel):
    """实时行情响应"""
    code: str
    name: str
    price: float
    change: float
    changePercent: float
    time: str
    volume: int
    data: List[MinuteBar] = []


class HistoryResponse(BaseModel):
    """历史数据响应"""
    code: str
    date: str
    data: List[MinuteBar] = []
    signals: List[Signal] = []


class SignalsResponse(BaseModel):
    """交易信号响应"""
    code: str
    signals: List[Signal]


class StockResponse(BaseModel):
    """股票信息响应"""
    code: str
    name: str
    price: float
    change: float
    changePercent: float


class AccountResponse(BaseModel):
    """资金账户响应"""
    available: float = 0.0
    total: float = 0.0
    market_value: float = 0.0
    frozen: float = 0.0
    connected: bool = False
    message: str = ""


class PositionResponse(BaseModel):
    """持仓响应"""
    positions: Dict[str, Dict[str, Any]] = {}
    connected: bool = False
    message: str = ""


# ==================== 全局变量 ====================

app = FastAPI(
    title="ETF T Quant API",
    description="ETF T策略量化交易系统 API 服务",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局对象
_config: Optional[Config] = None
_qmt_executor: Optional[QMTExecutor] = None
_gm_executor = None  # GM 执行器
_market_module: Optional[MarketModule] = None
_state_manager: Optional[StateManager] = None
_data_source: str = "gm"  # 默认使用 GM


# ==================== 模拟数据（降级模式） ====================

def get_mock_quote(code: str) -> QuoteData:
    """当无法获取真实行情时，返回模拟数据"""
    import random
    # 基于股票代码生成一个稳定的"模拟价格"
    base_price = 10.0 + (hash(code) % 100)  # 10-110 之间的稳定价格
    
    quote = QuoteData()
    quote.stock_code = code
    quote.last_price = base_price
    quote.open = base_price * 0.99
    quote.high = base_price * 1.02
    quote.low = base_price * 0.98
    quote.volume = 1000000
    quote.amount = base_price * 1000000
    quote.change = 0
    quote.change_pct = 0
    quote.update_time = datetime.now().strftime("%H:%M:%S")
    
    Logger.warning(f"使用模拟行情数据 | 标的:{code} | 价格:{base_price} (GM/QMT不可用)")
    
    return quote


def get_mock_minute_data(code: str) -> List[MinuteBar]:
    """生成模拟分时数据"""
    from datetime import datetime, timedelta
    
    minute_data = []
    base_time = datetime.now().replace(hour=9, minute=30, second=0)
    base_price = 20.0 + (hash(code) % 50)  # 基础价格
    
    for i in range(240):  # 全天约240分钟
        minute_time = base_time + timedelta(minutes=i)
        if minute_time.hour >= 11 and minute_time.hour < 13:
            continue  # 跳过午休
        if minute_time.hour >= 15:
            break
            
        # 模拟价格波动
        price = base_price + random.uniform(-0.5, 0.5)
        minute_data.append(MinuteBar(
            time=minute_time.strftime("%H:%M:%S"),
            price=round(price, 2),
            volume=random.randint(1000, 10000),
            vwap=price
        ))
    
    return minute_data


# ==================== 依赖注入 ====================

async def get_data_connection():
    """获取数据连接（支持 GM 和 QMT）"""
    global _qmt_executor, _gm_executor, _market_module, _state_manager, _config, _data_source
    
    if _config is None:
        try:
            _config = Config()
            _data_source = _config.data_source if hasattr(_config, 'data_source') else 'gm'
            print(f"📊 数据源配置: {_data_source}")
        except Exception as e:
            print(f"配置加载失败: {e}")
            _config = None
            _data_source = 'gm'
    
    # 根据数据源初始化对应的执行器
    if _data_source == 'gm' and _GM_AVAILABLE:
        # 使用 GM API 获取行情
        if _gm_executor is None:
            from src.executor.gm_executor import GMExecutor
            _gm_executor = GMExecutor(_config)
            if not _gm_executor.setup():
                # GM 连接失败，切换为模拟数据
                print(f"⚠️ GM 连接失败，将使用模拟数据")
                _gm_executor = None
                _data_source = 'mock'
            else:
                print(f"✅ GM 数据执行器已初始化")
        
        # 初始化行情模块，使用 GM 执行器
        if _market_module is None and _config:
            try:
                _market_module = MarketModule(_config, _gm_executor, executor_type='gm')
            except Exception as e:
                print(f"行情模块初始化失败: {e}")
                _market_module = None
                
    elif _XTQUANT_AVAILABLE:
        # 使用 QMT 获取行情
        if _qmt_executor is None:
            _qmt_executor = QMTExecutor(_config)
            try:
                _qmt_executor.start()
                if _qmt_executor.is_connected():
                    print(f"✅ QMT 数据执行器已连接")
            except Exception as e:
                print(f"QMT 启动失败: {e}")
                _qmt_executor = None
        
        # 初始化行情模块，使用 QMT 执行器
        if _market_module is None and _config:
            try:
                _market_module = MarketModule(_config, _qmt_executor, executor_type='qmt')
            except Exception as e:
                print(f"行情模块初始化失败: {e}")
                _market_module = None
    else:
        # GM 和 QMT 都不可用，使用模拟数据
        print(f"⚠️ GM 和 QMT 都不可用，将使用模拟数据")
        _data_source = 'mock'
    
    # 初始化状态管理器
    if _state_manager is None and _config:
        try:
            _state_manager = StateManager(_config)
            _state_manager.load()
        except Exception as e:
            print(f"状态加载失败: {e}")
            _state_manager = None
    
    # 返回合适的 executor（如果 GM/QMT 都不可用，返回 None）
    active_executor = _gm_executor if _data_source == 'gm' else _qmt_executor
    
    return active_executor, _market_module, _state_manager, _config


# ==================== API 路由 ====================

@app.get("/")
async def root():
    """API 根路径"""
    return {
        "service": "ETF T Quant API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "data_source": _data_source,
        "gm_available": _GM_AVAILABLE,
        "gm_connected": _gm_executor.is_connected() if _gm_executor else False,
        "qmt_connected": _qmt_executor.is_connected() if _qmt_executor else False,
        "xtquant_available": _XTQUANT_AVAILABLE,
        "xtquant_error": _XTQUANT_ERROR,
        "python_version": sys.version
    }


@app.get("/api/realtime", response_model=RealtimeResponse)
async def get_realtime(
    code: str = Query(..., description="股票代码，如 300124"),
    data_tuple = Depends(get_data_connection)
):
    """
    获取实时行情和分时数据
    
    Args:
        code: 股票代码
        
    Returns:
        实时行情数据包含分时K线
    """
    data_executor, market_module, state_manager, config = data_tuple
    
    try:
        # 格式化股票代码 (如 300124 -> SZ.300124)
        # 根据数据源选择格式化方式
        if _data_source == 'gm':
            from src.executor.gm_executor import format_gm_symbol
            qmt_code = format_gm_symbol(code)
        else:
            qmt_code = format_stock_code(code) if format_stock_code else code
        
        # 获取实时行情
        quote = None
        if market_module:
            try:
                quote = market_module.get_quote(qmt_code)
            except Exception as e:
                print(f"获取实时行情失败: {e}")
        
        if not quote:
            # 尝试直接通过 executor 获取
            if data_executor:
                try:
                    quote_dict = data_executor.get_quote(qmt_code)
                    if quote_dict:
                        from src.market_data import QuoteData
                        quote = QuoteData()
                        quote.stock_code = quote_dict.get('stock_code', code)
                        quote.last_price = float(quote_dict.get('last_price', 0))
                        quote.open = float(quote_dict.get('open', 0))
                        quote.high = float(quote_dict.get('high', 0))
                        quote.low = float(quote_dict.get('low', 0))
                        quote.volume = int(quote_dict.get('volume', 0))
                        quote.amount = float(quote_dict.get('amount', 0))
                        quote.change = float(quote_dict.get('change', 0))
                        quote.change_pct = float(quote_dict.get('change_pct', 0))
                        quote.update_time = quote_dict.get('update_time', '')
                except Exception as e:
                    print(f"直接获取行情失败: {e}")
        
        # 如果仍然无法获取真实行情，使用模拟数据（降级模式）
        if not quote:
            Logger.warning(f"无法获取真实行情，启用降级模式 | 标的:{code}")
            quote = get_mock_quote(code)
        
        # 获取分时数据
        minute_data = []
        if market_module and data_executor:
            # 通过 market_module 或 executor 获取分时数据
            today = datetime.now().strftime("%Y%m%d")
            try:
                minute_list = data_executor.get_minute_data(qmt_code, today)
                for m in minute_list:
                    minute_data.append(MinuteBar(
                        time=m.get('time', ''),
                        price=float(m.get('price', 0)),
                        volume=int(m.get('volume', 0)),
                        vwap=0.0  # 可后续计算 VWAP
                    ))
            except Exception as e:
                print(f"获取分时数据失败: {e}")
        
        # 如果分时数据为空，也使用模拟数据
        if not minute_data:
            minute_data = get_mock_minute_data(code)
        
        # 获取股票名称
        stock_name = code
        if config and hasattr(config, 'stock_name') and code == config.stock_code:
            stock_name = config.stock_name
        
        return RealtimeResponse(
            code=code,
            name=stock_name,
            price=quote.last_price,
            change=quote.change,
            changePercent=quote.change_pct,
            time=quote.update_time,
            volume=quote.volume,
            data=minute_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # 增加调试信息
        error_detail = f"获取实时数据失败: {str(e)}"
        debug_info = {
            "xtquant_available": _XTQUANT_AVAILABLE,
            "xtquant_error": _XTQUANT_ERROR,
            "qmt_connected": _qmt_executor.is_connected() if _qmt_executor else False,
            "requested_code": code
        }
        print(f"❌ API错误: {error_detail}")
        print(f"🔧 调试信息: {debug_info}")
        raise HTTPException(status_code=503, detail=error_detail)


@app.get("/api/history", response_model=HistoryResponse)
async def get_history(
    code: str = Query(..., description="股票代码，如 300124"),
    date: str = Query(..., description="日期，格式 YYYY-MM-DD，如 2026-03-31"),
    data_tuple = Depends(get_data_connection)
):
    """
    获取历史分时数据
    
    Args:
        code: 股票代码
        date: 日期
        
    Returns:
        历史分时数据和信号
    """
    qmt, market_module, state_manager, config = data_tuple
    
    # 格式化股票代码 (如 300124 -> SZ.300124)
    qmt_code = format_stock_code(code) if format_stock_code else code

    # 转换日期格式
    date_str = date.replace("-", "")

    # 获取分时数据：真实异常返回5xx；无数据仅告警
    minute_data = []
    if qmt:
        try:
            minute_list = qmt.get_minute_data(qmt_code, date_str)
        except Exception as e:
            if Logger:
                Logger.error(f"获取历史分时数据异常 | code={qmt_code} | date={date_str} | err={e}")
            raise HTTPException(status_code=502, detail=f"获取历史分时数据失败: {str(e)}")

        if not minute_list:
            if Logger:
                Logger.warning(f"历史分时数据为空 | code={qmt_code} | date={date_str}")
        else:
            # 生成策略信号和模拟交易
            signals = generate_signals(minute_list, code)
            
            for m in minute_list:
                minute_data.append(MinuteBar(
                    time=m.get('time', ''),
                    open=m.get('open', 0),
                    high=m.get('high', 0),
                    low=m.get('low', 0),
                    close=m.get('close', 0),
                    price=m.get('close', 0),
                    volume=m.get('volume', 0),
                    amount=m.get('amount', 0),
                    vwap=m.get('vwap', 0.0)
                ))

    # 获取交易信号：异常返回5xx，避免吞错
    signals = []
    if state_manager:
        try:
            state = state_manager.get_state()
            trade_history = state.get('trade_history', [])

            for trade in trade_history:
                trade_date = trade.get('date', '')[:8]
                if trade_date == date_str:
                    signals.append(Signal(
                        time=trade.get('time', ''),
                        type=trade.get('signal_type', ''),
                        price=float(trade.get('price', 0)),
                        reason=trade.get('reason', '')
                    ))
        except Exception as e:
            if Logger:
                Logger.error(f"获取历史信号异常 | code={qmt_code} | date={date_str} | err={e}")
            raise HTTPException(status_code=500, detail=f"获取历史信号失败: {str(e)}")

    return HistoryResponse(
        code=code,
        date=date,
        data=minute_data,
        signals=signals
    )


@app.get("/api/signals", response_model=SignalsResponse)
async def get_signals(
    code: str = Query(..., description="股票代码，如 300124"),
    data_tuple = Depends(get_data_connection)
):
    """
    获取交易信号
    
    Args:
        code: 股票代码
        
    Returns:
        交易信号列表
    """
    qmt, market_module, state_manager, config = data_tuple
    
    try:
        signals = []
        
        if state_manager:
            try:
                state = state_manager.get_state()
                trade_history = state.get('trade_history', [])
                
                # 获取最近的信号
                for trade in trade_history[-20:]:  # 最近20条
                    if trade.get('stock_code') == code:
                        signals.append(Signal(
                            time=trade.get('time', ''),
                            type=trade.get('signal_type', ''),
                            price=float(trade.get('price', 0)),
                            reason=trade.get('reason', '')
                        ))
            except Exception as e:
                print(f"获取交易信号失败: {e}")
        
        return SignalsResponse(
            code=code,
            signals=signals
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取信号失败: {str(e)}")


@app.get("/api/stock", response_model=StockResponse)
async def get_stock(
    code: str = Query(..., description="股票代码，如 300124"),
    data_tuple = Depends(get_data_connection)
):
    """
    获取股票基本信息
    
    Args:
        code: 股票代码
        
    Returns:
        股票基本信息
    """
    data_executor, market_module, state_manager, config = data_tuple
    
    try:
        # 格式化股票代码 (如 300124 -> SZ.300124)
        # 根据数据源选择格式化方式
        if _data_source == 'gm':
            from src.executor.gm_executor import format_gm_symbol
            qmt_code = format_gm_symbol(code)
        else:
            qmt_code = format_stock_code(code) if format_stock_code else code
        
        # 获取实时行情
        quote = market_module.get_quote(qmt_code) if market_module else None
        
        if not quote:
            raise HTTPException(status_code=404, detail=f"无法获取股票 {code} 的信息")
        
        # 获取股票名称
        stock_name = config.stock_name if code == config.stock_code else code
        
        return StockResponse(
            code=code,
            name=stock_name,
            price=quote.last_price,
            change=quote.change,
            changePercent=quote.change_pct
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票信息失败: {str(e)}")


class DatesResponse(BaseModel):
    """可用日期列表响应"""
    code: int = 0
    message: str = "success"
    data: List[str] = []


@app.get("/api/dates", response_model=DatesResponse)
async def get_dates(
    code: str = Query(..., description="股票代码，如 300124"),
    data_tuple = Depends(get_data_connection)
):
    """
    获取可回测的交易日列表
    
    Args:
        code: 股票代码
        
    Returns:
        最近30个交易日的日期列表
    """
    qmt, market_module, state_manager, config = data_tuple
    
    try:
        # 格式化股票代码
        qmt_code = format_stock_code(code) if format_stock_code else code
        
        # 获取最近30个交易日
        trading_dates = []
        
        if qmt:
            try:
                # 计算日期范围
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=45)  # 多获取一些日期，过滤周末
                
                # 获取K线数据来获取交易日
                kline_list = qmt.get_kline(
                    qmt_code,
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d")
                )
                
                if kline_list:
                    # 提取日期并转换为 YYYY-MM-DD 格式
                    for k in kline_list:
                        date_str = k.get('date', '')
                        if date_str:
                            # 转换为 YYYY-MM-DD 格式
                            if len(date_str) == 8:
                                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                                trading_dates.append(formatted_date)
                    
                    # 取最近30个
                    trading_dates = trading_dates[:30]
                    
            except Exception as e:
                print(f"获取交易日失败: {e}")
        
        # 如果没有获取到日期，使用本地计算的默认日期
        if not trading_dates:
            from datetime import datetime, timedelta
            today = datetime.now()
            for i in range(30):
                d = today - timedelta(days=i)
                day = d.weekday()
                if day < 5:  # 排除周末
                    trading_dates.append(d.strftime("%Y-%m-%d"))
        
        return DatesResponse(
            code=0,
            message="success",
            data=trading_dates
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取交易日失败: {str(e)}")


@app.get("/api/account", response_model=AccountResponse)
async def get_account():
    """
    获取资金账户信息
    """
    if not _qmt_executor or not _qmt_executor.is_connected():
        return AccountResponse(
            available=0,
            total=0,
            market_value=0,
            frozen=0,
            connected=False,
            message="QMT未连接"
        )
    
    try:
        account_info = _qmt_executor.get_account()
        
        if account_info:
            return AccountResponse(
                available=account_info.get('available', 0),
                total=account_info.get('total', 0),
                market_value=account_info.get('market_value', 0),
                frozen=account_info.get('frozen', 0),
                connected=True,
                message="查询成功"
            )
        else:
            return AccountResponse(
                available=0,
                total=0,
                market_value=0,
                frozen=0,
                connected=True,
                message="无法获取账户信息"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取账户信息失败: {str(e)}")


@app.get("/api/position", response_model=PositionResponse)
async def get_position(code: Optional[str] = Query(None, description="股票代码")):
    """
    获取持仓信息
    """
    if not _qmt_executor or not _qmt_executor.is_connected():
        return PositionResponse(
            positions={},
            connected=False,
            message="QMT未连接"
        )
    
    try:
        positions = _qmt_executor.get_position(code)
        
        return PositionResponse(
            positions=positions,
            connected=True,
            message=f"查询成功，共{len(positions)}只股票"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取持仓失败: {str(e)}")


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

# ==================== 回测策略信号生成 ====================

def generate_signals(minute_data: List[Dict], code: str) -> List[Signal]:
    """
    根据分时数据生成做T策略信号
    
    策略逻辑：
    - 初始化虚拟账户（100万资金，1万股持仓）
    - 计算累计均价（VWAP）
    - 当价格偏离均价超过阈值时触发交易
    - 每天做T要求正收益，亏钱要惩罚
    
    Args:
        minute_data: 分时数据列表
        code: 股票代码
        
    Returns:
        信号列表
    """
    signals = []
    
    if not minute_data or len(minute_data) == 0:
        return signals
    
    # 初始化虚拟账户
    virtual_cash = 1000000.0  # 100万资金
    virtual_shares = 10000    # 1万股持仓
    
    # 策略参数
    buy_threshold = -0.003   # 买入阈值：价格低于均价0.3%
    sell_threshold = 0.005   # 卖出阈值：价格高于均价0.5%
    stop_loss = 0.01          # 止损1%
    profit_target = 0.005     # 止盈0.5%
    
    # 跟踪数据
    cumulative_amount = 0.0
    cumulative_volume = 0
    avg_price = 0.0
    last_buy_price = 0.0
    last_buy_time = ""
    daily_profit = 0.0
    daily_trades = 0
    
    for i, minute in enumerate(minute_data):
        close = minute.get('close', 0)
        volume = minute.get('volume', 0)
        time_str = minute.get('time', '')
        
        if close <= 0 or volume <= 0:
            continue
        
        # 计算VWAP（累计均价）
        cumulative_amount += close * volume
        cumulative_volume += volume
        if cumulative_volume > 0:
            avg_price = cumulative_amount / cumulative_volume
        
        # 计算当前持仓市值
        current_value = virtual_cash + virtual_shares * close
        initial_value = 1000000.0 + 10000 * minute_data[0].get('close', close) if minute_data else current_value
        
        # 更新每日盈亏
        daily_profit = current_value - initial_value
        
        # 交易逻辑
        # 买入条件：价格低于均价且账户有资金
        if close < avg_price * (1 + buy_threshold) and virtual_cash >= close * 100:
            # 买入100股
            buy_volume = 100
            cost = close * buy_volume
            virtual_cash -= cost
            virtual_shares += buy_volume
            last_buy_price = close
            last_buy_time = time_str
            daily_trades += 1
            
            signals.append(Signal(
                time=time_str,
                type="buy",
                price=close,
                reason=f"买入 | 价格偏离均价{(close/avg_price-1)*100:.2f}%"
            ))
            
            if Logger:
                Logger.info(f"回测买入 | {time_str} | 价格:{close:.2f} | 数量:100")
        
        # 卖出条件：价格高于均价或止盈或止损
        elif virtual_shares >= 100:
            # 检查是否触发卖出
            should_sell = False
            reason = ""
            
            # 止盈
            if last_buy_price > 0 and close >= last_buy_price * (1 + profit_target):
                should_sell = True
                reason = f"止盈 | 涨幅{(close/last_buy_price-1)*100:.2f}%"
            
            # 止损
            elif last_buy_price > 0 and close <= last_buy_price * (1 - stop_loss):
                should_sell = True
                reason = f"止损 | 跌幅{(1-close/last_buy_price)*100:.2f}%"
            
            # 价格高于均价卖出
            elif close > avg_price * (1 + sell_threshold):
                should_sell = True
                reason = f"卖出 | 价格偏离均价{(close/avg_price-1)*100:.2f}%"
            
            if should_sell:
                sell_volume = 100
                income = close * sell_volume
                virtual_cash += income
                virtual_shares -= sell_volume
                daily_trades += 1
                
                # 计算这笔交易的盈亏
                trade_profit = income - last_buy_price * sell_volume
                
                signals.append(Signal(
                    time=time_str,
                    type="sell",
                    price=close,
                    reason=reason
                ))
                
                if Logger:
                    Logger.info(f"回测卖出 | {time_str} | 价格:{close:.2f} | 数量:100 | 盈亏:{trade_profit:.2f}")
                
                # 重置买入价格
                last_buy_price = 0
    
    # 每日结束总结
    if Logger:
        final_close = minute_data[-1].get('close', 0) if minute_data else 0
        final_value = virtual_cash + virtual_shares * final_close
        total_profit = final_value - (1000000.0 + 10000 * minute_data[0].get('close', final_close) if minute_data else 0)
        
        Logger.info(f"回测统计 | 日期 | 交易次数:{daily_trades} | 总盈亏:{total_profit:.2f}元 | 收益率:{total_profit/10000000*100:.2f}%")
    
    return signals

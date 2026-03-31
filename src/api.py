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
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置和数据模块
try:
    from src.config import Config
    from src.market_data import MarketModule, QuoteData, VWAPData, MinuteData
    from src.executor.qmt_executor import QMTExecutor
    from src.strategy.signal import SignalType
    from src.state.state_manager import StateManager
except ImportError as e:
    print(f"导入模块失败: {e}")
    # 如果导入失败，提供降级的 API 服务
    Config = None
    MarketModule = None
    QMTExecutor = None


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
    price: float
    volume: int
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
_market_module: Optional[MarketModule] = None
_state_manager: Optional[StateManager] = None


# ==================== 依赖注入 ====================

async def get_qmt_connection():
    """获取 QMT 连接"""
    global _qmt_executor, _market_module, _state_manager, _config
    
    if _qmt_executor is None:
        try:
            # 加载配置
            _config = Config()
            
            # 初始化 QMT 执行器
            _qmt_executor = QMTExecutor(_config)
            
            try:
                _qmt_executor.start()
            except Exception as e:
                print(f"QMT 启动失败: {e}，API 将返回离线数据")
            
            # 初始化行情模块
            _market_module = MarketModule(_config, _qmt_executor)
            
            # 初始化状态管理器
            _state_manager = StateManager(_config)
            try:
                _state_manager.load()
            except Exception as e:
                print(f"状态加载失败: {e}")
                
        except Exception as e:
            print(f"初始化失败: {e}")
    
    return _qmt_executor, _market_module, _state_manager, _config


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
        "qmt_connected": _qmt_executor.is_connected() if _qmt_executor else False
    }


@app.get("/api/realtime", response_model=RealtimeResponse)
async def get_realtime(
    code: str = Query(..., description="股票代码，如 300124"),
    qmt_tuple = Depends(get_qmt_connection)
):
    """
    获取实时行情和分时数据
    
    Args:
        code: 股票代码
        
    Returns:
        实时行情数据包含分时K线
    """
    qmt, market_module, state_manager, config = qmt_tuple
    
    try:
        # 获取实时行情
        quote = market_module.get_quote(code) if market_module else None
        
        if not quote:
            raise HTTPException(status_code=404, detail=f"无法获取股票 {code} 的行情数据")
        
        # 获取分时数据
        minute_data = []
        if market_module:
            # 通过 market_module 获取分时数据
            today = datetime.now().strftime("%Y%m%d")
            try:
                minute_list = qmt.get_minute_data(code, today) if qmt else []
                for m in minute_list:
                    minute_data.append(MinuteBar(
                        time=m.get('time', ''),
                        price=float(m.get('price', 0)),
                        volume=int(m.get('volume', 0)),
                        vwap=0.0  # 可后续计算 VWAP
                    ))
            except Exception as e:
                print(f"获取分时数据失败: {e}")
        
        # 获取股票名称
        stock_name = config.stock_name if code == config.stock_code else code
        
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
        raise HTTPException(status_code=500, detail=f"获取实时数据失败: {str(e)}")


@app.get("/api/history", response_model=HistoryResponse)
async def get_history(
    code: str = Query(..., description="股票代码，如 300124"),
    date: str = Query(..., description="日期，格式 YYYY-MM-DD，如 2026-03-31"),
    qmt_tuple = Depends(get_qmt_connection)
):
    """
    获取历史分时数据
    
    Args:
        code: 股票代码
        date: 日期
        
    Returns:
        历史分时数据和信号
    """
    qmt, market_module, state_manager, config = qmt_tuple
    
    try:
        # 转换日期格式
        date_str = date.replace("-", "")
        
        # 获取分时数据
        minute_data = []
        if qmt:
            try:
                minute_list = qmt.get_minute_data(code, date_str)
                for m in minute_list:
                    minute_data.append(MinuteBar(
                        time=m.get('time', ''),
                        price=float(m.get('price', 0)),
                        volume=int(m.get('volume', 0)),
                        vwap=0.0
                    ))
            except Exception as e:
                print(f"获取历史分时数据失败: {e}")
        
        # 获取交易信号
        signals = []
        if state_manager:
            try:
                # 从状态中获取历史信号
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
                print(f"获取交易信号失败: {e}")
        
        # 如果没有信号，尝试从 config 获取股票名称
        stock_name = config.stock_name if code == config.stock_code else code
        
        return HistoryResponse(
            code=code,
            date=date,
            data=minute_data,
            signals=signals
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史数据失败: {str(e)}")


@app.get("/api/signals", response_model=SignalsResponse)
async def get_signals(
    code: str = Query(..., description="股票代码，如 300124"),
    qmt_tuple = Depends(get_qmt_connection)
):
    """
    获取交易信号
    
    Args:
        code: 股票代码
        
    Returns:
        交易信号列表
    """
    qmt, market_module, state_manager, config = qmt_tuple
    
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
    qmt_tuple = Depends(get_qmt_connection)
):
    """
    获取股票基本信息
    
    Args:
        code: 股票代码
        
    Returns:
        股票基本信息
    """
    qmt, market_module, state_manager, config = qmt_tuple
    
    try:
        # 获取实时行情
        quote = market_module.get_quote(code) if market_module else None
        
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


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
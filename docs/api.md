# 接口说明文档

本文档详细介绍 ETF T 策略量化交易系统的各个接口。

---

## 目录

1. [配置接口](#配置接口)
2. [策略接口](#策略接口)
3. [交易接口](#交易接口)

---

## 配置接口

### Config 类

配置管理模块，负责加载和解析 `config.yml` 配置文件。

**位置**: `src/config.py`

#### 初始化

```python
config = Config(config_path=None)
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| config_path | str | 配置文件路径，默认为项目根目录的 config.yml |

#### 标的配置

| 属性 | 类型 | 说明 |
|------|------|------|
| `stock_code` | str | 股票代码 |
| `stock_name` | str | 股票名称 |

#### 资金配置

| 属性 | 类型 | 说明 |
|------|------|------|
| `total_capital` | float | 总资金（元） |
| `band_position_ratio` | float | 波段底仓比例 |
| `t_position_fund` | float | 做T资金池（元） |
| `reserve_ratio` | float | 预留资金比例 |

#### QMT 配置

| 属性 | 类型 | 说明 |
|------|------|------|
| `qmt_account` | str | QMT账号 |
| `qmt_password` | str | QMT密码 |
| `qmt_host` | str | QMT服务地址，默认 127.0.0.1 |
| `qmt_port` | int | QMT服务端口，默认 5910 |
| `qmt_timeout` | int | 超时时间（秒），默认 30 |
| `qmt_max_retries` | int | 最大重试次数，默认 3 |
| `qmt_retry_interval` | int | 重试间隔（秒），默认 5 |
| `qmt_path` | str | QMT安装路径 |
| `session_id` | int | Session ID，默认 123456 |

#### 交易时间段

| 属性 | 类型 | 说明 |
|------|------|------|
| `trading_morning_start` | str | 上午交易开始时间，默认 09:30 |
| `trading_morning_end` | str | 上午交易结束时间，默认 11:30 |
| `trading_afternoon_start` | str | 下午交易开始时间，默认 13:00 |
| `trading_afternoon_end` | str | 开仓截止时间，默认 14:55 |
| `trading_day_end` | str | 交易日结束时间，默认 15:00 |

#### 做T策略参数

| 属性 | 类型 | 说明 |
|------|------|------|
| `t_strategy_enabled` | bool | 做T策略是否启用 |
| `t_max_fund` | float | 做T最大资金 |
| `t_max_ratio` | float | 每次做T最大比例 |
| `t_trigger_drop` | float | 做多T买入触发跌幅 |
| `t_trigger_deviation` | float | 做多T买入触发偏离 |
| `t_profit_target` | float | 做T止盈比例 |
| `t_loss_stop` | float | 做T止损比例 |
| `t_max_single_quantity` | int | 单次做空T最大数量 |
| `t_min_position` | int | 最低持仓要求 |
| `t_min_fund` | float | 最低资金要求 |
| `t_vwap_flat_slope` | float | 分时均线走平斜率阈值 |
| `t_amplitude_limit` | float | 5分钟振幅限制 |
| `t_amplitude_duration` | int | 波动率限制持续时间 |

#### 波段策略参数

| 属性 | 类型 | 说明 |
|------|------|------|
| `band_strategy_enabled` | bool | 波段策略是否启用 |
| `band_initial_ratio` | float | 初始建仓比例 |
| `band_max_ratio` | float | 最大仓位 |
| `band_min_ratio` | float | 最小仓位 |
| `band_profit_target` | float | 波段止盈目标 |
| `band_stop_loss_fixed` | float | 波段固定止损 |

#### 风控参数

| 属性 | 类型 | 说明 |
|------|------|------|
| `risk_market_drop_limit` | float | 大盘跌幅限制 |
| `risk_sector_drop_limit` | float | 板块跌幅限制 |
| `risk_t_continuous_loss_limit` | int | 做T连续亏损熔断次数 |
| `risk_t_circuit_duration` | int | 做T熔断持续天数 |
| `risk_band_continuous_loss_limit` | int | 波段连续亏损熔断次数 |
| `risk_band_circuit_duration` | int | 波段熔断持续天数 |
| `risk_band_volatility_limit` | float | 20日波动率限制 |

#### 日志配置

| 属性 | 类型 | 说明 |
|------|------|------|
| `log_level` | str | 日志级别 |
| `log_dir` | Path | 日志目录 |
| `log_rotation` | str | 日志分割时间 |
| `log_retention` | str | 日志保留时间 |

#### 状态配置

| 属性 | 类型 | 说明 |
|------|------|------|
| `state_dir` | Path | 状态文件目录 |
| `state_file` | Path | 状态文件路径 |
| `state_auto_save_interval` | int | 自动保存间隔（秒） |

---

## 策略接口

### 信号定义

**位置**: `src/strategy/signal.py`

#### SignalType 枚举

```python
class SignalType(Enum):
    T_LONG_BUY = "T_LONG_BUY"      # 做多T买入
    T_LONG_SELL = "T_LONG_SELL"    # 做多T卖出
    T_SHORT_SELL = "T_SHORT_SELL"  # 做空T卖出
    T_SHORT_BUY = "T_SHORT_BUY"    # 做空T买回
    BAND_BUY = "BAND_BUY"          # 波段买入
    BAND_SELL = "BAND_SELL"        # 波段卖出
```

#### Direction 枚举

```python
class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"
```

#### OrderStatus 枚举

```python
class OrderStatus(Enum):
    PENDING = "pending"      # 待提交
    SUBMITTED = "submitted"  # 已提交
    PARTIAL = "partial"      # 部分成交
    FILLED = "filled"        # 全部成交
    CANCELLED = "cancelled"  # 已撤单
    REJECTED = "rejected"    # 已拒绝
    FAILED = "failed"        # 失败
```

#### TradingSignal 数据类

```python
@dataclass
class TradingSignal:
    signal_type: str         # 信号类型
    direction: str           # 交易方向 BUY/SELL
    stock_code: str          # 股票代码
    quantity: int            # 委托数量
    price: float             # 委托价格
    reason: str              # 触发原因
    is_open_position: bool   # 是否开仓（平仓=false）
```

#### Order 数据类

```python
@dataclass
class Order:
    order_id: str            # 订单ID
    stock_code: str          # 股票代码
    direction: str           # 交易方向
    price: float             # 委托价格
    quantity: int            # 委托数量
    filled_quantity: int     # 已成交数量
    status: str              # 订单状态
    order_type: str          # 订单类型
    submit_time: str         # 提交时间
    update_time: str         # 更新时间
    error_message: str       # 错误信息
    signal_type: str        # 对应信号类型
```

### TStrategy 类

做T策略模块，负责做多T和做空T的信号生成。

**位置**: `src/strategy/t_strategy.py`

#### 初始化

```python
ts = TStrategy(config, market, state_manager)
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| config | Config | 配置对象 |
| market | MarketModule | 行情模块 |
| state_manager | StateManager | 状态管理器 |

#### 方法

##### check_signals()

```python
signal = ts.check_signals(quote)
```

检查做T信号。

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| quote | QuoteData | 实时行情数据 |

**返回**: `Optional[TradingSignal]` - 交易信号，无信号返回 None

---

### BandStrategy 类

波段策略模块，负责趋势跟踪和仓位管理。

**位置**: `src/strategy/band_strategy.py`

#### 初始化

```python
bs = BandStrategy(config, market, state_manager)
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| config | Config | 配置对象 |
| market | MarketModule | 行情模块 |
| state_manager | StateManager | 状态管理器 |

#### 方法

##### check_signals()

```python
signal = bs.check_signals()
```

检查波段信号。

**返回**: `Optional[TradingSignal]` - 交易信号，无信号返回 None

---

## 交易接口

### QMTExecutor 类

QMT执行引擎，负责与QMT交互完成下单、撤单、持仓查询等操作。

**位置**: `src/executor/qmt_executor.py`

#### 初始化

```python
executor = QMTExecutor(config)
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| config | Config | 配置对象 |

#### 方法

##### connect()

```python
result = executor.connect()
```

连接QMT。

**返回**: `bool` - 连接是否成功

##### disconnect()

```python
executor.disconnect()
```

断开QMT连接。

##### is_connected()

```python
connected = executor.is_connected()
```

检查QMT是否连接。

**返回**: `bool` - 是否已连接

##### submit_order()

```python
order = executor.submit_order(signal)
```

提交订单。

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| signal | TradingSignal | 交易信号 |

**返回**: `Optional[Order]` - 订单对象，失败返回 None

##### cancel_order()

```python
result = executor.cancel_order(order_id)
```

撤单。

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| order_id | str | 订单ID |

**返回**: `bool` - 是否成功

##### cancel_all_pending()

```python
executor.cancel_all_pending()
```

撤销所有挂单。

##### get_position()

```python
positions = executor.get_position(stock_code)
```

查询持仓。

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| stock_code | str | 股票代码 |

**返回**: `Dict` - 持仓信息

##### get_account()

```python
account = executor.get_account()
```

查询账户信息。

**返回**: `Dict` - 账户信息

##### set_mock_mode()

```python
executor.set_mock_mode()
```

设置为模拟模式（不连接QMT，用于测试）。

##### register_callback()

```python
executor.register_callback(controller)
```

注册订单回调。

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| controller | MainController | 主控对象 |

---

### RiskEngine 类

风控引擎模块，负责信号风控检查和熔断处理。

**位置**: `src/risk/risk_engine.py`

#### 初始化

```python
risk = RiskEngine(config, state_manager, market)
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| config | Config | 配置对象 |
| state_manager | StateManager | 状态管理器 |
| market | MarketModule | 行情模块 |

#### 方法

##### check_signal()

```python
result = risk.check_signal(signal)
```

检查交易信号是否通过风控。

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| signal | TradingSignal | 交易信号 |

**返回**: `bool` - 是否通过风控

##### check_circuit_condition()

```python
risk.check_circuit_condition()
```

检查是否触发熔断条件。

---

### StateManager 类

状态管理器，负责持仓、订单等状态的持久化。

**位置**: `src/state/state_manager.py`

#### 初始化

```python
sm = StateManager(config)
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| config | Config | 配置对象 |

#### 方法

##### save_state()

```python
sm.save_state()
```

保存状态到文件。

##### load_state()

```python
sm.load_state()
```

从文件加载状态。

##### get_account()

```python
account = sm.get_account()
```

获取账户信息。

**返回**: 账户对象

##### get_band_position()

```python
position = sm.get_band_position()
```

获取波段持仓。

**返回**: 波段持仓对象

##### get_t_position()

```python
position = sm.get_t_position()
```

获取做T仓位。

**返回**: 做T仓位对象

##### sync_account_from_qmt()

```python
sm.sync_account_from_qmt(executor)
```

从QMT同步账户信息。

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| executor | QMTExecutor | 执行器对象 |

##### daily_settlement()

```python
sm.daily_settlement()
```

执行日终结算。

---

### MainController 类

主控模块，负责策略系统的启动、停止、调度和状态协调。

**位置**: `src/main_controller.py`

#### 初始化

```python
controller = MainController(config)
```

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| config | Config | 配置对象 |

#### 方法

##### start()

```python
controller.start()
```

启动策略系统。

##### stop()

```python
controller.stop()
```

停止策略系统。

##### run()

```python
controller.run()
```

主循环（阻塞）。

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `status` | str | 系统状态 (STOPPED/STARTING/RUNNING/STOPPING/ERROR) |
| `is_running` | bool | 是否正在运行 |

#### 回调方法

需要实现的回调接口：

| 方法 | 说明 |
|------|------|
| `on_order_filled(order)` | 订单成交回调 |
| `on_order_partial(order)` | 订单部分成交回调 |
| `on_order_cancelled(order)` | 订单撤单回调 |
| `on_order_rejected(order, reason)` | 订单拒绝回调 |

---

## 数据结构

### QuoteData

行情数据对象。

**属性**:
| 属性 | 类型 | 说明 |
|------|------|------|
| stock_code | str | 股票代码 |
| last_price | float | 最新价 |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| volume | float | 成交量 |
| amount | float | 成交额 |
| time | datetime | 时间 |
| vwap | float | 分时均价 |

### VWAPData

分时均线数据。

**属性**:
| 属性 | 类型 | 说明 |
|------|------|------|
| vwap | float | 当前均线值 |
| slope | float | 均线斜率 |
| change_rate | float | 变化率 |

---

*文档版本: 1.0.0*  
*最后更新: 2024*

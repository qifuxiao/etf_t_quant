# ETF T 策略量化交易系统

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

ETF T 策略量化交易系统是一个基于 Python 的自动化交易系统，专注于 A 股 ETF/股票 的 T+0 交易。系统集成了**做T策略**和**波段策略**，通过 QMT（迅投）接口实现自动化交易。

## 功能特性

### 1. 做T策略
- **做多T**: 股价下跌时买入，反弹时卖出赚取差价
- **做空T**: 股价上涨时卖出，回落时买回赚取差价
- 自动止盈止损
- 连续亏损熔断机制

### 2. 波段策略
- 趋势跟踪：站上均线买入，破位卖出
- 分批建仓/减仓
- 动态止盈：涨幅达标分批出货
- 止损保护：固定止损+均线止损

### 3. 风控引擎
- 大盘/板块环境限制
- 连续亏损熔断
- 波动率限制
- 涨跌停限制

### 4. 系统功能
- 状态自动持久化
- 日志自动管理
- 断线重连
- 模拟交易模式
- **API 服务**：提供 HTTP API 接口，支持前端实时行情和回测

## 环境要求

### Python 版本
- Python 3.8 ~ 3.12

### 依赖库
```
numpy>=1.20.0
pandas>=1.3.0
PyYAML>=5.4.0
requests>=2.25.0
python-dateutil>=2.8.0
loguru>=0.6.0
schedule>=1.1.0
fastapi>=0.100.0
uvicorn>=0.22.0
```

### 运行环境
- Windows（QMT 客户端）
- 需要安装 QMT 迅投客户端并完成登录

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 config.yml

编辑 `config.yml` 文件，配置交易参数：

```yaml
# 交易标的
stock:
  code: "300124"      # 股票代码
  name: "汇川技术"     # 股票名称

# 资金配置
capital:
  total: 200000       # 总资金（元）
  band_position_ratio: 0.6   # 波段底仓比例60%
  t_position_fund: 20000     # 做T资金池2万元

# QMT配置
qmt:
  account: "8881517461"     # QMT账号
  path: "D:/国金QMT交易端模拟/userdata_mini"  # QMT路径
  session_id: 123456
```

### 3. 启动 API 服务

```bash
cd etf_t_quant
python api_server.py
```

服务启动后访问：
- API 文档：http://localhost:8080/docs
- 实时行情：http://localhost:8080/api/realtime?code=300124
- 历史分时：http://localhost:8080/api/history?code=300124&date=2026-04-01

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 启动前端回测

```bash
cd frontend
npm install
npm run dev
```

打开浏览器访问：http://localhost:5173

**回测功能使用**：
1. 选择"回测模式"
2. 选择要回测的日期
3. 点击"开始回测"按钮
4. 系统将下载所选日期的分时数据并进行回测

### 5. 监控日志

查看 `logs/` 目录下的交易日志：

```bash
tail -f logs/trade_2024*.log
```

## 目录结构

```
etf_t_quant/
├── api_server.py           # API 服务入口
├── main.py                  # 主策略入口（可选）
├── config.yml               # 配置文件
├── requirements.txt         # Python依赖
├── src/
│   ├── config.py            # 配置管理模块
│   ├── main_controller.py   # 主控模块
│   ├── market_data.py       # 行情模块
│   ├── api.py               # FastAPI 服务
│   ├── strategy/
│   │   ├── t_strategy.py    # 做T策略
│   │   ├── band_strategy.py # 波段策略
│   │   └── signal.py        # 信号定义
│   ├── executor/
│   │   └── qmt_executor.py # QMT执行引擎（xtdata/xttrader）
│   ├── risk/
│   │   └── risk_engine.py  # 风控引擎
│   ├── state/
│   │   └── state_manager.py# 状态管理
│   └── log/
│       └── logger.py       # 日志模块
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── components/      # 组件
│   │   ├── stores/           # 状态管理
│   │   └── App.tsx          # 主应用
│   └── package.json
├── data/                    # 状态数据目录
├── logs/                    # 日志目录
└── tests/                   # 测试用例
```

## API 接口

| 接口 | 方法 | 说明 | 示例 |
|------|------|------|------|
| `/` | GET | 根路径 | `http://localhost:8080/` |
| `/health` | GET | 健康检查 | `http://localhost:8080/health` |
| `/api/realtime` | GET | 实时行情+分时 | `?code=300124` |
| `/api/history` | GET | 历史分时数据 | `?code=300124&date=2026-04-01` |
| `/api/stock` | GET | 股票基本信息 | `?code=300124` |
| `/api/signals` | GET | 交易信号 | `?code=300124` |
| `/api/dates` | GET | 可用交易日 | `?code=300124` |
| `/api/account` | GET | 资金账户信息 | - |
| `/api/position` | GET | 持仓信息 | `?code=300124` |

## 策略说明

### 做T策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_fund` | 20000 | 做T最大资金 |
| `max_ratio` | 0.3 | 每次做T不超过底仓30% |
| `trigger_drop` | 0.02 | 跌幅≥2%触发做多T |
| `trigger_deviation` | 0.003 | 偏离-0.3%触发 |
| `profit_target` | 0.005 | 止盈0.5% |
| `loss_stop` | 0.01 | 止损1.0% |

### 波段策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `initial_ratio` | 0.6 | 初始建仓60% |
| `max_ratio` | 0.8 | 最大仓位80% |
| `min_ratio` | 0.3 | 最小仓位30% |
| `profit_target` | 0.15 | 目标止盈15% |
| `stop_loss_fixed` | 0.05 | 固定止损-5% |

## 数据源

系统使用 **xtdata** 获取真实行情数据：
- **实时行情**：`xtdata.get_full_tick()`
- **历史分时**：`xtdata.get_market_data(period='1m')`
- **历史日K**：`xtdata.get_market_data(period='1d')`

数据来源于 QMT 客户端连接的行情服务器，确保数据真实性。

### 分时数据格式

API 返回的分时数据包含完整的 OHLC 数据：

```json
{
  "time": "09:30:00",
  "open": 68.50,
  "high": 68.55,
  "low": 68.36,
  "close": 68.50,
  "volume": 1914,
  "amount": 13110900.0
}
```

## 注意事项

### 1. 风险提示
- 量化交易存在风险，请谨慎使用
- 建议先在模拟盘测试验证
- 严格按照资金管理规则操作

### 2. QMT 要求
- 需要先启动 QMT 客户端并完成登录
- 确保 QMT 路径正确（userdata_mini 目录）
- 网络不畅时系统会自动重连

### 3. 运行模式
- **实盘模式**: QMT 连接成功时使用实盘交易
- **模拟模式**: QMT 连接失败时自动切换到模拟模式（仅供测试）

### 4. 数据备份
- 状态数据保存在 `data/state.json`
- 建议定期备份重要数据

## 常见问题

**Q: 启动时提示 QMT 连接失败？**
A: 检查 QMT 客户端是否已启动，配置文件中的账号密码是否正确。

**Q: API 返回空数据？**
A: 确认 QMT 已登录，xtdata 已连接。可能需要先下载历史数据。

**Q: 策略不执行交易？**
A: 检查：1) 策略是否启用；2) 是否在交易时间内；3) 风控是否拦截。

**Q: 如何查看交易记录？**
A: 查看 `logs/trade_*.log` 文件。

## License

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
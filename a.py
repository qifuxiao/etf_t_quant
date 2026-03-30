from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount
from xtquant import xtconstant

import time

# ========================
# 配置参数（必须修改）
# ========================
QMT_PATH = r"D:\国金QMT交易端模拟\userdata_mini"   # 👉 改成你的实际路径
SESSION_ID = 123456                  # 任意整数即可
ACCOUNT_ID = "55057942"          # 👉 必填

# ========================
# 初始化交易接口
# ========================
xt_trader = XtQuantTrader(QMT_PATH, SESSION_ID)

# 启动连接
xt_trader.start()

# 连接QMT
connect_result = xt_trader.connect()

if connect_result != 0:
    print("❌ 连接失败:", connect_result)
    exit()

print("✅ 连接成功")

# ========================
# 账户对象
# ========================
account = StockAccount(ACCOUNT_ID, "STOCK")

# ========================
# 查询资金
# ========================
asset = xt_trader.query_stock_asset(account)

if asset:
    print("\n💰 资金信息：")
    print("总资产:", asset.total_asset)
    print("可用资金:", asset.cash)
    print("市值:", asset.market_value)
else:
    print("❌ 获取资金失败")

# ========================
# 查询持仓
# ========================
positions = xt_trader.query_stock_positions(account)

print("\n📊 持仓信息：")

if positions:
    for pos in positions:
        print("-" * 30)
        print("股票代码:", pos.stock_code)
        print("持仓数量:", pos.volume)
        print("可用数量:", pos.can_use_volume)
        print("成本价:", pos.avg_price)
        print("市值:", pos.market_value)
else:
    print("⚠️ 当前无持仓")

# ========================
# 保持连接（避免立即退出）
# ========================
time.sleep(3)

# 停止
xt_trader.stop()
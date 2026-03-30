# app/infrastructure/qmt_client.py

import time
from typing import List, Optional

from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount


class QMTClient:
    def __init__(self, qmt_path: str, account_id: str, session_id: int = 123456):
        self.qmt_path = qmt_path
        self.account_id = account_id
        self.session_id = session_id

        self.trader: Optional[XtQuantTrader] = None
        self.account: Optional[StockAccount] = None

    def start(self):
        """启动并连接 QMT"""
        print(f"🚀 启动 QMT: path={self.qmt_path}")

        self.trader = XtQuantTrader(self.qmt_path, self.session_id)
        self.trader.start()

        result = self.trader.connect()
        if result != 0:
            raise RuntimeError(f"❌ QMT 连接失败: {result}")

        print("✅ QMT 连接成功")

        # ⚠️ 关键：必须指定 STOCK
        self.account = StockAccount(self.account_id, "STOCK")

    def stop(self):
        if self.trader:
            self.trader.stop()
            print("🛑 QMT 已停止")

    # ========================
    # 查询资金
    # ========================
    def get_asset(self):
        asset = self.trader.query_stock_asset(self.account)
        if not asset:
            print("❌ 获取资金失败")
            return None

        print("\n💰 资金信息：")
        print("总资产:", asset.total_asset)
        print("可用资金:", asset.cash)
        print("市值:", asset.market_value)

        return asset

    # ========================
    # 查询持仓
    # ========================
    def get_positions(self):
        positions = self.trader.query_stock_positions(self.account)

        print("\n📊 持仓信息：")

        if not positions:
            print("⚠️ 当前无持仓")
            return []

        result = []

        for pos in positions:
            data = {
                "stock_code": pos.stock_code,
                "volume": pos.volume,
                "can_use_volume": pos.can_use_volume,
                "avg_price": pos.avg_price,
                "market_value": pos.market_value,
            }
            result.append(data)

            print("-" * 30)
            print("股票代码:", data["stock_code"])
            print("持仓数量:", data["volume"])
            print("可用数量:", data["can_use_volume"])
            print("成本价:", data["avg_price"])
            print("市值:", data["market_value"])

        return result
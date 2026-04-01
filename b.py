from xtquant import xtdata, xtconstant
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
import threading

# === Trading Callbacks ===
class MyCallback(XtQuantTraderCallback):
    def on_stock_order(self, order):
        print(f'Order: {order.stock_code} status={order.order_status} {order.status_msg}')
    def on_stock_trade(self, trade):
        print(f'Trade: {trade.stock_code} {trade.traded_volume}@{trade.traded_price}')
    def on_order_error(self, error):
        print(f'Error: {error.error_msg}')

# === Initialize Trading ===
path = r'D:\国金QMT交易端模拟\userdata_mini'
xt_trader = XtQuantTrader(path, 888888)
xt_trader.register_callback(MyCallback())
xt_trader.start()
xt_trader.connect()
account = StockAccount('8881517461')
xt_trader.subscribe(account)

# === Quote Monitoring Parameters ===
target_stock = '000001.SZ'
buy_price = 10.50    # Target buy price
sell_price = 11.50   # Target sell price
bought = False

def on_tick(datas):
    """Real-time tick callback: automatically places orders when price hits target"""
    global bought
    for code, tick in datas.items():
        price = tick['lastPrice']
        print(f'{code}: latest price={price}')

        # Price drops to or below target buy price, buy
        if price <= buy_price and not bought:
            order_id = xt_trader.order_stock(
                account, code, xtconstant.STOCK_BUY, 100,
                xtconstant.FIX_PRICE, buy_price, 'auto_buy', '条件触发买入'
            )
            print(f'Buy triggered: order_id={order_id}')
            bought = True

        # Price rises to or above target sell price, sell
        elif price >= sell_price and bought:
            order_id = xt_trader.order_stock(
                account, code, xtconstant.STOCK_SELL, 100,
                xtconstant.FIX_PRICE, sell_price, 'auto_sell', '条件触发卖出'
            )
            print(f'Sell triggered: order_id={order_id}')
            bought = False

# === Start quote subscription (separate thread) ===
xtdata.connect()
def run_data():
    xtdata.subscribe_quote(target_stock, period='tick', callback=on_tick)
    xtdata.run()

t = threading.Thread(target=run_data, daemon=True)
t.start()

# Keep the main thread running
xt_trader.run_forever()
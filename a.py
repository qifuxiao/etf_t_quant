from xtquant import xtdata

# Connect to local miniQMT (default: localhost)
xtdata.connect()

# Download historical K-line data (must download to local cache before first access)
xtdata.download_history_data('000001.SZ', '1d', start_time='20240101', end_time='20240630')

# Get local K-line data (returns a dict of DataFrames keyed by stock code)
data = xtdata.get_market_data_ex(
    [],                    # field_list, empty list means all fields
    ['000001.SZ'],         # stock_list, list of stock codes
    period='1d',
    start_time='20240101',
    end_time='20240630',
    dividend_type='front'  # 复权类型: none (unadjusted), front (forward-adjusted), back (backward-adjusted), front_ratio (proportional forward), back_ratio (proportional backward)
)
print(data['000001.SZ'])

def on_data(datas):
    """Quote data callback function, receives pushed real-time data"""
    for stock_code, data in datas.items():
        print(stock_code, data)

# Subscribe to tick data for a single stock
xtdata.subscribe_quote('000001.SZ', period='tick', callback=on_data)

# Subscribe to full-market quote push
xtdata.subscribe_whole_quote(['SH', 'SZ'], callback=on_data)

xtdata.run()  # Block the current thread, continuously receiving callback data
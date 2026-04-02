# coding=utf-8
from __future__ import print_function, absolute_import
from gm.api import *
import time
import datetime

# GM API配置
GM_TOKEN = 'de3d46882e4afd894dcd5e43359d1dc5f38f9927'
GM_SERVER = '127.0.0.1:7001'

# 目标股票
TARGET_STOCK = 'SZSE.002648'

# 快照间隔（秒）
SNAPSHOT_INTERVAL = 3

def setup_gm_api():
    """设置GM API连接"""
    try:
        # 配置服务器
        set_serv_addr(addr=GM_SERVER)
        print(f"✅ 服务器配置成功: {GM_SERVER}")
        
        # 设置token
        set_token(GM_TOKEN)
        print("✅ Token设置成功")
        
        return True
    except Exception as e:
        print(f"❌ API设置失败: {e}")
        return False

def get_stock_snapshot(symbol):
    """获取股票快照数据"""
    try:
        current_data = current(symbols=[symbol])
        
        if current_data and len(current_data) > 0:
            return current_data[0]
        else:
            return None
            
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        return None

def display_snapshot_data(data):
    """显示快照数据"""
    if not data:
        print("❌ 无数据")
        return
    
    symbol = data.get('symbol', 'N/A')
    price = data.get('price', 'N/A')
    created_at = data.get('created_at', 'N/A')
    
    print(f"\n📊 {symbol} 快照数据:")
    print(f"   当前价格: {price}")
    print(f"   数据时间: {created_at}")
    print(f"   开盘价: {data.get('open', 'N/A')}")
    print(f"   最高价: {data.get('high', 'N/A')}")
    print(f"   最低价: {data.get('low', 'N/A')}")
    print(f"   成交量: {data.get('cum_volume', 'N/A')}")
    print(f"   成交额: {data.get('cum_amount', 'N/A')}")
    
    # 显示盘口报价（买卖五档）
    quotes = data.get('quotes', [])
    if quotes:
        print("   盘口报价（买卖五档）:")
        for i, quote in enumerate(quotes, 1):
            print(f"     第{i}档: 买价={quote.get('bid_p', 'N/A')}, 买量={quote.get('bid_v', 'N/A')}, "
                  f"卖价={quote.get('ask_p', 'N/A')}, 卖量={quote.get('ask_v', 'N/A')}")

def continuous_snapshot():
    """连续获取快照数据"""
    print("=== 开始3秒快照数据获取 ===")
    print(f"目标股票: {TARGET_STOCK}")
    print(f"快照间隔: {SNAPSHOT_INTERVAL}秒")
    print("按 Ctrl+C 停止")
    
    # 设置API
    if not setup_gm_api():
        return
    
    count = 0
    
    try:
        while True:
            count += 1
            current_time = datetime.datetime.now().strftime('%H:%M:%S')
            
            print(f"\n🔄 第{count}次获取 [{current_time}]")
            
            # 获取数据
            data = get_stock_snapshot(TARGET_STOCK)
            
            # 显示数据
            display_snapshot_data(data)
            
            # 等待3秒
            print(f"⏳ 等待{SNAPSHOT_INTERVAL}秒...")
            time.sleep(SNAPSHOT_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n✅ 快照获取已停止")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

def test_single_snapshot():
    """测试单次快照获取"""
    print("=== 测试单次快照获取 ===")
    
    # 设置API
    if not setup_gm_api():
        return
    
    # 获取数据
    data = get_stock_snapshot(TARGET_STOCK)
    
    # 显示数据
    display_snapshot_data(data)

def main():
    """主函数"""
    print("=== GM API 快照数据获取工具 ===")
    print(f"目标股票: {TARGET_STOCK}")
    print(f"服务器: {GM_SERVER}")
    
    while True:
        print("\n请选择功能:")
        print("1. 开始连续快照获取（3秒间隔）")
        print("2. 测试单次快照获取")
        print("3. 退出")
        
        choice = input("请输入选择 (1-3): ").strip()
        
        if choice == '1':
            continuous_snapshot()
        elif choice == '2':
            test_single_snapshot()
        elif choice == '3':
            print("✅ 程序退出")
            break
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == '__main__':
    main()
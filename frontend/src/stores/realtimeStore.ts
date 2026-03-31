import { create } from 'zustand';
import type { RealtimeData, TimeSeriesPoint, TradeSignal, TriggerCondition, StockInfo } from '../types';

interface RealtimeState {
  // 数据
  data: RealtimeData;
  isConnected: boolean;
  lastUpdate: string | null;
  
  // WebSocket
  connect: () => void;
  disconnect: () => void;
  updateData: (data: Partial<RealtimeData>) => void;
  addPoint: (point: TimeSeriesPoint) => void;
  addSignal: (signal: TradeSignal) => void;
  updateStockInfo: (info: Partial<StockInfo>) => void;
  
  // 刷新控制
  autoRefresh: boolean;
  setAutoRefresh: (enabled: boolean) => void;
  refresh: () => void;
}

// 模拟生成实时数据
const generateMockRealtimeData = (): RealtimeData => {
  const basePrice = 3.45;
  const timeSeries: TimeSeriesPoint[] = [];
  const signals: TradeSignal[] = [];
  const triggers: TriggerCondition[] = [];
  
  // 生成当天的分时数据（简化模拟）
  const hours = ['09:30', '09:35', '09:40', '09:45', '09:50', '09:55', '10:00', '10:05', '10:10', '10:15', '10:20', '10:25', '10:30', '10:35', '10:40', '10:45', '10:50', '10:55', '11:00', '11:05', '11:10', '11:15', '11:20', '11:25', '11:30'];
  
  let price = basePrice;
  let sumPrice = 0;
  let count = 0;
  
  hours.forEach((time) => {
    const change = (Math.random() - 0.5) * 0.02;
    price = Math.max(3.30, Math.min(3.60, price + change));
    const volume = Math.floor(Math.random() * 10000000) + 5000000;
    
    sumPrice += price;
    count++;
    
    timeSeries.push({
      time,
      price: parseFloat(price.toFixed(3)),
      volume,
      avgPrice: parseFloat((sumPrice / count).toFixed(3))
    });
  });
  
  // 添加一些模拟信号
  signals.push(
    { id: '1', time: '09:45', price: 3.42, type: 'buy', reason: '金叉买入' },
    { id: '2', time: '10:30', price: 3.48, type: 'sell', reason: '止盈卖出' },
    { id: '3', time: '11:00', price: 3.44, type: 'buy', reason: '做T买入' }
  );
  
  // 触发条件
  triggers.push(
    { id: '1', type: 'stop_loss', price: 3.38, time: '11:30', active: true },
    { id: '2', type: 'take_profit', price: 3.52, time: '11:30', active: true },
    { id: '3', type: 't_strategy', price: 3.46, time: '11:30', active: false }
  );
  
  const currentPrice = timeSeries[timeSeries.length - 1]?.price || basePrice;
  
  return {
    timeSeries,
    signals,
    triggers,
    stockInfo: {
      code: '511880',
      name: '上证ETF',
      currentPrice,
      change: parseFloat((currentPrice - basePrice).toFixed(3)),
      changePercent: parseFloat(((currentPrice - basePrice) / basePrice * 100).toFixed(2))
    }
  };
};

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  data: {
    timeSeries: [],
    signals: [],
    triggers: [],
    stockInfo: { code: '', name: '', currentPrice: 0, change: 0, changePercent: 0 }
  },
  isConnected: false,
  lastUpdate: null,
  autoRefresh: true,
  
  connect: () => {
    // 模拟 WebSocket 连接
    set({ isConnected: true });
    // 初始化数据
    const mockData = generateMockRealtimeData();
    set({ 
      data: mockData, 
      lastUpdate: new Date().toISOString() 
    });
  },
  
  disconnect: () => {
    set({ isConnected: false });
  },
  
  updateData: (newData) => {
    set((state) => ({
      data: { ...state.data, ...newData },
      lastUpdate: new Date().toISOString()
    }));
  },
  
  addPoint: (point) => {
    set((state) => ({
      data: {
        ...state.data,
        timeSeries: [...state.data.timeSeries, point]
      },
      lastUpdate: new Date().toISOString()
    }));
  },
  
  addSignal: (signal) => {
    set((state) => ({
      data: {
        ...state.data,
        signals: [...state.data.signals, signal]
      }
    }));
  },
  
  updateStockInfo: (info) => {
    set((state) => ({
      data: {
        ...state.data,
        stockInfo: { ...state.data.stockInfo, ...info }
      },
      lastUpdate: new Date().toISOString()
    }));
  },
  
  setAutoRefresh: (enabled) => {
    set({ autoRefresh: enabled });
  },
  
  refresh: () => {
    // 模拟刷新 - 添加新数据点
    const state = get();
    if (state.data.timeSeries.length > 0) {
      const lastPoint = state.data.timeSeries[state.data.timeSeries.length - 1];
      const lastTime = lastPoint.time;
      const [hour, min] = lastTime.split(':').map(Number);
      const newMin = min + 5;
      const newHour = newMin >= 60 ? hour + 1 : hour;
      const newMinStr = newMin >= 60 ? '00' : String(newMin).padStart(2, '0');
      const newTime = `${String(newHour).padStart(2, '0')}:${newMinStr}`;
      
      if (newHour > 11 && newHour < 13) return; // 午休时间不更新
      
      const change = (Math.random() - 0.5) * 0.02;
      const newPrice = Math.max(3.30, Math.min(3.60, lastPoint.price + change));
      const volume = Math.floor(Math.random() * 10000000) + 5000000;
      
      state.addPoint({
        time: newTime,
        price: parseFloat(newPrice.toFixed(3)),
        volume,
        avgPrice: parseFloat(((lastPoint.avgPrice! * state.data.timeSeries.length + newPrice) / (state.data.timeSeries.length + 1)).toFixed(3))
      });
      
      state.updateStockInfo({
        currentPrice: parseFloat(newPrice.toFixed(3)),
        change: parseFloat((newPrice - 3.45).toFixed(3)),
        changePercent: parseFloat(((newPrice - 3.45) / 3.45 * 100).toFixed(2))
      });
    }
  }
}));
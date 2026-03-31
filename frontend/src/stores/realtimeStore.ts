import { create } from 'zustand';
import type { RealtimeData, TimeSeriesPoint, TradeSignal, TriggerCondition, StockInfo } from '../types';

interface RealtimeState {
  // 数据
  data: RealtimeData;
  isConnected: boolean;
  lastUpdate: string | null;
  error: string | null;
  
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
  refresh: () => Promise<void>;
}

// API 地址
const API_BASE = 'http://localhost:8080';

// 默认股票代码
const DEFAULT_CODE = '300124';

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  data: {
    timeSeries: [],
    signals: [],
    triggers: [],
    stockInfo: { code: '', name: '', currentPrice: 0, change: 0, changePercent: 0 }
  },
  isConnected: false,
  lastUpdate: null,
  error: null,
  autoRefresh: true,
  
  connect: async () => {
    set({ isConnected: true, error: null });
    
    try {
      // 并行请求实时数据、信号和股票信息
      const [realtimeRes, signalsRes, stockRes] = await Promise.all([
        fetch(`${API_BASE}/api/realtime?code=${DEFAULT_CODE}`),
        fetch(`${API_BASE}/api/signals?code=${DEFAULT_CODE}`),
        fetch(`${API_BASE}/api/stock?code=${DEFAULT_CODE}`)
      ]);
      
      const [realtimeData, signalsData, stockData] = await Promise.all([
        realtimeRes.json(),
        signalsRes.json(),
        stockRes.json()
      ]);
      
      // 处理实时数据响应
      let timeSeries: TimeSeriesPoint[] = [];
      let triggers: TriggerCondition[] = [];
      
      if (realtimeData.code === 0 && realtimeData.data) {
        timeSeries = realtimeData.data.timeSeries || [];
        triggers = realtimeData.data.triggers || [];
      }
      
      // 处理信号响应
      let signals: TradeSignal[] = [];
      if (signalsData.code === 0 && signalsData.data) {
        signals = signalsData.data;
      }
      
      // 处理股票信息响应
      let stockInfo: StockInfo = { code: DEFAULT_CODE, name: '', currentPrice: 0, change: 0, changePercent: 0 };
      if (stockData.code === 0 && stockData.data) {
        stockInfo = stockData.data;
      }
      
      set({ 
        data: { timeSeries, signals, triggers, stockInfo },
        lastUpdate: new Date().toISOString()
      });
    } catch (error) {
      console.error('获取实时数据失败:', error);
      set({ error: '连接服务器失败，请检查后端服务是否运行' });
    }
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
  
  refresh: async () => {
    const state = get();
    
    try {
      // 刷新实时数据
      const [realtimeRes, stockRes] = await Promise.all([
        fetch(`${API_BASE}/api/realtime?code=${DEFAULT_CODE}`),
        fetch(`${API_BASE}/api/stock?code=${DEFAULT_CODE}`)
      ]);
      
      const [realtimeData, stockData] = await Promise.all([
        realtimeRes.json(),
        stockRes.json()
      ]);
      
      if (realtimeData.code === 0 && realtimeData.data) {
        set((state) => ({
          data: {
            ...state.data,
            timeSeries: realtimeData.data.timeSeries || state.data.timeSeries,
            triggers: realtimeData.data.triggers || state.data.triggers
          },
          lastUpdate: new Date().toISOString()
        }));
      }
      
      if (stockData.code === 0 && stockData.data) {
        set((state) => ({
          data: {
            ...state.data,
            stockInfo: stockData.data
          },
          lastUpdate: new Date().toISOString()
        }));
      }
    } catch (error) {
      console.error('刷新数据失败:', error);
      set({ error: '刷新数据失败' });
    }
  }
}));
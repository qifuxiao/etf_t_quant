import { create } from 'zustand';
import type { BacktestData, TimeSeriesPoint, TradeSignal, TriggerCondition, PlaybackState } from '../types';

interface BacktestState {
  // 数据
  data: BacktestData | null;
  selectedDate: string;
  availableDates: string[];
  
  // 播放控制
  playback: PlaybackState;
  
  // 方法
  setDate: (date: string) => void;
  loadData: (date: string) => Promise<void>;
  play: () => void;
  pause: () => void;
  stop: () => void;
  reset: () => void;
  setSpeed: (speed: number) => void;
  seek: (index: number) => void;
  stepForward: () => void;
  stepBackward: () => void;
}

// 生成模拟回测数据
const generateMockBacktestData = (date: string): BacktestData => {
  const basePrice = 3.45;
  const timeSeries: TimeSeriesPoint[] = [];
  const signals: TradeSignal[] = [];
  const triggers: TriggerCondition[] = [];
  
  // 生成完整的分时数据（9:30 - 15:00）
  const hours: string[] = [];
  for (let h = 9; h < 12; h++) {
    for (let m = 30; m < 60; m += 5) {
      hours.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
    }
  }
  hours.push('11:30'); // 上午结束
  for (let h = 13; h < 15; h++) {
    for (let m = 0; m < 60; m += 5) {
      hours.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
    }
  }
  hours.push('15:00'); // 下午结束
  
  let price = basePrice;
  let sumPrice = 0;
  let count = 0;
  
  // 模拟一天的价格波动
  const priceTrend = [
    0.005, 0.008, 0.01, 0.008, 0.005, 0, -0.005, -0.008, -0.01, -0.005, 0.005, 0.01,
    0.015, 0.01, 0.005, 0, -0.005, -0.01, -0.015, -0.01, -0.005, 0, 0.005, 0.008,
    0.01, 0.008, 0.005, 0, -0.005, -0.008, -0.01, -0.008, -0.005, 0, 0.005, 0.008,
    0.01, 0.008, 0.005, 0, -0.005, -0.008, -0.01, -0.005, 0, 0.005, 0.008, 0.01,
    0.008, 0.005, 0, -0.005, -0.008, -0.01, -0.008, -0.005, 0
  ];
  
  hours.forEach((time, index) => {
    const trend = priceTrend[index] || 0;
    const noise = (Math.random() - 0.5) * 0.01;
    price = Math.max(3.30, Math.min(3.60, basePrice + (index * 0.002) + trend + noise));
    const volume = Math.floor(Math.random() * 15000000) + 3000000;
    
    sumPrice += price;
    count++;
    
    timeSeries.push({
      time,
      price: parseFloat(price.toFixed(3)),
      volume,
      avgPrice: parseFloat((sumPrice / count).toFixed(3))
    });
  });
  
  // 添加历史信号
  signals.push(
    { id: '1', time: '09:35', price: 3.41, type: 'buy', reason: '突破买入' },
    { id: '2', time: '09:50', price: 3.44, type: 'sell', reason: '止盈卖出' },
    { id: '3', time: '10:15', price: 3.42, type: 'buy', reason: '回踩买入' },
    { id: '4', time: '10:45', price: 3.48, type: 'sell', reason: '高位卖出' },
    { id: '5', time: '11:20', price: 3.45, type: 'buy', reason: '做T买入' },
    { id: '6', time: '13:30', price: 3.50, type: 'sell', reason: '止盈卖出' },
    { id: '7', time: '14:15', price: 3.46, type: 'buy', reason: '低吸买入' },
    { id: '8', time: '14:45', price: 3.52, type: 'sell', reason: '尾盘卖出' }
  );
  
  // 触发条件
  triggers.push(
    { id: '1', type: 'stop_loss', price: 3.38, time: '09:30', active: true },
    { id: '2', type: 'take_profit', price: 3.55, time: '09:30', active: true },
    { id: '3', type: 't_strategy', price: 3.47, time: '10:00', active: true }
  );
  
  return {
    date,
    timeSeries,
    signals,
    triggers
  };
};

export const useBacktestStore = create<BacktestState>((set, get) => ({
  data: null,
  selectedDate: new Date().toISOString().split('T')[0],
  availableDates: [
    '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05',
    '2024-01-08', '2024-01-09', '2024-01-10', '2024-01-11',
    '2024-01-12', '2024-01-15', '2024-01-16', '2024-01-17',
    '2024-01-18', '2024-01-19', '2024-01-22', '2024-01-23',
    '2024-01-24', '2024-01-25', '2024-01-26', '2024-01-29',
    '2024-01-30', '2024-01-31'
  ],
  
  playback: {
    isPlaying: false,
    currentIndex: 0,
    speed: 1,
    totalPoints: 0
  },
  
  setDate: (date) => {
    set({ selectedDate: date });
    get().loadData(date);
  },
  
  loadData: async (date) => {
    // 模拟异步加载
    await new Promise(resolve => setTimeout(resolve, 300));
    const data = generateMockBacktestData(date);
    set({ 
      data,
      playback: {
        isPlaying: false,
        currentIndex: 0,
        speed: 1,
        totalPoints: data.timeSeries.length
      }
    });
  },
  
  play: () => {
    const state = get();
    if (state.playback.currentIndex >= state.playback.totalPoints - 1) {
      // 已经播完，重置
      set({
        playback: { ...state.playback, isPlaying: true, currentIndex: 0 }
      });
    } else {
      set({
        playback: { ...state.playback, isPlaying: true }
      });
    }
  },
  
  pause: () => {
    set((state) => ({
      playback: { ...state.playback, isPlaying: false }
    }));
  },
  
  stop: () => {
    set((state) => ({
      playback: { ...state.playback, isPlaying: false, currentIndex: 0 }
    }));
  },
  
  reset: () => {
    set((state) => ({
      playback: { ...state.playback, isPlaying: false, currentIndex: 0 }
    }));
  },
  
  setSpeed: (speed) => {
    const clampedSpeed = Math.max(1, Math.min(120, speed));
    set((state) => ({
      playback: { ...state.playback, speed: clampedSpeed }
    }));
  },
  
  seek: (index) => {
    const state = get();
    const clampedIndex = Math.max(0, Math.min(index, state.playback.totalPoints - 1));
    set({
      playback: { ...state.playback, currentIndex: clampedIndex }
    });
  },
  
  stepForward: () => {
    const state = get();
    if (state.playback.currentIndex < state.playback.totalPoints - 1) {
      set({
        playback: { ...state.playback, currentIndex: state.playback.currentIndex + 1 }
      });
    }
  },
  
  stepBackward: () => {
    const state = get();
    if (state.playback.currentIndex > 0) {
      set({
        playback: { ...state.playback, currentIndex: state.playback.currentIndex - 1 }
      });
    }
  }
}));
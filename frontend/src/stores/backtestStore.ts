import { create } from 'zustand';
import type { BacktestData, TimeSeriesPoint, TradeSignal, TriggerCondition, PlaybackState } from '../types';

interface BacktestState {
  // 数据
  data: BacktestData | null;
  selectedDate: string;
  availableDates: string[];
  datesCache: Record<string, string[]>;  // 日期缓存
  error: string | null;
  
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
  fetchAvailableDates: (code?: string) => Promise<void>;
}

// API 地址
const API_BASE = 'http://localhost:8080';

// 默认股票代码
const DEFAULT_CODE = '300124';

export const useBacktestStore = create<BacktestState>((set, get) => ({
  data: null,
  selectedDate: new Date().toISOString().split('T')[0],
  availableDates: [],
  datesCache: {},
  error: null,
  
  playback: {
    isPlaying: false,
    currentIndex: 0,
    speed: 1,
    totalPoints: 0
  },
  
  fetchAvailableDates: async (code = DEFAULT_CODE) => {
    const { datesCache } = get();
    
    // 检查缓存
    if (datesCache[code] && datesCache[code].length > 0) {
      set({ availableDates: datesCache[code] });
      return;
    }
    
    try {
      // 从后端获取可用日期
      const res = await fetch(`${API_BASE}/api/dates?code=${code}`);
      const data = await res.json();
      
      if (data.code === 0 && data.data && data.data.length > 0) {
        // 更新缓存
        set({
          availableDates: data.data,
          datesCache: { ...datesCache, [code]: data.data }
        });
      } else {
        // 如果没有日期接口，使用默认日期列表
        const today = new Date();
        const dates: string[] = [];
        for (let i = 0; i < 20; i++) {
          const d = new Date(today);
          d.setDate(d.getDate() - i);
          const day = d.getDay();
          if (day !== 0 && day !== 6) { // 排除周末
            dates.push(d.toISOString().split('T')[0]);
          }
        }
        set({ 
          availableDates: dates,
          datesCache: { ...datesCache, [code]: dates }
        });
      }
    } catch (error) {
      console.error('获取可用日期失败:', error);
      // 使用默认日期列表
      const today = new Date();
      const dates: string[] = [];
      for (let i = 0; i < 20; i++) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        const day = d.getDay();
        if (day !== 0 && day !== 6) {
          dates.push(d.toISOString().split('T')[0]);
        }
      }
      set({ 
        availableDates: dates,
        datesCache: { ...datesCache, [code]: dates }
      });
    }
  },
  
  setDate: (date) => {
    set({ selectedDate: date });
    // 选择日期后自动加载数据
    get().loadData(date);
  },
  
  loadData: async (date) => {
    set({ error: null });
    
    try {
      const res = await fetch(`${API_BASE}/api/history?code=${DEFAULT_CODE}&date=${date}`);
      const response = await res.json();
      
      if (response.code === 0 && response.data) {
        const data: BacktestData = {
          date,
          timeSeries: response.data.timeSeries || [],
          signals: response.data.signals || [],
          triggers: response.data.triggers || []
        };
        
        set({ 
          data,
          playback: {
            isPlaying: false,
            currentIndex: 0,
            speed: 1,
            totalPoints: data.timeSeries.length
          }
        });
      } else {
        set({ error: response.message || '加载数据失败' });
      }
    } catch (error) {
      console.error('加载历史数据失败:', error);
      set({ error: '连接服务器失败，请检查后端服务是否运行' });
    }
  },
  
  play: () => {
    const state = get();
    if (state.playback.currentIndex >= state.playback.totalPoints - 1) {
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
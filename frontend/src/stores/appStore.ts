import { create } from 'zustand';
import type { ViewMode, Settings } from '../types';

interface AppState {
  // 视图模式
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  
  // 公共设置
  settings: Settings;
  updateSettings: (settings: Partial<Settings>) => void;
  
  // 股票选择（当前选中的股票）
  selectedStock: {
    code: string;
    name: string;
  };
  setSelectedStock: (stock: { code: string; name: string }) => void;
}

export const useAppStore = create<AppState>((set) => ({
  viewMode: 'realtime',
  
  settings: {
    showMA: true,
    showVolume: true,
    showSignals: true,
    showTriggers: true
  },
  
  selectedStock: {
    code: '511880',
    name: '上证ETF'
  },
  
  setViewMode: (mode) => set({ viewMode: mode }),
  
  updateSettings: (newSettings) => set((state) => ({
    settings: { ...state.settings, ...newSettings }
  })),
  
  setSelectedStock: (stock) => set({ selectedStock: stock })
}));
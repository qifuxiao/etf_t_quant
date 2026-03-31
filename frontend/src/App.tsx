import { useEffect, useRef } from 'react';
import { useAppStore, useBacktestStore } from './stores';
import { Chart } from './components/Chart';
import { ModeSwitch } from './components/ModeSwitch';
import { Playback } from './components/Playback';
import { Realtime } from './components/Realtime';
import { Signals } from './components/Signals';
import { DatePicker, Settings } from './components/Common';
import type { TimeSeriesPoint } from './types';
import './App.css';

function App() {
  const { viewMode } = useAppStore();
  const { data, playback } = useBacktestStore();
  const intervalRef = useRef<number | null>(null);
  
  // 回测播放循环
  useEffect(() => {
    if (viewMode !== 'backtest' || !playback.isPlaying || !data) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }
    
    // 计算间隔时间 (基础 1 秒 = 1000ms，除以倍速)
    const baseInterval = 1000;
    const interval = baseInterval / playback.speed;
    
    intervalRef.current = window.setInterval(() => {
      const currentState = useBacktestStore.getState();
      
      if (currentState.playback.currentIndex >= currentState.playback.totalPoints - 1) {
        // 播放完毕
        currentState.pause();
        return;
      }
      
      // 步进
      currentState.seek(currentState.playback.currentIndex + 1);
    }, interval);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [viewMode, playback.isPlaying, playback.speed, data]);
  
  // 回测模式下，加载初始数据
  useEffect(() => {
    if (viewMode === 'backtest' && !data) {
      useBacktestStore.getState().loadData(useBacktestStore.getState().selectedDate);
    }
  }, [viewMode, data]);
  
  // 获取可见数据（回测模式下当前索引之前的数据）
  const visibleData: TimeSeriesPoint[] | undefined = viewMode === 'backtest' && data
    ? data.timeSeries.slice(0, playback.currentIndex + 1)
    : undefined;
  
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-title">ETF T+0 量化交易系统</h1>
          <span className="app-subtitle">分时数据可视化</span>
        </div>
        <div className="header-right">
          <ModeSwitch />
          <Settings />
        </div>
      </header>
      
      <main className="app-main">
        <div className="main-content">
          {viewMode === 'realtime' ? (
            <Realtime />
          ) : (
            <>
              <DatePicker />
              <Playback />
            </>
          )}
          
          <div className="chart-container">
            <Chart 
              visibleData={visibleData}
              currentIndex={viewMode === 'backtest' ? playback.currentIndex : undefined}
            />
          </div>
        </div>
        
        <aside className="sidebar">
          <Signals />
        </aside>
      </main>
      
      <footer className="app-footer">
        <span>© 2024 ETF T+0 量化交易系统</span>
      </footer>
    </div>
  );
}

export default App;
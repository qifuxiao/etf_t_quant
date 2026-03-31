import { useEffect, useState, useRef } from 'react';
import { useRealtimeStore, useAppStore } from '../../stores';
import './Realtime.css';

// 判断当前是否在交易时间
const isTradingTime = (): boolean => {
  const now = new Date();
  const hour = now.getHours();
  const minute = now.getMinutes();
  const time = hour * 60 + minute;
  
  // 上午: 9:30 - 11:30 (570 - 690)
  // 下午: 13:00 - 15:00 (780 - 900)
  const morningStart = 9 * 60 + 30; // 570
  const morningEnd = 11 * 60 + 30;  // 690
  const afternoonStart = 13 * 60;   // 780
  const afternoonEnd = 15 * 60;    // 900
  
  return (time >= morningStart && time <= morningEnd) || 
         (time >= afternoonStart && time <= afternoonEnd);
};

// 判断是否在周末
const isWeekend = (): boolean => {
  const day = new Date().getDay();
  return day === 0 || day === 6;
};

export const Realtime: React.FC = () => {
  const { viewMode } = useAppStore();
  const { data, isConnected, lastUpdate, autoRefresh, connect, disconnect, setAutoRefresh, refresh } = useRealtimeStore();
  const [status, setStatus] = useState<'closed' | 'trading' | 'break'>('closed');
  const intervalRef = useRef<number | null>(null);
  
  // 初始化连接
  useEffect(() => {
    if (viewMode === 'realtime') {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [viewMode]);
  
  // 刷新计时器
  useEffect(() => {
    if (viewMode !== 'realtime' || !autoRefresh) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }
    
    // 每分钟刷新一次
    intervalRef.current = window.setInterval(() => {
      if (isTradingTime()) {
        refresh();
      }
    }, 60000);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [viewMode, autoRefresh, refresh]);
  
  // 检查交易状态
  useEffect(() => {
    const checkStatus = () => {
      if (isWeekend()) {
        setStatus('closed');
        return;
      }
      
      if (isTradingTime()) {
        setStatus('trading');
      } else {
        // 检查是否在午间休市
        const now = new Date();
        const hour = now.getHours();
        const minute = now.getMinutes();
        const time = hour * 60 + minute;
        
        if (time > 690 && time < 780) {
          setStatus('break');
        } else {
          setStatus('closed');
        }
      }
    };
    
    checkStatus();
    const interval = setInterval(checkStatus, 60000);
    return () => clearInterval(interval);
  }, []);
  
  if (viewMode !== 'realtime') {
    return null;
  }
  
  const { stockInfo } = data;
  const changeColor = stockInfo.change >= 0 ? 'up' : 'down';
  const changeIcon = stockInfo.change >= 0 ? '▲' : '▼';
  
  return (
    <div className="realtime">
      <div className="realtime-header">
        <div className="stock-info">
          <div className="stock-code">{stockInfo.code}</div>
          <div className="stock-name">{stockInfo.name}</div>
        </div>
        
        <div className="price-info">
          <div className={`current-price ${changeColor}`}>
            {stockInfo.currentPrice.toFixed(3)}
          </div>
          <div className={`price-change ${changeColor}`}>
            <span className="change-icon">{changeIcon}</span>
            <span className="change-value">{Math.abs(stockInfo.change).toFixed(3)}</span>
            <span className="change-percent">({stockInfo.changePercent.toFixed(2)}%)</span>
          </div>
        </div>
        
        <div className="status-info">
          <div className={`status-badge ${status}`}>
            {status === 'trading' ? '交易中' : status === 'break' ? '休市' : '未开盘'}
          </div>
          <div className="connect-status">
            <span className={`status-dot ${isConnected ? 'connected' : ''}`}></span>
            {isConnected ? '已连接' : '未连接'}
          </div>
        </div>
      </div>
      
      <div className="realtime-controls">
        <label className="auto-refresh-toggle">
          <input 
            type="checkbox" 
            checked={autoRefresh} 
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          <span>自动刷新</span>
        </label>
        <button 
          className="refresh-btn"
          onClick={refresh}
          disabled={!isConnected || status !== 'trading'}
        >
          刷新数据
        </button>
        {lastUpdate && (
          <span className="last-update">
            更新: {new Date(lastUpdate).toLocaleTimeString()}
          </span>
        )}
      </div>
      
      <div className="realtime-stats">
        <div className="stat-item">
          <span className="stat-label">最高</span>
          <span className="stat-value">
            {data.timeSeries.length > 0 
              ? Math.max(...data.timeSeries.map(p => p.price)).toFixed(3)
              : '--'}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">最低</span>
          <span className="stat-value">
            {data.timeSeries.length > 0 
              ? Math.min(...data.timeSeries.map(p => p.price)).toFixed(3)
              : '--'}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">今开</span>
          <span className="stat-value">
            {data.timeSeries.length > 0 ? data.timeSeries[0].price.toFixed(3) : '--'}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">成交量</span>
          <span className="stat-value">
            {data.timeSeries.length > 0 
              ? (data.timeSeries.reduce((sum, p) => sum + p.volume, 0) / 100000000).toFixed(2) + '亿'
              : '--'}
          </span>
        </div>
      </div>
    </div>
  );
};
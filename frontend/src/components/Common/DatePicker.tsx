import React from 'react';
import { useBacktestStore, useAppStore } from '../../stores';
import './DatePicker.css';

export const DatePicker: React.FC = () => {
  const { viewMode } = useAppStore();
  const { selectedDate, availableDates, setDate } = useBacktestStore();
  
  if (viewMode !== 'backtest') {
    return null;
  }
  
  return (
    <div className="date-picker">
      <label className="date-label">选择日期:</label>
      <select 
        value={selectedDate}
        onChange={(e) => setDate(e.target.value)}
        className="date-select"
      >
        {availableDates.map(date => (
          <option key={date} value={date}>
            {date}
          </option>
        ))}
      </select>
      <span className="date-hint">选择日期进行回测复盘</span>
    </div>
  );
};
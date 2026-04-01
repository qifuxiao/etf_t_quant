import React from 'react';
import { useBacktestStore, useAppStore } from '../../stores';
import './DatePicker.css';

export const DatePicker: React.FC = () => {
  const { viewMode } = useAppStore();
  const { selectedDate, availableDates, setDate, loadData, isLoading, error } = useBacktestStore();
  
  if (viewMode !== 'backtest') {
    return null;
  }
  
  const handleDateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setDate(e.target.value);
  };
  
  const handleStartBacktest = async () => {
    await loadData(selectedDate);
  };
  
  return (
    <div className="date-picker">
      <label className="date-label">选择日期:</label>
      <select 
        value={selectedDate}
        onChange={handleDateChange}
        className="date-select"
      >
        {availableDates.map(date => (
          <option key={date} value={date}>
            {date}
          </option>
        ))}
      </select>
      <button 
        className="backtest-button"
        onClick={handleStartBacktest}
        disabled={isLoading}
      >
        {isLoading ? '加载中...' : '开始回测'}
      </button>
      {error && <span className="date-error">{error}</span>}
    </div>
  );
};
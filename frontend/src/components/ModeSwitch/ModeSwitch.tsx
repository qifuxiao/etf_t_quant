import React from 'react';
import { useAppStore } from '../../stores';
import type { ViewMode } from '../../types';
import './ModeSwitch.css';

interface ModeSwitchProps {
  onModeChange?: (mode: ViewMode) => void;
}

export const ModeSwitch: React.FC<ModeSwitchProps> = ({ onModeChange }) => {
  const { viewMode, setViewMode } = useAppStore();
  
  const handleModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    onModeChange?.(mode);
  };
  
  return (
    <div className="mode-switch">
      <button 
        className={`mode-btn ${viewMode === 'realtime' ? 'active' : ''}`}
        onClick={() => handleModeChange('realtime')}
      >
        <span className="mode-icon">📊</span>
        实时模式
      </button>
      <button 
        className={`mode-btn ${viewMode === 'backtest' ? 'active' : ''}`}
        onClick={() => handleModeChange('backtest')}
      >
        <span className="mode-icon">🔄</span>
        回测模式
      </button>
    </div>
  );
};
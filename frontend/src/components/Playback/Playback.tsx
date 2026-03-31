import React from 'react';
import { useBacktestStore, useAppStore } from '../../stores';
import './Playback.css';

export const Playback: React.FC = () => {
  const { viewMode } = useAppStore();
  const { data, playback, setSpeed, seek, play, pause, stop, reset, stepForward, stepBackward } = useBacktestStore();
  
  if (viewMode !== 'backtest' || !data) {
    return null;
  }
  
  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    seek(parseInt(e.target.value));
  };
  
  const handleSpeedChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSpeed(parseInt(e.target.value));
  };
  
  const currentPoint = data.timeSeries[playback.currentIndex];
  const progress = playback.totalPoints > 0 
    ? ((playback.currentIndex + 1) / playback.totalPoints) * 100 
    : 0;
  
  return (
    <div className="playback">
      <div className="playback-controls">
        <button className="control-btn" onClick={reset} title="重置">
          ⏮
        </button>
        <button className="control-btn" onClick={stepBackward} title="后退">
          ⏪
        </button>
        <button 
          className={`control-btn ${playback.isPlaying ? 'playing' : ''}`}
          onClick={playback.isPlaying ? pause : play}
          title={playback.isPlaying ? '暂停' : '播放'}
        >
          {playback.isPlaying ? '⏸' : '▶'}
        </button>
        <button className="control-btn" onClick={stepForward} title="前进">
          ⏩
        </button>
        <button className="control-btn" onClick={stop} title="停止">
          ⏹
        </button>
      </div>
      
      <div className="playback-progress">
        <span className="time-label">
          {currentPoint ? currentPoint.time : '--:--'}
        </span>
        <input
          type="range"
          min="0"
          max={playback.totalPoints - 1}
          value={playback.currentIndex}
          onChange={handleSliderChange}
          className="progress-slider"
          disabled={playback.isPlaying}
        />
        <span className="time-label">
          {data.timeSeries[data.timeSeries.length - 1]?.time || '--:--'}
        </span>
      </div>
      
      <div className="playback-info">
        <div className="info-item">
          <span className="label">价格:</span>
          <span className="value">{currentPoint?.price?.toFixed(3) || '--'}</span>
        </div>
        <div className="info-item">
          <span className="label">量能:</span>
          <span className="value">{currentPoint ? (currentPoint.volume / 10000).toFixed(0) + '万' : '--'}</span>
        </div>
        <div className="info-item">
          <span className="label">进度:</span>
          <span className="value">{playback.currentIndex + 1}/{playback.totalPoints}</span>
        </div>
      </div>
      
      <div className="playback-speed">
        <label>倍速:</label>
        <select value={playback.speed} onChange={handleSpeedChange} className="speed-select">
          <option value="1">1x</option>
          <option value="2">2x</option>
          <option value="5">5x</option>
          <option value="10">10x</option>
          <option value="20">20x</option>
          <option value="30">30x</option>
          <option value="60">60x</option>
          <option value="120">120x</option>
        </select>
      </div>
      
      <div className="playback-progress-bar">
        <div className="progress-bar" style={{ width: `${progress}%` }}></div>
      </div>
    </div>
  );
};
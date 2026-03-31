import React, { useState } from 'react';
import { useAppStore } from '../../stores';
import './Settings.css';

export const Settings: React.FC = () => {
  const { settings, updateSettings } = useAppStore();
  const [isOpen, setIsOpen] = useState(false);
  
  const handleToggle = (key: keyof typeof settings) => {
    updateSettings({ [key]: !settings[key] });
  };
  
  return (
    <div className="settings">
      <button 
        className="settings-toggle"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="settings-icon">⚙</span>
        设置
      </button>
      
      {isOpen && (
        <div className="settings-panel">
          <h3 className="settings-title">显示设置</h3>
          
          <div className="settings-options">
            <label className="settings-option">
              <input
                type="checkbox"
                checked={settings.showMA}
                onChange={() => handleToggle('showMA')}
              />
              <span>显示均线</span>
            </label>
            
            <label className="settings-option">
              <input
                type="checkbox"
                checked={settings.showVolume}
                onChange={() => handleToggle('showVolume')}
              />
              <span>显示量能</span>
            </label>
            
            <label className="settings-option">
              <input
                type="checkbox"
                checked={settings.showSignals}
                onChange={() => handleToggle('showSignals')}
              />
              <span>显示买卖信号</span>
            </label>
            
            <label className="settings-option">
              <input
                type="checkbox"
                checked={settings.showTriggers}
                onChange={() => handleToggle('showTriggers')}
              />
              <span>显示触发条件</span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
};
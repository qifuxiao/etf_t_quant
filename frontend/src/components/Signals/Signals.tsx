import React from 'react';
import { useRealtimeStore, useBacktestStore, useAppStore } from '../../stores';
import type { TradeSignal, TriggerCondition } from '../../types';
import './Signals.css';

interface SignalItemProps {
  signal: TradeSignal;
}

const SignalItem: React.FC<SignalItemProps> = ({ signal }) => {
  const typeLabel = signal.type === 'buy' ? '买入' : '卖出';
  const typeClass = signal.type === 'buy' ? 'buy' : 'sell';
  
  return (
    <div className={`signal-item ${typeClass}`}>
      <span className="signal-type">{typeLabel}</span>
      <span className="signal-time">{signal.time}</span>
      <span className="signal-price">{signal.price.toFixed(3)}</span>
      <span className="signal-reason">{signal.reason}</span>
    </div>
  );
};

interface TriggerItemProps {
  trigger: TriggerCondition;
}

const TriggerItem: React.FC<TriggerItemProps> = ({ trigger }) => {
  const typeLabel = trigger.type === 'stop_loss' ? '止损' : trigger.type === 'take_profit' ? '止盈' : '做T';
  const typeClass = trigger.type === 'stop_loss' ? 'stop-loss' : trigger.type === 'take_profit' ? 'take-profit' : 't-strategy';
  
  return (
    <div className={`trigger-item ${typeClass} ${trigger.active ? 'active' : ''}`}>
      <span className="trigger-type">{typeLabel}</span>
      <span className="trigger-price">{trigger.price.toFixed(3)}</span>
      <span className={`trigger-status ${trigger.active ? 'active' : ''}`}>
        {trigger.active ? '● 运行中' : '○ 未触发'}
      </span>
    </div>
  );
};

export const Signals: React.FC = () => {
  const { viewMode, settings } = useAppStore();
  const realtimeData = useRealtimeStore(state => state.data);
  const backtestData = useBacktestStore(state => state.data);
  
  const signals = viewMode === 'realtime' ? realtimeData.signals : backtestData?.signals || [];
  const triggers = viewMode === 'realtime' ? realtimeData.triggers : backtestData?.triggers || [];
  
  // 过滤显示
  const visibleSignals = settings.showSignals ? signals : [];
  const visibleTriggers = settings.showTriggers ? triggers : [];
  
  // 按时间排序
  const sortedSignals = [...visibleSignals].sort((a, b) => a.time.localeCompare(b.time));
  
  return (
    <div className="signals">
      {visibleSignals.length > 0 && (
        <div className="signals-section">
          <h3 className="section-title">买卖信号</h3>
          <div className="signals-list">
            {sortedSignals.map(signal => (
              <SignalItem key={signal.id} signal={signal} />
            ))}
          </div>
        </div>
      )}
      
      {visibleTriggers.length > 0 && (
        <div className="triggers-section">
          <h3 className="section-title">触发条件</h3>
          <div className="triggers-list">
            {visibleTriggers.map(trigger => (
              <TriggerItem key={trigger.id} trigger={trigger} />
            ))}
          </div>
        </div>
      )}
      
      {visibleSignals.length === 0 && visibleTriggers.length === 0 && (
        <div className="no-data">
          暂无信号数据
        </div>
      )}
    </div>
  );
};
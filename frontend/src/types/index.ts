// 分时数据点
export interface TimeSeriesPoint {
  time: string; // HH:MM 格式
  price: number;
  volume: number;
  avgPrice?: number; // 均线
}

// 买卖信号
export interface TradeSignal {
  id: string;
  time: string;
  price: number;
  type: 'buy' | 'sell';
  reason: string; // 触发条件描述
}

// 触发条件
export interface TriggerCondition {
  id: string;
  type: 'stop_loss' | 'take_profit' | 't_strategy'; // 止损/止盈/做T
  price: number;
  time: string;
  active: boolean;
}

// 股票信息
export interface StockInfo {
  code: string;
  name: string;
  currentPrice: number;
  change: number;
  changePercent: number;
}

// 回测数据
export interface BacktestData {
  date: string; // YYYY-MM-DD
  timeSeries: TimeSeriesPoint[];
  signals: TradeSignal[];
  triggers: TriggerCondition[];
}

// 实时数据
export interface RealtimeData {
  timeSeries: TimeSeriesPoint[];
  signals: TradeSignal[];
  triggers: TriggerCondition[];
  stockInfo: StockInfo;
}

// 播放状态
export interface PlaybackState {
  isPlaying: boolean;
  currentIndex: number;
  speed: number; // 1-120 倍
  totalPoints: number;
}

// 视图模式
export type ViewMode = 'realtime' | 'backtest';

// 公共设置
export interface Settings {
  showMA: boolean; // 显示均线
  showVolume: boolean; // 显示量能
  showSignals: boolean; // 显示买卖信号
  showTriggers: boolean; // 显示触发条件
}

// API 响应类型
export interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}
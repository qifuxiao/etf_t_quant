import { useRef, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { useAppStore, useRealtimeStore, useBacktestStore } from '../../stores';
import type { TimeSeriesPoint } from '../../types';

interface ChartProps {
  visibleData?: TimeSeriesPoint[]; // 回测时可见的数据范围
  currentIndex?: number; // 回测时当前播放到的索引
}

export const Chart: React.FC<ChartProps> = ({ visibleData, currentIndex }) => {
  const chartRef = useRef<ReactECharts>(null);
  
  const { viewMode, settings } = useAppStore();
  const realtimeData = useRealtimeStore(state => state.data);
  const backtestData = useBacktestStore(state => state.data);
  
  // 根据模式获取数据
  const data = useMemo(() => {
    if (viewMode === 'realtime') {
      return realtimeData.timeSeries;
    } else if (visibleData) {
      return visibleData;
    } else if (backtestData) {
      return backtestData.timeSeries;
    }
    return [];
  }, [viewMode, realtimeData.timeSeries, visibleData, backtestData]);
  
  const signals = useMemo(() => {
    if (viewMode === 'realtime') {
      return realtimeData.signals;
    } else if (backtestData) {
      // 回测模式下，显示到当前索引之前的所有信号
      if (currentIndex !== undefined) {
        return backtestData.signals.filter(s => {
          const signalIndex = data.findIndex(p => p.time === s.time);
          return signalIndex <= currentIndex;
        });
      }
      return backtestData.signals;
    }
    return [];
  }, [viewMode, realtimeData.signals, backtestData?.signals, data, currentIndex]);
  
  const triggers = useMemo(() => {
    if (viewMode === 'realtime') {
      return realtimeData.triggers;
    } else if (backtestData) {
      return backtestData.triggers;
    }
    return [];
  }, [viewMode, realtimeData.triggers, backtestData?.triggers]);
  
  // ECharts 配置
  const option = useMemo(() => {
    if (data.length === 0) {
      return {
        title: { text: '暂无数据', left: 'center', top: 'middle' },
        grid: { top: 40, bottom: 40, left: 60, right: 40 }
      };
    }
    
    const times = data.map(d => d.time);
    const prices = data.map(d => d.price);
    const volumes = data.map(d => d.volume);
    const avgPrices = data.map(d => d.avgPrice || d.price);
    
    // 计算价格范围
    const minPrice = Math.min(...prices) * 0.995;
    const maxPrice = Math.max(...prices) * 1.005;
    
    const series: any[] = [
      // 价格线
      {
        name: '价格',
        type: 'line',
        data: prices,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          color: '#5470C6'
        },
        markPoint: settings.showSignals ? {
          data: signals.map(s => ({
            coord: [s.time, s.price],
            value: s.type === 'buy' ? '买' : '卖',
            itemStyle: {
              color: s.type === 'buy' ? '#EE6666' : '#91CC75'
            }
          })),
          symbolSize: 40,
          label: {
            fontSize: 10,
            color: '#fff'
          }
        } : undefined
      }
    ];
    
    // 均线
    if (settings.showMA) {
      series.push({
        name: '均线',
        type: 'line',
        data: avgPrices,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 1,
          color: '#FAC858',
          type: 'dashed'
        },
        emphasis: {
          disabled: true
        }
      });
    }
    
    // 触发条件线
    if (settings.showTriggers) {
      triggers.forEach(trigger => {
        series.push({
          name: trigger.type === 'stop_loss' ? '止损' : trigger.type === 'take_profit' ? '止盈' : '做T',
          type: 'line',
          markLine: {
            silent: true,
            symbol: 'none',
            label: {
              show: true,
              position: 'end',
              formatter: trigger.type === 'stop_loss' ? '止损' : trigger.type === 'take_profit' ? '止盈' : '做T'
            },
            lineStyle: {
              color: trigger.type === 'stop_loss' ? '#EE6666' : trigger.type === 'take_profit' ? '#91CC75' : '#5470C6',
              type: 'dashed'
            },
            data: [
              { yAxis: trigger.price }
            ]
          }
        });
      });
    }
    
    // 量能柱状图
    if (settings.showVolume) {
      series.push({
        name: '量能',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
        itemStyle: {
          color: (params: any) => {
            // 根据涨跌显示不同颜色
            if (params.dataIndex === 0) return '#91CC75';
            const prevPrice = prices[params.dataIndex - 1];
            const currPrice = prices[params.dataIndex];
            return currPrice >= prevPrice ? '#EE6666' : '#91CC75';
          }
        }
      });
    }
    
    return {
      animation: viewMode === 'backtest', // 回测模式启用动画
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        },
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          const time = params[0].axisValue;
          const priceData = params.find((p: any) => p.seriesName === '价格');
          const volumeData = params.find((p: any) => p.seriesName === '量能');
          const avgData = params.find((p: any) => p.seriesName === '均线');
          
          let html = `<div style="font-size:12px"><strong>${time}</strong><br/>`;
          if (priceData) {
            html += `价格: ${priceData.value}<br/>`;
          }
          if (avgData) {
            html += `均线: ${avgData.value}<br/>`;
          }
          if (volumeData) {
            html += `量能: ${(volumeData.value / 10000).toFixed(2)}万<br/>`;
          }
          
          // 显示信号
          const timeSignals = signals.filter(s => s.time === time);
          timeSignals.forEach(s => {
            html += `<span style="color:${s.type === 'buy' ? '#EE6666' : '#91CC75'}">◆ ${s.type === 'buy' ? '买入' : '卖出'} ${s.price} (${s.reason})</span><br/>`;
          });
          
          html += '</div>';
          return html;
        }
      },
      legend: {
        data: ['价格', '均线', '量能'],
        top: 0,
        left: 20
      },
      grid: [
        {
          top: 40,
          bottom: '50%',
          left: 60,
          right: 40
        },
        {
          top: '55%',
          bottom: 40,
          left: 60,
          right: 40
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: times,
          boundaryGap: false,
          axisLine: { onZero: false },
          axisLabel: {
            formatter: (value: string) => {
              const [h, m] = value.split(':');
              if (m === '00' || m === '30') {
                return `${h}:${m}`;
              }
              return '';
            }
          },
          splitLine: {
            show: true,
            lineStyle: {
              color: '#eee',
              type: 'dashed'
            }
          }
        },
        {
          type: 'category',
          data: times,
          gridIndex: 1,
          boundaryGap: false,
          axisLabel: { show: false },
          axisLine: { onZero: false },
          splitLine: { show: false }
        }
      ],
      yAxis: [
        {
          type: 'value',
          min: minPrice,
          max: maxPrice,
          scale: true,
          splitNumber: 5,
          axisLabel: {
            formatter: (value: number) => value.toFixed(3)
          },
          splitLine: {
            show: true,
            lineStyle: {
              color: '#eee',
              type: 'dashed'
            }
          }
        },
        {
          type: 'value',
          gridIndex: 1,
          splitNumber: 3,
          axisLabel: {
            formatter: (value: number) => (value / 10000).toFixed(0) + '万'
          },
          splitLine: {
            show: true,
            lineStyle: {
              color: '#eee',
              type: 'dashed'
            }
          }
        }
      ],
      series
    };
  }, [data, signals, triggers, settings, viewMode, currentIndex]);
  
  return (
    <div style={{ width: '100%', height: '100%', minHeight: 400 }}>
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ width: '100%', height: '100%' }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
};
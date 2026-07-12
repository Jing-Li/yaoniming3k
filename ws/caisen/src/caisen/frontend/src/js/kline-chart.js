/**
 * Caisen Visualization - K-Line Chart (Lightweight Charts)
 * 使用 TradingView Lightweight Charts 渲染高性能 K 线主图
 *
 * 替代原 ECharts candlestick 实现，性能提升 5-10x
 */

import { createChart, CandlestickSeries, HistogramSeries, LineSeries, ColorType } from 'lightweight-charts';
import { CHART_COLORS } from './constants.js';
import { calculateMA } from './chart-builder.js';
import { processAnnotations } from './annotation-renderer.js';
import { processTrades } from './chart-builder.js';
import { buildBarIndex } from './utils.js';
import { createLogger } from './logger.js';

const log = createLogger('KLineChart');

// ============================================================
// Time conversion utilities
// ============================================================

/**
 * Convert ISO timestamp to LWC UTC timestamp (seconds).
 * LWC accepts UTC seconds or { year, month, day } objects.
 * @param {string} timestamp - ISO timestamp string
 * @returns {number} UTC seconds
 */
function toUtcSeconds(timestamp) {
  return Math.floor(new Date(timestamp).getTime() / 1000);
}

// ============================================================
// Chart creation & configuration
// ============================================================

/**
 * LWC chart theme — matches existing dark theme
 */
const CHART_THEME = {
  layout: {
    background: { type: ColorType.Solid, color: 'transparent' },
    textColor: CHART_COLORS.textColor,
    fontFamily: "'Inter', ui-sans-serif, system-ui, sans-serif",
    fontSize: 12,
  },
  grid: {
    vertLines: { color: 'rgba(45, 55, 72, 0.5)', style: 1 },
    horzLines: { color: 'rgba(45, 55, 72, 0.5)', style: 1 },
  },
  crosshair: {
    vertLine: { color: '#a0aec0', width: 1, style: 2, labelBackgroundColor: '#2d3748' },
    horzLine: { color: '#a0aec0', width: 1, style: 2, labelBackgroundColor: '#2d3748' },
  },
  rightPriceScale: {
    borderColor: CHART_COLORS.lineColor,
    scaleMargins: { top: 0.05, bottom: 0.25 },
  },
  timeScale: {
    borderColor: CHART_COLORS.lineColor,
    timeVisible: true,
    secondsVisible: false,
    rightOffset: 5,
    barSpacing: 8,
  },
  handleScroll: { mouseWheel: true, pressedMouseMove: true },
  handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
};

/**
 * Create or update K-line chart using Lightweight Charts.
 *
 * @param {HTMLElement} container - DOM element for chart
 * @param {Object} options
 * @param {Object} options.data - Filtered data with bars, annotations, trades
 * @param {boolean} options.showMA - Whether to show MA overlays
 * @param {Object|null} options.existingChart - Existing LWC chart instance (for updates)
 * @returns {{ chart: Object, candleSeries: Object, overlayCanvas: HTMLCanvasElement|null }}
 */
export function renderKLine({ container, data, showMA = true, existingChart = null }) {
  if (!data || !data.bars || data.bars.length === 0) {
    log.warn('无数据，跳过渲染');
    return null;
  }

  log.info('开始渲染, bars:', data.bars.length);
  const startTime = performance.now();

  // Dispose previous chart if exists
  if (existingChart) {
    try { existingChart.remove(); } catch (e) { /* ignore */ }
  }

  // Create chart
  const chartHeight = parseInt(getComputedStyle(container).height) || 500;
  const chart = createChart(container, {
    ...CHART_THEME,
    width: container.clientWidth,
    height: chartHeight,
  });

  // ---- Candlestick series ----
  const candleSeries = chart.addSeries(CandlestickSeries, {
    upColor: CHART_COLORS.upColor,
    downColor: CHART_COLORS.downColor,
    borderUpColor: CHART_COLORS.upColor,
    borderDownColor: CHART_COLORS.downColor,
    wickUpColor: CHART_COLORS.upColor,
    wickDownColor: CHART_COLORS.downColor,
  });

  const candleData = data.bars.map(bar => ({
    time: toUtcSeconds(bar.timestamp),
    open: bar.open,
    high: bar.high,
    low: bar.low,
    close: bar.close,
  }));
  candleSeries.setData(candleData);

  // ---- Volume series ----
  const volumeSeries = chart.addSeries(HistogramSeries, {
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',
  });

  chart.priceScale('volume').applyOptions({
    scaleMargins: { top: 0.82, bottom: 0 },
  });

  const volumeData = data.bars.map(bar => ({
    time: toUtcSeconds(bar.timestamp),
    value: bar.volume,
    color: bar.close >= bar.open
      ? 'rgba(72, 187, 120, 0.5)'
      : 'rgba(252, 129, 129, 0.5)',
  }));
  volumeSeries.setData(volumeData);

  // ---- MA overlays ----
  let ma5Series = null;
  let ma20Series = null;

  if (showMA) {
    const ma5 = calculateMA(data.bars, 5);
    const ma20 = calculateMA(data.bars, 20);

    ma5Series = chart.addSeries(LineSeries, {
      color: '#f6ad55',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
    ma5Series.setData(buildLineData(data.bars, ma5));

    ma20Series = chart.addSeries(LineSeries, {
      color: '#9f7aea',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
    ma20Series.setData(buildLineData(data.bars, ma20));
  }

  // ---- Trade markers + signal markers ----
  const tradeMarkers = buildTradeMarkers(data.trades, data.bars);
  const signalMarkers = buildSignalMarkers(data.annotations, data.bars);
  const allMarkers = mergeMarkers(tradeMarkers, signalMarkers);
  if (allMarkers.length > 0) {
    candleSeries.setMarkers(allMarkers);
  }

  // ---- Annotation price lines ----
  applyAnnotationPriceLines(chart, candleSeries, data);

  // ---- Fit content ----
  chart.timeScale().fitContent();

  // ---- Resize observer ----
  const resizeObserver = new ResizeObserver(entries => {
    for (const entry of entries) {
      const { width, height } = entry.contentRect;
      chart.applyOptions({ width, height });
    }
  });
  resizeObserver.observe(container);

  const elapsed = (performance.now() - startTime).toFixed(1);
  log.info(`渲染完成, 耗时: ${elapsed}ms, bars: ${data.bars.length}`);

  return {
    chart,
    candleSeries,
    volumeSeries,
    ma5Series,
    ma20Series,
    resizeObserver,
  };
}

// ============================================================
// Helper functions
// ============================================================

/**
 * Build LWC line series data from MA array
 */
function buildLineData(bars, maValues) {
  const result = [];
  for (let i = 0; i < bars.length; i++) {
    if (maValues[i] !== null && maValues[i] !== undefined) {
      result.push({
        time: toUtcSeconds(bars[i].timestamp),
        value: maValues[i],
      });
    }
  }
  return result;
}

/**
 * Convert trades into LWC marker objects
 */
function buildTradeMarkers(trades, bars) {
  if (!trades || !bars || bars.length === 0) return [];

  const barIndex = buildBarIndex(bars);
  const markers = [];

  // Build ms→idx sorted array for fuzzy match
  const msArr = bars.map((b, i) => ({ ms: new Date(b.timestamp).getTime(), idx: i }));
  msArr.sort((a, b) => a.ms - b.ms);

  trades.forEach(trade => {
    let idx = barIndex.get(trade.timestamp);
    if (idx === undefined) {
      idx = barIndex.get(new Date(trade.timestamp).getTime());
    }
    if (idx === undefined) {
      // Binary search fallback
      const targetTime = new Date(trade.timestamp).getTime();
      let lo = 0, hi = msArr.length - 1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (msArr[mid].ms < targetTime) lo = mid + 1;
        else hi = mid - 1;
      }
      for (let k = Math.max(0, lo - 1); k <= Math.min(msArr.length - 1, lo + 1); k++) {
        if (Math.abs(msArr[k].ms - targetTime) < 3600000) {
          idx = msArr[k].idx;
          break;
        }
      }
    }

    if (idx !== undefined && isFinite(idx)) {
      const isBuy = trade.side === 'BUY';
      markers.push({
        time: toUtcSeconds(bars[idx].timestamp),
        position: isBuy ? 'belowBar' : 'aboveBar',
        color: isBuy ? '#48bb78' : '#fc8181',
        shape: isBuy ? 'arrowUp' : 'arrowDown',
        text: isBuy ? '买入' : '卖出',
      });
    }
  });

  // Sort markers by time (LWC requirement)
  markers.sort((a, b) => a.time - b.time);
  return markers;
}

/**
 * Convert signal annotations (buy/sell/neutral) into LWC marker objects
 */
function buildSignalMarkers(annotations, bars) {
  if (!annotations || !bars || bars.length === 0) return [];

  const barIndex = buildBarIndex(bars);
  const markers = [];
  const SIGNAL_TYPES = ['buy_signal', 'sell_signal', 'neutral_signal'];

  // Build ms→idx sorted array for fuzzy match
  const msArr = bars.map((b, i) => ({ ms: new Date(b.timestamp).getTime(), idx: i }));
  msArr.sort((a, b) => a.ms - b.ms);

  annotations.forEach(ann => {
    if (!SIGNAL_TYPES.includes(ann.type)) return;

    let idx = barIndex.get(ann.timestamp);
    if (idx === undefined) {
      idx = barIndex.get(new Date(ann.timestamp).getTime());
    }
    if (idx === undefined) {
      // Binary search fallback
      const targetTime = new Date(ann.timestamp).getTime();
      let lo = 0, hi = msArr.length - 1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (msArr[mid].ms < targetTime) lo = mid + 1;
        else hi = mid - 1;
      }
      for (let k = Math.max(0, lo - 1); k <= Math.min(msArr.length - 1, lo + 1); k++) {
        if (Math.abs(msArr[k].ms - targetTime) < 3600000) {
          idx = msArr[k].idx;
          break;
        }
      }
    }

    if (idx !== undefined && isFinite(idx)) {
      let shape, color, text, position;
      switch (ann.type) {
        case 'buy_signal':
          shape = 'arrowUp';
          color = '#48bb78';
          text = ann.data.label || '买入';
          position = 'belowBar';
          break;
        case 'sell_signal':
          shape = 'arrowDown';
          color = '#fc8181';
          text = ann.data.label || '卖出';
          position = 'aboveBar';
          break;
        case 'neutral_signal':
          shape = 'circle';
          color = '#a0aec0';
          text = ann.data.label || '中性';
          position = 'inBar';
          break;
      }
      markers.push({
        time: toUtcSeconds(bars[idx].timestamp),
        position,
        color,
        shape,
        text,
      });
    }
  });

  return markers;
}

/**
 * Merge trade markers and signal markers, sorted by time (LWC requirement)
 * Dedup: if same time + same position, keep trade marker (higher priority)
 */
function mergeMarkers(tradeMarkers, signalMarkers) {
  const merged = [...tradeMarkers];
  const timePosSet = new Set(tradeMarkers.map(m => `${m.time}_${m.position}`));

  signalMarkers.forEach(m => {
    const key = `${m.time}_${m.position}`;
    if (!timePosSet.has(key)) {
      merged.push(m);
    }
  });

  merged.sort((a, b) => a.time - b.time);
  return merged;
}

/**
 * Apply annotation-based price lines (horizontal lines, support/resistance)
 */
function applyAnnotationPriceLines(chart, candleSeries, data) {
  if (!data.annotations) return;

  const HORIZONTAL_TYPES = ['horizontal_line', 'support_zone', 'resistance_zone'];

  data.annotations.forEach(ann => {
    if (HORIZONTAL_TYPES.includes(ann.type) && ann.data?.price != null) {
      const price = ann.data.price;
      if (typeof price !== 'number' || !isFinite(price)) return;

      const colorMap = {
        horizontal_line: '#60a5fa',
        support_zone: '#48bb78',
        resistance_zone: '#fc8181',
      };

      candleSeries.createPriceLine({
        price,
        color: ann.data.color || colorMap[ann.type] || '#60a5fa',
        lineWidth: 1,
        lineStyle: 2, // dashed
        axisLabelVisible: true,
        title: ann.data.label || '',
      });
    }
  });
}

/**
 * Dispose K-line chart and cleanup
 * @param {Object} klineState - Return value from renderKLine()
 */
export function disposeKLine(klineState) {
  if (!klineState) return;
  if (klineState.resizeObserver) {
    klineState.resizeObserver.disconnect();
  }
  if (klineState.chart) {
    try { klineState.chart.remove(); } catch (e) { /* ignore */ }
  }
}

/**
 * Toggle zoom (fit content vs scroll to end)
 */
export function fitKLineContent(klineState) {
  if (klineState?.chart) {
    klineState.chart.timeScale().fitContent();
  }
}

/**
 * Reset zoom on K-line chart
 */
export function resetKLineZoom(klineState) {
  if (klineState?.chart) {
    klineState.chart.timeScale().setVisibleLogicalRange({ from: 0, to: undefined });
    klineState.chart.timeScale().fitContent();
  }
}

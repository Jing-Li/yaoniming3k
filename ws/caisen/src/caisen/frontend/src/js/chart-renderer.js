/**
 * Caisen Visualization - Chart Renderer
 * 图表渲染逻辑
 */

import { appState } from './app-state.js';
import { buildKLineOption, buildEquityOption } from './chart-builder.js';
import { DEBUG_CONFIG } from './constants.js';

// Track which chart instances have been wired for sync (avoids double-bind on re-render).
const _syncedCharts = new WeakSet();

// ==================== Performance Utilities ====================

/**
 * Debounce utility — delays execution until `delay` ms after the last call.
 * @param {Function} fn
 * @param {number} delay
 * @returns {Function}
 */
function debounce(fn, delay = 250) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

// Single debounced handler for all chart resizes (shared across render calls).
const _debouncedResize = debounce(() => {
    const charts = [
        appState.getChart(),
        appState.getEquityChart(),
        appState.getDrawdownChart(),
        appState.getHeatmapChart(),
        appState.getTradeDistributionChart()
    ];
    charts.forEach(c => c && c.resize());
}, 250);

let _resizeBound = false;
function ensureResizeHandler() {
    if (_resizeBound) return;
    _resizeBound = true;
    window.addEventListener('resize', _debouncedResize);
}

// ==================== Lazy Initialization ====================

// Track observers so we don't duplicate.
const _lazyObservers = new Map();

/**
 * Lazy-init a chart: only call `initFn` when `containerId` enters the viewport.
 * Falls back to immediate init if IntersectionObserver is not available.
 * @param {string} containerId - DOM id of the chart container
 * @param {Function} initFn - function to call once visible
 */
export function lazyInitChart(containerId, initFn) {
    const el = document.getElementById(containerId);
    if (!el) {
        // Container doesn't exist, skip.
        return;
    }

    // Disconnect previous observer for this container if any (e.g. re-render)
    if (_lazyObservers.has(containerId)) {
        _lazyObservers.get(containerId).disconnect();
        _lazyObservers.delete(containerId);
    }

    if (typeof IntersectionObserver === 'undefined') {
        // Fallback: init immediately
        initFn();
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                observer.disconnect();
                _lazyObservers.delete(containerId);
                initFn();
            }
        });
    }, { rootMargin: '200px' });

    observer.observe(el);
    _lazyObservers.set(containerId, observer);
}

/**
 * Render K-Line chart
 */
export function renderKLineChart() {
    const data = appState.getFilteredData();
    if (!data || !data.bars || data.bars.length === 0) {
        DEBUG_CONFIG.log('[KLine] 无数据，跳过渲染');
        return;
    }

    DEBUG_CONFIG.log('[KLine] 开始渲染, bars:', data.bars.length);

    const isZoomEnabled = appState.getIsZoomEnabled();
    const showMA = appState.getShowMA();
    const option = buildKLineOption({ data, isZoomEnabled, showMA });

    if (!option) {
        DEBUG_CONFIG.error('[KLine] buildKLineOption 返回 null');
        return;
    }

    const chart = appState.getChart();

    if (chart) {
        try {
            chart.setOption(option, true);
            DEBUG_CONFIG.log('[KLine] chart.setOption 完成');
        } catch (e) {
            DEBUG_CONFIG.error('[KLine] chart.setOption 失败:', e.message);
            handleChartError(option);
        }
    } else {
        try {
            const chartInstance = echarts.init(document.getElementById('kline-chart'));
            appState.setChart(chartInstance);
            chartInstance.setOption(option, true);
            DEBUG_CONFIG.log('[KLine] 新实例初始化完成');
        } catch (e) {
            DEBUG_CONFIG.error('[KLine] ECharts 初始化失败:', e.message);
            handleChartError(option);
        }
    }

    // Resize handler (shared debounced)
    ensureResizeHandler();
}

/**
 * Render equity chart
 */
export function renderEquityChart() {
    const data = appState.getFilteredData();
    if (!data || !data.equity_curve || data.equity_curve.length === 0) {
        DEBUG_CONFIG.log('[Equity] 无数据，跳过渲染');
        return;
    }

    const option = buildEquityOption({ data });
    if (!option) return;

    const equityChart = appState.getEquityChart();

    if (equityChart) {
        try {
            equityChart.setOption(option, true);
            DEBUG_CONFIG.log('[Equity] equityChart.setOption 完成');
        } catch (e) {
            DEBUG_CONFIG.error('[Equity] equityChart.setOption 失败:', e.message);
        }
    } else {
        try {
            const chartInstance = echarts.init(document.getElementById('equity-chart'));
            appState.setEquityChart(chartInstance);
            chartInstance.setOption(option, true);
            DEBUG_CONFIG.log('[Equity] 新实例初始化完成');
        } catch (e) {
            DEBUG_CONFIG.error('[Equity] ECharts 初始化失败:', e.message);
        }
    }

    // Resize handler (shared debounced)
    ensureResizeHandler();
}

/**
 * Handle chart error with fallback
 */
function handleChartError(option) {
    try {
        const fallbackOption = structuredClone(option);
        fallbackOption.series[0].markPoint = { data: [] };
        fallbackOption.series[0].markLine = { data: [] };

        let chart = appState.getChart();
        if (chart) {
            chart.setOption(fallbackOption, true);
        } else {
            chart = echarts.init(document.getElementById('kline-chart'));
            appState.setChart(chart);
            chart.setOption(fallbackOption, true);
        }
        DEBUG_CONFIG.log('[KLine] 简化配置成功');
    } catch (e2) {
        DEBUG_CONFIG.error('[KLine] 简化配置也失败:', e2.message);
    }
}

/**
 * Toggle zoom
 */
export function toggleZoom() {
    const isZoomEnabled = appState.toggleZoom();
    const btn = document.getElementById('btn-zoom');
    if (btn) {
        btn.classList.toggle('is-active', isZoomEnabled);
        btn.setAttribute('aria-pressed', String(isZoomEnabled));
    }
    renderKLineChart();
}

/**
 * Reset zoom on every linked chart.
 */
export function resetZoom() {
    [
        appState.getChart(),
        appState.getEquityChart(),
        appState.getDrawdownChart()
    ].forEach(chart => {
        if (chart) {
            chart.dispatchAction({ type: 'dataZoom', start: 0, end: 100 });
        }
    });
}

/**
 * Toggle equity visibility
 */
export function toggleEquity() {
    const isVisible = appState.toggleEquity();
    const wrapper = document.getElementById('equity-chart')?.parentElement;
    if (wrapper) {
        wrapper.style.display = isVisible ? 'block' : 'none';
    }
    const btn = document.getElementById('btn-equity');
    if (btn) {
        btn.classList.toggle('is-active', !isVisible);
        btn.setAttribute('aria-pressed', String(isVisible));
    }
}

/**
 * Toggle MA overlay on K-line chart
 */
export function toggleMA() {
    const show = appState.toggleMA();
    const btn = document.getElementById('btn-ma');
    if (btn) {
        btn.classList.toggle('is-active', show);
        btn.setAttribute('aria-pressed', String(show));
    }
    renderKLineChart();
}

/**
 * Wire dataZoom + axisPointer synchronization across the K-line, equity and
 * drawdown charts. Safe to call multiple times: only newly added chart
 * instances will have handlers wired (uses WeakSet to track bound charts).
 */
export function setupChartSync() {
    const charts = [
        appState.getChart(),
        appState.getEquityChart(),
        appState.getDrawdownChart()
    ].filter(Boolean);

    if (charts.length < 2) {
        DEBUG_CONFIG.log('[Sync] 图表实例不足，跳过联动');
        return;
    }

    let isSyncingZoom = false;
    let isSyncingPointer = false;

    charts.forEach((src, srcIdx) => {
        if (_syncedCharts.has(src)) return;
        _syncedCharts.add(src);

        // dataZoom sync
        src.on('dataZoom', (params) => {
            if (isSyncingZoom) return;
            isSyncingZoom = true;
            try {
                // Prefer batch entry (toolbox / slider produce batch); fallback to direct fields.
                let start;
                let end;
                if (params.batch && params.batch.length > 0) {
                    start = params.batch[0].start;
                    end = params.batch[0].end;
                } else {
                    start = params.start;
                    end = params.end;
                }
                if (start == null || end == null) return;
                charts.forEach((dst, dstIdx) => {
                    if (dstIdx === srcIdx) return;
                    try {
                        dst.dispatchAction({ type: 'dataZoom', start, end });
                    } catch (e) {
                        DEBUG_CONFIG.error('[Sync] dataZoom dispatch 失败:', e.message);
                    }
                });
            } finally {
                isSyncingZoom = false;
            }
        });

        // Crosshair / axis pointer sync
        src.on('updateAxisPointer', (event) => {
            if (isSyncingPointer) return;
            const axesInfo = event && event.axesInfo;
            if (!axesInfo || axesInfo.length === 0) return;
            const xInfo = axesInfo.find(a => a.axisDim === 'x');
            if (!xInfo) return;
            const xValue = xInfo.value;
            if (xValue == null) return;
            isSyncingPointer = true;
            try {
                charts.forEach((dst, dstIdx) => {
                    if (dstIdx === srcIdx) return;
                    try {
                        dst.dispatchAction({
                            type: 'updateAxisPointer',
                            currTrigger: 'mousemove',
                            x: xValue
                        });
                    } catch (e) {
                        // Some charts may not have a compatible axis; ignore.
                    }
                });
            } finally {
                isSyncingPointer = false;
            }
        });
    });

    DEBUG_CONFIG.log('[Sync] 图表联动已建立, charts:', charts.length);
}

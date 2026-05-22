/**
 * Caisen Visualization - Chart Renderer
 * 图表渲染逻辑
 */

import { appState } from './app-state.js';
import { buildKLineOption, buildEquityOption } from './chart-builder.js';
import { DEBUG_CONFIG } from './constants.js';

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
    const option = buildKLineOption({ data, isZoomEnabled });

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

    // Resize handler
    window.addEventListener('resize', () => {
        const chart = appState.getChart();
        chart && chart.resize();
    });
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

    // Resize handler
    window.addEventListener('resize', () => {
        const chart = appState.getEquityChart();
        chart && chart.resize();
    });
}

/**
 * Handle chart error with fallback
 */
function handleChartError(option) {
    try {
        const fallbackOption = JSON.parse(JSON.stringify(option));
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
        btn.classList.toggle('active', isZoomEnabled);
    }
    renderKLineChart();
}

/**
 * Reset zoom
 */
export function resetZoom() {
    const chart = appState.getChart();
    if (chart) {
        chart.dispatchAction({ type: 'dataZoom', start: 0, end: 100 });
    }

    const equityChart = appState.getEquityChart();
    if (equityChart) {
        equityChart.dispatchAction({ type: 'dataZoom', start: 0, end: 100 });
    }
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
}
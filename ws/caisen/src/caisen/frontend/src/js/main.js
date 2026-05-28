/**
 * Caisen Visualization - Application Entry
 * 应用入口点
 * 
 * 导出全局函数供 HTML 内联脚本使用
 */

import { appState } from './app-state.js';
import { PATTERN_COLORS, DEBUG_CONFIG } from './constants.js';
import { buildKLineOption, buildEquityOption, buildTooltipContent } from './chart-builder.js';
import { processAnnotations, processTrades, getAnnotationRenderer } from './chart-builder.js';
import { renderHeader, renderMetrics, renderTradesTable, renderPatternLegend, initDateInputs, showError, formatValue, formatTimestamp, calculateAnnualReturn } from './components.js';
import { renderKLineChart, renderEquityChart, toggleZoom, resetZoom, toggleEquity, toggleMA, setupChartSync } from './chart-renderer.js';
import { loadData, loadRun, showRunsList, hideRunsList, applyDateFilter } from './data-loader.js';
import { annotationFilterToggle, annotationFilterSelectAll, annotationFilterSelectNone, toggleAnnotationFilterPanel } from './annotation-filter.js';
import { renderHeatmapChart } from './heatmap-chart.js';
import { renderDrawdownChart } from './drawdown-chart.js';
import { renderTradeDistribution } from './trade-distribution.js';
import { renderVersionCompare, disposeVersionCompare, buildVersionCompareOption } from './version-compare.js';
import { getStrategyDisplayName, STRATEGY_DISPLAY_NAMES } from './constants.js';

// Make functions available globally for inline script
window.buildKLineOption = buildKLineOption;
window.applyDateFilter = applyDateFilter;
window.loadRun = loadRun;
window.showRunsList = showRunsList;
window.toggleZoom = toggleZoom;
window.resetZoom = resetZoom;
window.toggleEquity = toggleEquity;
window.toggleMA = toggleMA;
window.annotationFilterToggle = annotationFilterToggle;
window.annotationFilterSelectAll = annotationFilterSelectAll;
window.annotationFilterSelectNone = annotationFilterSelectNone;
window.toggleAnnotationFilterPanel = toggleAnnotationFilterPanel;

// Global handlers
window.onerror = function(message, source, lineno, colno, error) {
    DEBUG_CONFIG.error('JavaScript Error:', message, 'at', source, lineno + ':' + colno);
    if (error?.stack) {
        DEBUG_CONFIG.error('Stack:', error.stack);
    }
    return true;
};

window.onunhandledrejection = function(event) {
    DEBUG_CONFIG.error('Unhandled Promise Rejection:', event.reason);
};

console.log('[INIT] Caisen 可视化模块加载完成');

// Auto-init on DOMContentLoaded (only for report page)
document.addEventListener('DOMContentLoaded', () => {
    // Only auto-load if we have a run_id (report page)
    const runId = new URLSearchParams(window.location.search).get('run_id');
    if (runId) {
        console.log('[INIT] Report page detected, loading data for run:', runId);
        loadData();
    }
});

export {
    appState,
    PATTERN_COLORS,
    STRATEGY_DISPLAY_NAMES,
    getStrategyDisplayName,
    buildKLineOption,
    buildEquityOption,
    buildTooltipContent,
    processAnnotations,
    processTrades,
    getAnnotationRenderer,
    renderHeader,
    renderMetrics,
    renderTradesTable,
    renderPatternLegend,
    initDateInputs,
    renderKLineChart,
    renderEquityChart,
    toggleZoom,
    resetZoom,
    toggleEquity,
    toggleMA,
    setupChartSync,
    loadData,
    loadRun,
    showRunsList,
    hideRunsList,
    applyDateFilter,
    renderHeatmapChart,
    renderDrawdownChart,
    renderTradeDistribution,
    renderVersionCompare,
    disposeVersionCompare,
    buildVersionCompareOption
};

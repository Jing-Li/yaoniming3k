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
import { renderKLineChart, renderEquityChart, toggleZoom, resetZoom, toggleEquity } from './chart-renderer.js';
import { loadData, loadRun, showRunsList, hideRunsList, applyDateFilter } from './data-loader.js';

// Make functions available globally for inline script
window.buildKLineOption = buildKLineOption;
window.applyDateFilter = applyDateFilter;
window.loadRun = loadRun;
window.showRunsList = showRunsList;

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
    loadData,
    loadRun,
    showRunsList,
    hideRunsList,
    applyDateFilter
};
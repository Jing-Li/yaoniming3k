/**
 * Caisen Visualization - Application State
 * 统一的应用状态管理
 */

export const createAppState = () => {
    // Core state
    let chart = null;           // LWC kline chart state (from kline-chart.js)
    let klineState = null;      // Full LWC state object { chart, candleSeries, resizeObserver, ... }
    let equityChart = null;     // ECharts equity chart
    let heatmapChart = null;    // ECharts heatmap
    let drawdownChart = null;   // ECharts drawdown
    let tradeDistributionChart = null; // ECharts distribution
    let rawData = null;
    let filteredData = null;
    let isZoomEnabled = false;
    let isEquityVisible = true;
    let showMA = true;
    let annotationFilter = null; // Map<string, boolean> or null (null = show all)

    return {
        // Getters
        getChart: () => chart,
        getKlineState: () => klineState,
        getEquityChart: () => equityChart,
        getHeatmapChart: () => heatmapChart,
        getDrawdownChart: () => drawdownChart,
        getTradeDistributionChart: () => tradeDistributionChart,
        getRawData: () => rawData,
        getFilteredData: () => filteredData,
        getIsZoomEnabled: () => isZoomEnabled,
        getIsEquityVisible: () => isEquityVisible,
        getShowMA: () => showMA,
        getAnnotationFilter: () => annotationFilter,

        // Setters
        setChart: (instance) => { chart = instance; },
        setKlineState: (state) => { klineState = state; },
        setEquityChart: (instance) => { equityChart = instance; },
        setHeatmapChart: (instance) => { heatmapChart = instance; },
        setDrawdownChart: (instance) => { drawdownChart = instance; },
        setTradeDistributionChart: (instance) => { tradeDistributionChart = instance; },
        setRawData: (data) => { rawData = data; },
        setFilteredData: (data) => { filteredData = data; },
        setIsZoomEnabled: (enabled) => { isZoomEnabled = enabled; },
        setIsEquityVisible: (visible) => { isEquityVisible = visible; },
        setShowMA: (show) => { showMA = !!show; },
        setAnnotationFilter: (filter) => { annotationFilter = filter; },

        // Toggle methods
        toggleZoom: function() {
            isZoomEnabled = !isZoomEnabled;
            return isZoomEnabled;
        },
        toggleEquity: function() {
            isEquityVisible = !isEquityVisible;
            return isEquityVisible;
        },
        toggleMA: function() {
            showMA = !showMA;
            return showMA;
        },

        // Reset
        reset: function() {
            chart = null;
            klineState = null;
            equityChart = null;
            heatmapChart = null;
            drawdownChart = null;
            tradeDistributionChart = null;
            rawData = null;
            filteredData = null;
            isZoomEnabled = false;
            isEquityVisible = true;
            showMA = true;
            annotationFilter = null;
        }
    };
};

// Singleton instance for use across modules
export const appState = createAppState();
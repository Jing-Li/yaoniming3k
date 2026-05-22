/**
 * Caisen Visualization - Application State
 * 统一的应用状态管理
 */

export const createAppState = () => {
    // Core state
    let chart = null;
    let equityChart = null;
    let rawData = null;
    let filteredData = null;
    let isZoomEnabled = false;
    let isEquityVisible = true;

    return {
        // Getters
        getChart: () => chart,
        getEquityChart: () => equityChart,
        getRawData: () => rawData,
        getFilteredData: () => filteredData,
        getIsZoomEnabled: () => isZoomEnabled,
        getIsEquityVisible: () => isEquityVisible,

        // Setters
        setChart: (instance) => { chart = instance; },
        setEquityChart: (instance) => { equityChart = instance; },
        setRawData: (data) => { rawData = data; },
        setFilteredData: (data) => { filteredData = data; },
        setIsZoomEnabled: (enabled) => { isZoomEnabled = enabled; },
        setIsEquityVisible: (visible) => { isEquityVisible = visible; },

        // Toggle methods
        toggleZoom: function() {
            isZoomEnabled = !isZoomEnabled;
            return isZoomEnabled;
        },
        toggleEquity: function() {
            isEquityVisible = !isEquityVisible;
            return isEquityVisible;
        },

        // Reset
        reset: function() {
            chart = null;
            equityChart = null;
            rawData = null;
            filteredData = null;
            isZoomEnabled = false;
            isEquityVisible = true;
        }
    };
};

// Singleton instance for use across modules
export const appState = createAppState();
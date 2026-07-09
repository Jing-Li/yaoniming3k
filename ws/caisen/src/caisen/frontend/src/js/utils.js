/**
 * Caisen Visualization - Utility Functions
 * 工具函数库，提供数据处理、格式化等纯函数
 */

/**
 * Escape HTML special characters to prevent XSS injection.
 * @param {any} str - Value to escape (coerced to string)
 * @returns {string} Escaped string safe for innerHTML insertion
 */
export function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const s = String(str);
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return s.replace(/[&<>"']/g, c => map[c]);
}

/**
 * Format numeric value for display
 * @param {number|null|undefined} value - Value to format
 * @param {string} type - Format type: 'percent', 'currency', 'ratio'
 * @returns {string} Formatted value string
 */
export function formatValue(value, type = 'percent') {
    if (value === null || value === undefined || isNaN(value)) return '-';
    if (type === 'percent') {
        return (value * 100).toFixed(2) + '%';
    } else if (type === 'currency') {
        return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } else if (type === 'ratio') {
        if (!isFinite(value)) return '∞';
        return value.toFixed(2);
    }
    return value.toFixed(2);
}

/**
 * Format timestamp to locale string
 * @param {string|Date} ts - Timestamp to format
 * @returns {string} Formatted datetime string
 */
export function formatTimestamp(ts) {
    const date = new Date(ts);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Calculate annual return based on equity curve
 * @param {Object} rawData - Raw backtest data
 * @returns {number} Annual return as decimal
 */
export function calculateAnnualReturn(rawData) {
    if (!rawData || !rawData.equity_curve || rawData.equity_curve.length < 2) return 0;
    const equity = rawData.equity_curve;
    const initial = equity[0].equity;
    const final = equity[equity.length - 1].equity;
    if (initial <= 0) return 0;

    // Estimate days based on data frequency
    const days = equity.length;
    const freq = rawData.meta?.freq || '1d';
    const years = days / (freq === '1h' ? 250 * 24 : freq === '5m' ? 250 * 48 : 250);

    return Math.pow(final / initial, 1 / years) - 1;
}

/**
 * Check if a value is a valid finite number
 * @param {any} v - Value to check
 * @returns {boolean} True if valid finite number
 */
export function isFiniteNum(v) {
    return typeof v === 'number' && isFinite(v);
}

/**
 * Check if a coordinate point is valid
 * @param {number[]} c - Coordinate [x, y]
 * @returns {boolean} True if valid coordinate
 */
export function isValidCoordPoint(c) {
    return c && Array.isArray(c) && c.length >= 2 && isFiniteNum(c[0]) && isFiniteNum(c[1]);
}

/**
 * Check if a coordinate is valid
 * @param {number[]} c - Coordinate [x, y]
 * @returns {boolean} True if valid coordinate
 */
export function isValidCoord(c) {
    return c && isFiniteNum(c[0]) && isFiniteNum(c[1]);
}

/**
 * Filter valid markPoints (must have valid coord)
 * @param {Object[]} markPoints - Array of markPoint objects
 * @returns {Object[]} Filtered valid markPoints
 */
export function filterValidMarkPoints(markPoints) {
    return markPoints.filter(p => {
        return p && p.coord && isValidCoord(p.coord);
    });
}

/**
 * Filter valid markLines (yAxis format or coords format with 2+ points)
 * @param {Object[]} markLines - Array of markLine objects
 * @returns {Object[]} Filtered valid markLines
 */
export function filterValidMarkLines(markLines) {
    return markLines.filter(l => {
        if (!l) return false;
        // yAxis format (horizontal_line, support_zone, resistance_zone)
        if (typeof l.yAxis === 'number' && isFinite(l.yAxis)) {
            return true;
        }
        // coords format: must have at least 2 valid points
        if (l.coords && l.coords.length >= 2 && l.coords.every(isValidCoordPoint)) {
            return true;
        }
        return false;
    });
}

/**
 * Find bar by timestamp with fuzzy matching (within 1 hour for intraday data)
 * @param {Object[]} bars - Array of bar objects
 * @param {string|number} timestamp - Timestamp to search for
 * @returns {Object|null} Found bar or null
 */
export function findBarByTimestamp(bars, timestamp) {
    if (!timestamp) {
        return null;
    }
    const targetTime = new Date(timestamp).getTime();

    // Try exact match first
    let bar = bars.find(b => new Date(b.timestamp).getTime() === targetTime);

    if (!bar) {
        // Find closest bar within 1 hour for intraday data
        bar = bars.find(b => Math.abs(new Date(b.timestamp) - targetTime) < 3600000);
    }

    return bar;
}

/**
 * Apply date filter to data
 * @param {Object} data - Raw data object
 * @param {string} startDate - Start date string (YYYY-MM-DD)
 * @param {string} endDate - End date string (YYYY-MM-DD)
 * @returns {Object} Filtered data copy
 */
export function applyDateFilterToData(data, startDate, endDate) {
    const filteredData = structuredClone(data);

    if (startDate) {
        const start = new Date(startDate);
        filteredData.bars = filteredData.bars.filter(bar => new Date(bar.timestamp) >= start);
        filteredData.equity_curve = filteredData.equity_curve.filter(item => new Date(item.timestamp) >= start);
        filteredData.trades = filteredData.trades.filter(trade => new Date(trade.timestamp) >= start);
        filteredData.annotations = filteredData.annotations.filter(ann => new Date(ann.timestamp) >= start);
    }

    if (endDate) {
        const end = new Date(endDate);
        end.setHours(23, 59, 59);
        filteredData.bars = filteredData.bars.filter(bar => new Date(bar.timestamp) <= end);
        filteredData.equity_curve = filteredData.equity_curve.filter(item => new Date(item.timestamp) <= end);
        filteredData.trades = filteredData.trades.filter(trade => new Date(trade.timestamp) <= end);
        filteredData.annotations = filteredData.annotations.filter(ann => new Date(ann.timestamp) <= end);
    }

    return filteredData;
}
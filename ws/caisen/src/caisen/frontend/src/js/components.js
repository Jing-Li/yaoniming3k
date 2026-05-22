/**
 * Caisen Visualization - UI Components
 * UI 渲染组件
 */

import { appState } from './app-state.js';
import { PATTERN_COLORS } from './constants.js';

/**
 * Format numeric value for display
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
 * Calculate annual return
 */
export function calculateAnnualReturn(rawData) {
    if (!rawData || !rawData.equity_curve || rawData.equity_curve.length < 2) return 0;
    const equity = rawData.equity_curve;
    const initial = equity[0].equity;
    const final = equity[equity.length - 1].equity;
    if (initial <= 0) return 0;

    const days = equity.length;
    const freq = rawData.meta?.freq || '1d';
    const years = days / (freq === '1h' ? 250 * 24 : freq === '5m' ? 250 * 48 : 250);

    return Math.pow(final / initial, 1 / years) - 1;
}

// ==================== Render Components ====================

/**
 * Render header
 */
export function renderHeader() {
    const rawData = appState.getRawData();
    if (!rawData) return;

    const { meta } = rawData;
    const strategyNameEl = document.getElementById('strategy-name');
    const symbolEl = document.getElementById('symbol');
    const freqEl = document.getElementById('freq');
    const dateRangeEl = document.getElementById('date-range');

    if (strategyNameEl) strategyNameEl.textContent = meta.strategy_name || '-';
    if (symbolEl) symbolEl.textContent = meta.symbol || '-';
    if (freqEl) freqEl.textContent = meta.freq || '-';
    if (dateRangeEl) dateRangeEl.textContent = `${meta.start} ~ ${meta.end}`;
}

/**
 * Render metrics
 */
export function renderMetrics() {
    const rawData = appState.getRawData();
    if (!rawData) return;

    const { metrics } = rawData;
    const annualReturn = calculateAnnualReturn(rawData);

    const setValue = (id, value, type = 'percent') => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = formatValue(value, type);
    };

    const setClass = (id, condition) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.className = 'value ' + (condition ? 'positive' : 'negative');
    };

    setValue('total-return', metrics.total_return);
    setClass('total-return', metrics.total_return >= 0);

    setValue('annual-return', annualReturn);
    setClass('annual-return', annualReturn >= 0);

    setValue('max-drawdown', metrics.max_drawdown);
    setValue('sharpe-ratio', metrics.sharpe_ratio, 'ratio');
    setValue('win-rate', metrics.win_rate);
    setValue('profit-factor', metrics.profit_factor, 'ratio');
    setValue('total-trades', rawData.trades?.length || 0, 'number');

    // Sharpe ratio class
    const sharpeEl = document.getElementById('sharpe-ratio');
    if (sharpeEl) {
        sharpeEl.className = 'value ' + (metrics.sharpe_ratio > 0 ? 'positive' : metrics.sharpe_ratio < 0 ? 'negative' : 'neutral');
    }

    // Win rate class
    const winRateEl = document.getElementById('win-rate');
    if (winRateEl) {
        winRateEl.className = 'value ' + (metrics.win_rate >= 0.5 ? 'positive' : 'negative');
    }

    // Profit factor class
    const profitFactorEl = document.getElementById('profit-factor');
    if (profitFactorEl) {
        profitFactorEl.className = 'value ' + (metrics.profit_factor >= 1 ? 'positive' : 'negative');
    }
}

/**
 * Render trades table
 */
export function renderTradesTable() {
    const data = appState.getFilteredData();
    const tbody = document.getElementById('trades-body');
    if (!tbody) return;

    if (!data || !data.trades) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#718096;">暂无交易记录</td></tr>';
        return;
    }

    tbody.innerHTML = data.trades.map(trade => `
        <tr>
            <td>${formatTimestamp(trade.timestamp)}</td>
            <td><span class="side-badge ${trade.side.toLowerCase()}">${trade.side === 'BUY' ? '买入' : '卖出'}</span></td>
            <td>${trade.price.toLocaleString()}</td>
            <td>${trade.quantity}</td>
            <td>${trade.commission.toFixed(2)}</td>
        </tr>
    `).join('');
}

/**
 * Render pattern legend
 */
export function renderPatternLegend() {
    const legendEl = document.getElementById('pattern-legend');
    if (!legendEl) return;

    const data = appState.getFilteredData();
    if (!data || !data.annotations) {
        legendEl.innerHTML = '';
        return;
    }

    const patterns = new Map();
    data.annotations.forEach(a => {
        if (a.type === 'pattern_mark' && a.data.pattern) {
            patterns.set(a.data.pattern, a.data.label || a.data.pattern);
        }
    });

    if (patterns.size === 0) {
        legendEl.innerHTML = '';
        return;
    }

    const legendHtml = Array.from(patterns.entries()).map(([pattern, label]) => `
        <div class="legend-item">
            <div class="legend-line" style="background:${PATTERN_COLORS[pattern] || '#9f7aea'}"></div>
            <span>${label}</span>
        </div>
    `).join('');

    legendEl.innerHTML = legendHtml;
}

/**
 * Initialize date inputs
 */
export function initDateInputs() {
    const rawData = appState.getRawData();
    if (!rawData) return;

    const { meta } = rawData;
    const startDateEl = document.getElementById('start-date');
    const endDateEl = document.getElementById('end-date');

    if (startDateEl) startDateEl.value = meta.start ? meta.start.split('T')[0] : '';
    if (endDateEl) endDateEl.value = meta.end ? meta.end.split('T')[0] : '';
}

/**
 * Show error state
 */
export function showError(message) {
    document.querySelector('.container').innerHTML = `
        <div class="error">
            <div class="error-icon">!</div>
            <div>加载数据失败</div>
            <div style="font-size: 14px; color: #718096;">${message}</div>
            <button onclick="location.reload()">重试</button>
        </div>
    `;
}

/**
 * Show loading state
 */
export function showLoading() {
    const container = document.querySelector('.container');
    if (container) {
        container.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <div>加载中...</div>
            </div>
        `;
    }
}

/**
 * Show empty state
 */
export function showEmpty(message = '暂无数据') {
    const container = document.querySelector('.container');
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <div>${message}</div>
            </div>
        `;
    }
}

/**
 * Render all components
 */
export function renderAll() {
    renderHeader();
    renderMetrics();
    renderTradesTable();
    renderPatternLegend();
    initDateInputs();
}
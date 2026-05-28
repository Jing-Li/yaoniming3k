/**
 * Caisen Visualization - UI Components
 * UI 渲染组件
 */

import { appState } from './app-state.js';
import { PATTERN_COLORS } from './constants.js';

// ==================== Module State (pagination & sorting) ====================

const PAGE_SIZE = 20;
const VIRTUAL_ROW_HEIGHT = 44;
const VIRTUAL_BUFFER = 5;
const VIRTUAL_THRESHOLD = 100;
let _currentPage = 1;
let _sortField = 'timestamp';
let _sortDir = 'desc';
let _sparklineChart = null;

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

/**
 * Build trend arrow HTML for a numeric value.
 * Positive => green up, Negative => red down, Zero => nothing.
 */
export function trendArrow(value, { invert = false } = {}) {
    if (value === null || value === undefined || isNaN(value) || value === 0) return '';
    const positive = invert ? value < 0 : value > 0;
    const arrow = positive ? '↑' : '↓';
    const color = positive ? 'var(--color-success, #10b981)' : 'var(--color-danger, #ef4444)';
    return `<span class="trend-arrow" aria-hidden="true" style="display:inline-block;margin-left:6px;font-size:0.7em;font-weight:700;color:${color};vertical-align:middle;letter-spacing:0;">${arrow}</span>`;
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
 * Render the sparkline on the total-return metric card.
 */
export function renderSparkline(container, equityData) {
    if (!container || !equityData || equityData.length === 0) return null;
    if (typeof echarts === 'undefined') return null;

    if (_sparklineChart) {
        try { _sparklineChart.dispose(); } catch (e) { /* noop */ }
        _sparklineChart = null;
    }

    const chart = echarts.init(container, null, { renderer: 'canvas' });
    const initial = equityData[0]?.equity ?? 0;
    const final = equityData[equityData.length - 1]?.equity ?? 0;
    const isUp = final >= initial;
    const lineColor = isUp ? '#10b981' : '#ef4444';
    const areaTop = isUp ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.35)';
    const areaBottom = isUp ? 'rgba(16,185,129,0)' : 'rgba(239,68,68,0)';

    chart.setOption({
        animation: false,
        grid: { top: 2, bottom: 2, left: 0, right: 0 },
        xAxis: {
            show: false,
            type: 'category',
            boundaryGap: false,
            data: equityData.map(e => e.timestamp)
        },
        yAxis: {
            show: false,
            type: 'value',
            min: 'dataMin',
            max: 'dataMax'
        },
        tooltip: {
            trigger: 'axis',
            confine: true,
            backgroundColor: 'rgba(15,23,42,0.92)',
            borderColor: 'rgba(96,165,250,0.35)',
            textStyle: { color: '#f8fafc', fontSize: 11 },
            formatter: (params) => {
                if (!params || !params.length) return '';
                const p = params[0];
                return `${p.axisValueLabel || p.name}<br/>净值: <b>${Number(p.value).toFixed(2)}</b>`;
            }
        },
        series: [{
            type: 'line',
            data: equityData.map(e => e.equity),
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 1.5, color: lineColor },
            areaStyle: {
                color: {
                    type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: areaTop },
                        { offset: 1, color: areaBottom }
                    ]
                }
            }
        }]
    });

    _sparklineChart = chart;
    return chart;
}

/**
 * Render metrics
 */
export function renderMetrics() {
    const rawData = appState.getRawData();
    if (!rawData) return;

    const { metrics } = rawData;
    const annualReturn = calculateAnnualReturn(rawData);

    const setValueWithTrend = (id, value, type = 'percent', { invert = false, neutralZero = false } = {}) => {
        const el = document.getElementById(id);
        if (!el) return;
        const text = formatValue(value, type);
        const arrow = neutralZero ? '' : trendArrow(value, { invert });
        el.innerHTML = `<span class="metric-value-text">${text}</span>${arrow}`;
    };

    const setClass = (id, condition, baseClass = 'value metric-value-large') => {
        const el = document.getElementById(id);
        if (!el) return;
        el.className = baseClass + ' ' + (condition ? 'positive' : 'negative');
    };

    // Ensure all metric value elements have the large modifier class for emphasis.
    ['total-return', 'annual-return', 'max-drawdown', 'sharpe-ratio',
     'win-rate', 'profit-factor', 'total-trades'].forEach(id => {
        const el = document.getElementById(id);
        if (el && !el.classList.contains('metric-value-large')) {
            el.classList.add('metric-value-large');
            el.style.fontSize = el.style.fontSize || 'var(--font-size-2xl, 1.875rem)';
        }
    });

    setValueWithTrend('total-return', metrics.total_return, 'percent');
    setClass('total-return', metrics.total_return >= 0);

    setValueWithTrend('annual-return', annualReturn, 'percent');
    setClass('annual-return', annualReturn >= 0);

    // Max drawdown: always negative semantically; show down arrow if non-zero.
    setValueWithTrend('max-drawdown', metrics.max_drawdown, 'percent', { invert: true });
    const mddEl = document.getElementById('max-drawdown');
    if (mddEl) mddEl.className = 'value metric-value-large negative';

    setValueWithTrend('sharpe-ratio', metrics.sharpe_ratio, 'ratio');
    const sharpeEl = document.getElementById('sharpe-ratio');
    if (sharpeEl) {
        sharpeEl.className = 'value metric-value-large ' +
            (metrics.sharpe_ratio > 0 ? 'positive' : metrics.sharpe_ratio < 0 ? 'negative' : 'neutral');
    }

    setValueWithTrend('win-rate', metrics.win_rate, 'percent', { neutralZero: true });
    const winRateEl = document.getElementById('win-rate');
    if (winRateEl) {
        winRateEl.className = 'value metric-value-large ' +
            (metrics.win_rate >= 0.5 ? 'positive' : 'negative');
    }

    setValueWithTrend('profit-factor', metrics.profit_factor, 'ratio', { neutralZero: true });
    const profitFactorEl = document.getElementById('profit-factor');
    if (profitFactorEl) {
        profitFactorEl.className = 'value metric-value-large ' +
            (metrics.profit_factor >= 1 ? 'positive' : 'negative');
    }

    const tradesCount = rawData.trades?.length || 0;
    const tradesEl = document.getElementById('total-trades');
    if (tradesEl) {
        tradesEl.innerHTML = `<span class="metric-value-text">${tradesCount}</span>`;
        tradesEl.className = 'value metric-value-large neutral';
    }

    // Sparkline in total-return card.
    const sparkContainer = document.getElementById('sparkline-container');
    if (sparkContainer && rawData.equity_curve && rawData.equity_curve.length > 1) {
        renderSparkline(sparkContainer, rawData.equity_curve);
    }
}

// ==================== Trades Table ====================

/**
 * Compute per-trade pnl using FIFO matching of BUYs against SELLs.
 * Mutates a new array of trades, attaching `_pnl` to each SELL.
 */
function annotateTradesWithPnl(trades) {
    const queue = []; // FIFO queue of {qty, price, commission}
    return trades.map(t => {
        const clone = { ...t };
        if (t.side === 'BUY') {
            queue.push({
                qty: t.quantity,
                price: t.price,
                commission: t.commission || 0
            });
        } else if (t.side === 'SELL') {
            let remaining = t.quantity;
            let costBasis = 0;
            let buyCommission = 0;
            while (remaining > 1e-9 && queue.length > 0) {
                const head = queue[0];
                const consume = Math.min(head.qty, remaining);
                costBasis += consume * head.price;
                buyCommission += head.commission * (consume / head.qty);
                head.qty -= consume;
                head.commission -= head.commission * (consume / (head.qty + consume));
                remaining -= consume;
                if (head.qty <= 1e-9) queue.shift();
            }
            const matched = t.quantity - remaining;
            if (matched > 0) {
                const proceeds = matched * t.price;
                const sellCommission = (t.commission || 0) * (matched / t.quantity);
                clone._pnl = proceeds - costBasis - sellCommission - buyCommission;
            }
        }
        return clone;
    });
}

/**
 * Sort trades by a given field/direction. Returns a new array.
 */
export function sortTrades(trades, field, direction) {
    const dir = direction === 'asc' ? 1 : -1;
    return [...trades].sort((a, b) => {
        let va = a[field];
        let vb = b[field];
        if (field === 'timestamp') {
            va = new Date(va).getTime();
            vb = new Date(vb).getTime();
        }
        if (va == null) return 1;
        if (vb == null) return -1;
        if (va < vb) return -1 * dir;
        if (va > vb) return 1 * dir;
        return 0;
    });
}

/**
 * Build the pagination HTML and wire click handlers.
 * Strategy: «  1  2  3 … N  » with up to 7 numeric slots.
 */
export function renderPagination(totalItems, container, onChange) {
    if (!container) return;
    const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
    if (_currentPage > totalPages) _currentPage = totalPages;
    if (_currentPage < 1) _currentPage = 1;

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    const pages = [];
    const push = (p) => { if (!pages.includes(p)) pages.push(p); };
    push(1);
    for (let p = _currentPage - 1; p <= _currentPage + 1; p++) {
        if (p > 1 && p < totalPages) push(p);
    }
    if (totalPages > 1) push(totalPages);
    pages.sort((a, b) => a - b);

    const btnStyle = (active, disabled) => `
        min-width:34px;height:34px;padding:0 10px;
        display:inline-flex;align-items:center;justify-content:center;
        background:${active ? 'var(--gradient-primary, linear-gradient(135deg,#3b82f6,#8b5cf6))' : 'var(--glass-bg, rgba(15,23,42,0.7))'};
        color:${active ? '#fff' : 'var(--text-secondary, #cbd5e1)'};
        border:1px solid ${active ? 'transparent' : 'var(--glass-border, rgba(255,255,255,0.08))'};
        border-radius:var(--radius-sm, 6px);
        font-size:var(--font-size-sm, 14px);
        font-weight:${active ? '600' : '500'};
        font-feature-settings:"tnum" 1;
        cursor:${disabled ? 'not-allowed' : 'pointer'};
        opacity:${disabled ? '0.4' : '1'};
        transition:all var(--transition-fast, 150ms) ease;
    `;

    const parts = [];
    parts.push(`<button class="page-btn page-prev" ${_currentPage === 1 ? 'disabled' : ''} style="${btnStyle(false, _currentPage === 1)}" aria-label="上一页">‹</button>`);

    let prev = 0;
    for (const p of pages) {
        if (p - prev > 1) {
            parts.push(`<span style="padding:0 6px;color:var(--text-muted, #64748b);">…</span>`);
        }
        parts.push(`<button class="page-btn page-num" data-page="${p}" style="${btnStyle(p === _currentPage, false)}">${p}</button>`);
        prev = p;
    }

    parts.push(`<button class="page-btn page-next" ${_currentPage === totalPages ? 'disabled' : ''} style="${btnStyle(false, _currentPage === totalPages)}" aria-label="下一页">›</button>`);

    const info = `<span style="margin-left:var(--spacing-md, 12px);color:var(--text-muted, #64748b);font-size:var(--font-size-xs, 12px);font-feature-settings:'tnum' 1;">第 ${_currentPage} / ${totalPages} 页 · 共 ${totalItems} 条</span>`;
    container.innerHTML = parts.join('') + info;

    // Wire events
    container.querySelectorAll('.page-num').forEach(btn => {
        btn.addEventListener('click', () => {
            _currentPage = parseInt(btn.dataset.page, 10);
            onChange && onChange();
        });
    });
    const prevBtn = container.querySelector('.page-prev');
    const nextBtn = container.querySelector('.page-next');
    if (prevBtn && !prevBtn.disabled) prevBtn.addEventListener('click', () => {
        _currentPage = Math.max(1, _currentPage - 1);
        onChange && onChange();
    });
    if (nextBtn && !nextBtn.disabled) nextBtn.addEventListener('click', () => {
        _currentPage = Math.min(totalPages, _currentPage + 1);
        onChange && onChange();
    });
}

/**
 * Render a friendly empty-state row inside trades-body.
 */
function renderTradesEmpty(tbody, colspan = 6) {
    tbody.innerHTML = `
        <tr>
            <td colspan="${colspan}" style="padding:var(--spacing-2xl, 48px) var(--spacing-md, 16px);text-align:center;">
                <div style="display:flex;flex-direction:column;align-items:center;gap:var(--spacing-sm, 8px);color:var(--text-muted, #64748b);">
                    <div style="font-size:2.5rem;opacity:0.55;line-height:1;">⌛</div>
                    <div style="font-size:var(--font-size-sm, 14px);">暂无交易记录</div>
                    <div style="font-size:var(--font-size-xs, 12px);opacity:0.7;">当前回测未触发任何成交</div>
                </div>
            </td>
        </tr>
    `;
}

/**
 * Update the sort icon indicators on table headers.
 */
function updateSortIndicators() {
    const headRow = document.getElementById('trades-thead-row');
    if (!headRow) return;
    headRow.querySelectorAll('th.sortable').forEach(th => {
        const key = th.dataset.sortKey;
        const icon = th.querySelector('.sort-icon');
        if (!icon) return;
        th.style.cursor = 'pointer';
        th.style.userSelect = 'none';
        if (key === _sortField) {
            icon.textContent = _sortDir === 'asc' ? ' ▲' : ' ▼';
            icon.style.color = 'var(--color-neutral, #3b82f6)';
            icon.style.fontSize = '0.7em';
            th.style.color = 'var(--text-primary, #f8fafc)';
        } else {
            icon.textContent = ' ⇅';
            icon.style.color = 'var(--text-muted, #64748b)';
            icon.style.opacity = '0.4';
            icon.style.fontSize = '0.7em';
            th.style.color = '';
        }
    });
}

/**
 * Attach sorting click handlers to the table head (idempotent).
 * @param {HTMLElement} [headRow] - optional thead row element; defaults to #trades-thead-row
 */
function attachSortHandlers(headRow) {
    const row = headRow || document.getElementById('trades-thead-row');
    if (!row || row.dataset.sortBound) return;
    row.dataset.sortBound = '1';
    row.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const key = th.dataset.sortKey;
            if (!key) return;
            if (_sortField === key) {
                _sortDir = _sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                _sortField = key;
                _sortDir = key === 'timestamp' ? 'desc' : 'asc';
            }
            _currentPage = 1;
            renderTradesTable();
        });
    });
}

/**
 * Render trades summary row.
 */
function renderTradesSummary(trades) {
    const el = document.getElementById('trades-summary');
    if (!el) return;
    if (!trades || trades.length === 0) {
        el.innerHTML = '';
        return;
    }
    const buys = trades.filter(t => t.side === 'BUY').length;
    const sells = trades.filter(t => t.side === 'SELL').length;
    const totalCommission = trades.reduce((s, t) => s + (t.commission || 0), 0);

    const stat = (label, value, color = 'var(--text-primary, #f8fafc)') => `
        <span style="display:inline-flex;align-items:center;gap:var(--spacing-xs, 4px);">
            <span style="text-transform:uppercase;letter-spacing:0.06em;color:var(--text-muted, #64748b);font-size:0.72rem;">${label}</span>
            <span style="color:${color};font-weight:600;font-feature-settings:'tnum' 1;">${value}</span>
        </span>
    `;

    el.innerHTML = [
        stat('总成交', trades.length),
        stat('买入', buys, 'var(--color-up, #10b981)'),
        stat('卖出', sells, 'var(--color-down, #ef4444)'),
        stat('总手续费', totalCommission.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
    ].join('');
}

/**
 * Render trades table with sorting + pagination + pnl colorization.
 * Uses virtual scrolling when trade count exceeds VIRTUAL_THRESHOLD.
 */
export function renderTradesTable() {
    const data = appState.getFilteredData();
    const tbody = document.getElementById('trades-body');
    const paginationEl = document.getElementById('trades-pagination');
    if (!tbody) return;

    attachSortHandlers();
    updateSortIndicators();

    if (!data || !data.trades || data.trades.length === 0) {
        renderTradesEmpty(tbody, 6);
        renderTradesSummary([]);
        if (paginationEl) paginationEl.innerHTML = '';
        return;
    }

    // PnL annotation must be done on chronological order to be meaningful.
    const chronological = [...data.trades].sort((a, b) =>
        new Date(a.timestamp) - new Date(b.timestamp));
    const annotated = annotateTradesWithPnl(chronological);

    renderTradesSummary(annotated);

    const sorted = sortTrades(annotated, _sortField, _sortDir);

    // Virtual scrolling for large datasets
    if (sorted.length > VIRTUAL_THRESHOLD) {
        if (paginationEl) paginationEl.innerHTML = '';
        renderVirtualTable(sorted, tbody);
        return;
    }

    // Standard pagination for smaller datasets
    const start = (_currentPage - 1) * PAGE_SIZE;
    const pageRows = sorted.slice(start, start + PAGE_SIZE);

    tbody.innerHTML = pageRows.map(trade => renderTradeRow(trade)).join('');

    if (paginationEl) {
        renderPagination(sorted.length, paginationEl, () => renderTradesTable());
    }
}

/**
 * Render a single trade row HTML string.
 */
function renderTradeRow(trade) {
    const isSell = trade.side === 'SELL';
    const pnl = trade._pnl;
    const hasPnl = isSell && pnl !== undefined && pnl !== null && !isNaN(pnl);
    const pnlPositive = hasPnl && pnl >= 0;
    const rowBg = isSell && hasPnl
        ? (pnlPositive ? 'background:rgba(16,185,129,0.08);' : 'background:rgba(239,68,68,0.08);')
        : '';
    const pnlCell = hasPnl
        ? `<span style="color:${pnlPositive ? 'var(--color-success, #10b981)' : 'var(--color-danger, #ef4444)'};font-weight:600;font-feature-settings:'tnum' 1;">${pnlPositive ? '+' : ''}${pnl.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>`
        : '<span style="color:var(--text-muted, #64748b);">\u2014</span>';
    return `
        <tr style="${rowBg}height:${VIRTUAL_ROW_HEIGHT}px;">
            <td>${formatTimestamp(trade.timestamp)}</td>
            <td><span class="side-badge ${trade.side.toLowerCase()}">${trade.side === 'BUY' ? '\u4e70\u5165' : '\u5356\u51fa'}</span></td>
            <td>${trade.price.toLocaleString()}</td>
            <td>${trade.quantity.toLocaleString('zh-CN', { maximumFractionDigits: 4 })}</td>
            <td>${(trade.commission || 0).toFixed(2)}</td>
            <td>${pnlCell}</td>
        </tr>
    `;
}

/**
 * Virtual scrolling for large trade tables (>100 rows).
 * Only renders visible rows + buffer for performance.
 */
function renderVirtualTable(trades, container) {
    const totalHeight = trades.length * VIRTUAL_ROW_HEIGHT;

    // Build wrapper structure
    const scrollWrapper = document.createElement('div');
    scrollWrapper.className = 'virtual-scroll-wrapper';
    scrollWrapper.style.cssText = `height:480px;overflow-y:auto;`;

    const spacer = document.createElement('div');
    spacer.style.cssText = `height:${totalHeight}px;position:relative;`;

    const viewport = document.createElement('table');
    viewport.className = 'virtual-viewport';
    viewport.style.cssText = `position:absolute;width:100%;border-collapse:collapse;`;

    scrollWrapper.appendChild(spacer);
    spacer.appendChild(viewport);

    const visibleCount = Math.ceil(480 / VIRTUAL_ROW_HEIGHT);

    function updateVisibleRows() {
        const scrollTop = scrollWrapper.scrollTop;
        const startIdx = Math.max(0, Math.floor(scrollTop / VIRTUAL_ROW_HEIGHT) - VIRTUAL_BUFFER);
        const endIdx = Math.min(trades.length, startIdx + visibleCount + VIRTUAL_BUFFER * 2);

        viewport.style.top = (startIdx * VIRTUAL_ROW_HEIGHT) + 'px';
        viewport.innerHTML = trades.slice(startIdx, endIdx)
            .map(trade => renderTradeRow(trade)).join('');
    }

    scrollWrapper.addEventListener('scroll', () => requestAnimationFrame(updateVisibleRows));

    // Replace container content - the container is tbody, but we need to go up
    // to the table wrapper level for proper virtual scroll
    const tableEl = container.closest('table');
    const tableParent = tableEl ? tableEl.parentElement : container.parentElement;
    if (!tableParent) return;

    // Preserve the thead
    const thead = tableEl ? tableEl.querySelector('thead') : null;
    const theadHTML = thead ? thead.outerHTML : '';

    // Create a fixed header + virtual body structure
    const wrapper = document.createElement('div');
    wrapper.className = 'virtual-table-container';

    if (theadHTML) {
        const headerTable = document.createElement('table');
        headerTable.className = tableEl ? tableEl.className : '';
        headerTable.innerHTML = theadHTML;
        headerTable.style.cssText = 'width:100%;border-collapse:collapse;table-layout:fixed;';
        wrapper.appendChild(headerTable);

        // Re-attach sort handlers to the cloned thead
        const newHeadRow = headerTable.querySelector('#trades-thead-row');
        if (newHeadRow) {
            newHeadRow.dataset.sortBound = '';
            attachSortHandlers(newHeadRow);
        }
    }

    wrapper.appendChild(scrollWrapper);

    // Replace the original table
    if (tableEl) {
        tableEl.style.display = 'none';
        // Remove previously inserted virtual container if any
        const prev = tableParent.querySelector('.virtual-table-container');
        if (prev) prev.remove();
        tableParent.appendChild(wrapper);
    } else {
        container.innerHTML = '';
        container.appendChild(scrollWrapper);
    }

    // Initial render
    updateVisibleRows();
}

/**
 * Render pattern legend. Hides annotation panels when no annotations exist.
 */
export function renderPatternLegend() {
    const legendEl = document.getElementById('pattern-legend');
    const filterPanel = document.getElementById('annotation-filter-panel');

    const data = appState.getFilteredData();
    const annotations = data?.annotations || [];

    if (!legendEl) return;
    if (annotations.length === 0) {
        legendEl.innerHTML = '';
        if (filterPanel) filterPanel.style.display = 'none';
        return;
    }
    if (filterPanel) filterPanel.style.display = '';

    const patterns = new Map();
    annotations.forEach(a => {
        if (a.type === 'pattern_mark' && a.data.pattern) {
            patterns.set(a.data.pattern, a.data.label || a.data.pattern);
        }
    });

    if (patterns.size === 0) {
        legendEl.innerHTML = '';
        return;
    }

    legendEl.innerHTML = Array.from(patterns.entries()).map(([pattern, label]) => `
        <div class="legend-item">
            <div class="legend-line" style="background:${PATTERN_COLORS[pattern] || '#9f7aea'}"></div>
            <span>${label}</span>
        </div>
    `).join('');
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
    // Reset pagination whenever the underlying data changes.
    _currentPage = 1;
    renderHeader();
    renderMetrics();
    renderTradesTable();
    renderPatternLegend();
    initDateInputs();
}

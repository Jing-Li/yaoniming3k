/**
 * Caisen Visualization - Data Loader
 * 数据加载逻辑
 */

import { appState } from './app-state.js';
import { showError, renderAll } from './components.js';
import { renderKLineChart, renderEquityChart, setupChartSync, lazyInitChart } from './chart-renderer.js';
import { renderTradesTable, renderPatternLegend, initDateInputs } from './components.js';
import { DEBUG_CONFIG } from './constants.js';
import { buildFilterPanel } from './annotation-filter.js';
import { renderHeatmapChart } from './heatmap-chart.js';
import { renderDrawdownChart } from './drawdown-chart.js';
import { renderTradeDistribution } from './trade-distribution.js';
import { escapeHtml } from './utils.js';

// ==================== Data Cache ====================
const dataCache = new Map();

/**
 * Get data URL from query params
 */
function getDataUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('data') || './data.json';
}

/**
 * Get API base URL
 */
function getApiBase() {
    const runId = new URLSearchParams(window.location.search).get('run_id');
    if (runId) {
        return `/api/runs/${runId}/visualization`;
    }
    return null;
}

/**
 * Show runs list
 */
export function showRunsList() {
    const runsPanel = document.getElementById('runs-panel');
    if (runsPanel) runsPanel.classList.add('visible');
    const header = document.querySelector('.header');
    if (header) header.style.display = 'none';
    const metricsPanel = document.getElementById('metrics-panel');
    if (metricsPanel) metricsPanel.style.display = 'none';
    document.querySelectorAll('.chart-container').forEach(el => el.style.display = 'none');
    const tradesPanel = document.querySelector('.trades-panel');
    if (tradesPanel) tradesPanel.style.display = 'none';
    const backLink = document.getElementById('back-link');
    if (backLink) backLink.style.display = 'none';

    loadRunsList();
}

/**
 * Hide runs list, show report
 */
export function hideRunsList() {
    document.getElementById('runs-panel')?.classList.remove('visible');
    const header = document.querySelector('.header');
    if (header) header.style.display = 'flex';
    const metricsPanel = document.getElementById('metrics-panel');
    if (metricsPanel) metricsPanel.style.display = 'grid';
    document.querySelectorAll('.chart-container').forEach(el => el.style.display = 'block');
    const tradesPanel = document.querySelector('.trades-panel');
    if (tradesPanel) tradesPanel.style.display = 'block';
    const backLink = document.getElementById('back-link');
    if (backLink) backLink.style.display = 'block';
}

/**
 * Load runs list from API
 */
async function loadRunsList() {
    try {
        const response = await fetch('/api/runs');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const runsList = document.getElementById('runs-list');
        if (data.runs && data.runs.length > 0) {
            runsList.innerHTML = data.runs.map(run => {
                const safeId = escapeHtml(run.run_id);
                const safeName = escapeHtml(run.strategy_name);
                return `
                <div class="run-item" onclick="loadRun('${safeId}')">
                    <div class="run-info">
                        <div class="run-id">${safeName}</div>
                        <div class="run-meta">${safeId} · ${new Date(run.created_at).toLocaleString('zh-CN')}</div>
                    </div>
                    <div class="run-actions">
                        <button class="run-btn" onclick="event.stopPropagation(); loadRun('${safeId}')">查看</button>
                    </div>
                </div>
            `;}).join('');
        } else {
            runsList.innerHTML = '<div class="no-runs">暂无回测记录</div>';
        }
    } catch (error) {
        document.getElementById('runs-list').innerHTML = `<div class="no-runs">加载失败: ${escapeHtml(error.message)}</div>`;
    }
}

/**
 * Load specific run
 */
export function loadRun(runId) {
    const url = new URL(window.location);
    url.searchParams.set('run_id', runId);
    window.history.pushState({}, '', url);
    loadData();
    hideRunsList();
}

/**
 * 验证可视化数据是否可用
 * @param {object} data
 * @returns {{valid: boolean, message: string}}
 */
export function validateVisualizationData(data) {
    if (!data) return { valid: false, message: '未获取到数据' };
    if (!Array.isArray(data.bars) || data.bars.length === 0) {
        return { valid: false, message: '无K线数据，无法显示蜡烛图' };
    }
    const firstBar = data.bars[0];
    const requiredFields = ['timestamp', 'open', 'high', 'low', 'close'];
    const missing = requiredFields.filter(f => firstBar[f] === undefined || firstBar[f] === null);
    if (missing.length > 0) {
        return { valid: false, message: `K线数据格式不完整，缺少: ${missing.join(', ')}` };
    }
    return { valid: true, message: '' };
}

/**
 * 展示数据不可用的友好提示，并隐藏原有图表区域
 * @param {string} message
 */
export function showDataError(message) {
    // 隐藏原有图表与周边面板
    document.querySelectorAll('.chart-container').forEach(c => { c.style.display = 'none'; });
    const metricsPanel = document.getElementById('metrics-panel');
    if (metricsPanel) metricsPanel.style.display = 'none';
    const tradesPanel = document.querySelector('.trades-panel');
    if (tradesPanel) tradesPanel.style.display = 'none';

    // 防止重复插入
    document.querySelectorAll('.data-error').forEach(el => el.remove());

    const errorDiv = document.createElement('div');
    errorDiv.className = 'data-error';
    errorDiv.innerHTML = `
        <div style="text-align:center; padding:60px 20px; color:var(--text-secondary);">
            <div style="font-size:48px; margin-bottom:16px;">📊</div>
            <h3 style="color:var(--text-primary); margin-bottom:8px;">数据不可用</h3>
            <p>${message}</p>
            <p style="margin-top:12px; font-size:var(--font-size-sm); color:var(--text-muted);">
                该回测记录可能数据不完整或已损坏
            </p>
            <a href="/" style="display:inline-block; margin-top:20px; padding:8px 20px;
               background:var(--glass-bg); border:1px solid var(--border-default);
               border-radius:var(--radius-md); color:var(--text-primary); text-decoration:none;">
                ← 返回列表
            </a>
        </div>
    `;

    const main = document.querySelector('.report-content')
        || document.querySelector('main')
        || document.body;
    main.prepend(errorDiv);
}

/**
 * Load data from API or local file
 */
export async function loadData() {
    try {
        const runId = new URLSearchParams(window.location.search).get('run_id');

        if (!runId) {
            // No run_id means we're on the list page, which handles its own rendering
            return;
        }

        // Check cache first
        let rawData;
        if (dataCache.has(runId)) {
            DEBUG_CONFIG.log('[Data] 命中缓存:', runId);
            rawData = dataCache.get(runId);
        } else {
            const apiBase = getApiBase();

            if (apiBase && window.location.host) {
                const response = await fetch(apiBase);
                if (!response.ok) {
                    throw new Error(`API ${response.status}: ${response.statusText}`);
                }
                rawData = await response.json();
            } else {
                const url = getDataUrl();
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                rawData = await response.json();
            }

            // Store in cache
            dataCache.set(runId, rawData);
            DEBUG_CONFIG.log('[Data] 已缓存:', runId);
        }

        // 数据有效性验证：不合法的数据不进入渲染流程
        const validation = validateVisualizationData(rawData);
        if (!validation.valid) {
            DEBUG_CONFIG.error('[Data] 数据验证失败:', validation.message);
            hideRunsList();
            showDataError(validation.message);
            return;
        }

        appState.setRawData(rawData);
        appState.setFilteredData(structuredClone(rawData));

        hideRunsList();
        renderAll();
        renderKLineChart();
        renderEquityChart();
        renderTradesTable();
        renderPatternLegend();
        initDateInputs();
        buildFilterPanel(rawData.annotations);

        // Lazy-load non-first-screen charts (drawdown, heatmap, distribution)
        lazyInitChart('drawdown-chart', () => renderDrawdownChart());
        lazyInitChart('heatmap-chart', () => renderHeatmapChart());
        lazyInitChart('trade-distribution-chart', () => renderTradeDistribution());

        // After all charts are initialized, wire up cross-chart synchronization
        // (idempotent: only binds the first time it's called).
        setupChartSync();
    } catch (error) {
        DEBUG_CONFIG.error('[Data] 加载失败:', error.message);
        showError(error.message);
    }
}

/**
 * Apply date filter
 */
export function applyDateFilter() {
    const startDate = document.getElementById('start-date')?.value;
    const endDate = document.getElementById('end-date')?.value;
    const rawData = appState.getRawData();

    if (!rawData) return;

    const filteredData = structuredClone(rawData);

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

    appState.setFilteredData(filteredData);

    renderKLineChart();
    renderEquityChart();
    renderTradesTable();
    renderPatternLegend();
    buildFilterPanel(filteredData.annotations);
    renderDrawdownChart();
    renderHeatmapChart();
    renderTradeDistribution();
}
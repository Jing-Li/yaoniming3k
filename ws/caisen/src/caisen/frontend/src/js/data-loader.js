/**
 * Caisen Visualization - Data Loader
 * 数据加载逻辑
 */

import { appState } from './app-state.js';
import { showError, renderAll } from './components.js';
import { renderKLineChart, renderEquityChart } from './chart-renderer.js';
import { renderTradesTable, renderPatternLegend, initDateInputs } from './components.js';
import { DEBUG_CONFIG } from './constants.js';

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
            runsList.innerHTML = data.runs.map(run => `
                <div class="run-item" onclick="loadRun('${run.run_id}')">
                    <div class="run-info">
                        <div class="run-id">${run.strategy_name}</div>
                        <div class="run-meta">${run.run_id} · ${new Date(run.created_at).toLocaleString('zh-CN')}</div>
                    </div>
                    <div class="run-actions">
                        <button class="run-btn" onclick="event.stopPropagation(); loadRun('${run.run_id}')">查看</button>
                    </div>
                </div>
            `).join('');
        } else {
            runsList.innerHTML = '<div class="no-runs">暂无回测记录</div>';
        }
    } catch (error) {
        document.getElementById('runs-list').innerHTML = `<div class="no-runs">加载失败: ${error.message}</div>`;
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
 * Load data from API or local file
 */
export async function loadData() {
    try {
        const runId = new URLSearchParams(window.location.search).get('run_id');

        if (!runId) {
            // No run_id means we're on the list page, which handles its own rendering
            return;
        }

        const apiBase = getApiBase();
        let rawData;

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

        appState.setRawData(rawData);
        appState.setFilteredData(JSON.parse(JSON.stringify(rawData)));

        hideRunsList();
        renderAll();
        renderKLineChart();
        renderEquityChart();
        renderTradesTable();
        renderPatternLegend();
        initDateInputs();
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

    const filteredData = JSON.parse(JSON.stringify(rawData));

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
}
/**
 * Caisen Visualization - Runs List Page
 * 回测列表页面逻辑
 */

import { formatValue, formatTimestamp } from './components.js';
import { appState } from './app-state.js';
import { getStrategyDisplayName } from './constants.js';
import { renderVersionCompare, disposeVersionCompare } from './version-compare.js';
import { escapeHtml } from './utils.js';

// ==================== Module State ====================

let _allRuns = [];            // full list cached after fetch
let _searchQuery = '';        // current search filter
const _sparkCharts = new Map(); // run_id -> echarts instance
const _compareCharts = new Map(); // strategy name -> echarts instance
const _versionIndex = new Map();  // run_id -> 'vN' label
const _strategyRunIndex = new Map(); // strategy_name -> sorted runs (asc)
const SPARKLINE_LIMIT = 10;   // only auto-load mini charts for the first N runs

/**
 * Group runs by strategy name
 */
function groupByStrategy(runs) {
    const groups = {};
    runs.forEach(run => {
        const key = run.strategy_name || 'Unknown';
        if (!groups[key]) {
            groups[key] = [];
        }
        groups[key].push(run);
    });
    // Sort groups by latest run date
    return Object.entries(groups).sort((a, b) => {
        const aLatest = Math.max(...a[1].map(r => new Date(r.created_at).getTime()));
        const bLatest = Math.max(...b[1].map(r => new Date(r.created_at).getTime()));
        return bLatest - aLatest;
    }).reduce((acc, [key, value]) => {
        acc[key] = value;
        return acc;
    }, {});
}

/**
 * Get metric display value with appropriate class
 */
function getMetricDisplay(metrics, key, defaultValue = '-') {
    if (!metrics || metrics[key] === undefined) return { value: defaultValue, class: 'neutral' };
    const val = metrics[key];
    if (key === 'total_return' || key === 'annual_return') {
        return {
            value: formatValue(val, 'percent'),
            class: val >= 0 ? 'positive' : 'negative'
        };
    }
    if (key === 'max_drawdown') {
        return {
            value: formatValue(val, 'percent'),
            class: 'negative'
        };
    }
    if (key === 'sharpe_ratio' || key === 'profit_factor') {
        return {
            value: formatValue(val, 'ratio'),
            class: val > 0 ? 'positive' : 'negative'
        };
    }
    return { value: val, class: 'neutral' };
}

/**
 * Get strategy icon based on strategy display (form) name first, then raw name.
 */
function getStrategyIcon(strategyName) {
    const display = getStrategyDisplayName(strategyName);
    const formIcons = {
        'Phoenix': '🔥',
        'Tide': '🌊',
        'Eagle': '🦅',
        'Storm': '⚡',
        'Anchor': '⚓',
    };
    if (formIcons[display]) return formIcons[display];

    const fallbacks = {
        '蔡森策略': '📈',
        'CaiSen': '📈',
        'MACD': '📉',
        'MA': '📊',
    };
    for (const [key, icon] of Object.entries(fallbacks)) {
        if (strategyName && strategyName.includes(key)) return icon;
    }
    return '🎯';
}

/**
 * Compute version label (v0, v1, ...) for a single run within its strategy group.
 * The earliest run (by created_at, fallback to run_id) is v0.
 */
export function getVersionLabel(runs, currentRun) {
    if (!Array.isArray(runs) || !currentRun) return 'v0';
    const sorted = [...runs].sort((a, b) => {
        const timeA = a?.created_at || a?.run_id || '';
        const timeB = b?.created_at || b?.run_id || '';
        return timeA.localeCompare(timeB);
    });
    const index = sorted.findIndex(r => r.run_id === currentRun.run_id);
    return `v${index < 0 ? 0 : index}`;
}

/**
 * Build per-strategy version index from the full run list, so that version
 * numbering remains stable across search filtering.
 */
function rebuildVersionIndex(runs) {
    _versionIndex.clear();
    _strategyRunIndex.clear();

    const byStrategy = {};
    runs.forEach(run => {
        const key = run.strategy_name || 'Unknown';
        (byStrategy[key] = byStrategy[key] || []).push(run);
    });

    Object.entries(byStrategy).forEach(([strategy, group]) => {
        const sorted = [...group].sort((a, b) => {
            const ta = a?.created_at || a?.run_id || '';
            const tb = b?.created_at || b?.run_id || '';
            return ta.localeCompare(tb);
        });
        _strategyRunIndex.set(strategy, sorted);
        sorted.forEach((run, idx) => {
            _versionIndex.set(run.run_id, `v${idx}`);
        });
    });
}

/**
 * Format date to relative time
 */
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 7) return `${days} 天前`;

    return date.toLocaleDateString('zh-CN');
}

/**
 * Render hero stats (uses currently-visible runs).
 */
function renderHeroStats(runs) {
    const heroStats = document.getElementById('hero-stats');
    if (!heroStats) return;

    const totalRuns = runs.length;
    const strategies = new Set(runs.map(r => r.strategy_name)).size;
    const avgReturn = runs.length > 0
        ? runs.reduce((sum, r) => sum + (r.metrics?.total_return || 0), 0) / runs.length
        : 0;

    heroStats.innerHTML = `
        <div class="hero-stat">
            <span class="value">${totalRuns}</span>
            <span class="label">回测记录</span>
        </div>
        <div class="hero-stat">
            <span class="value">${strategies}</span>
            <span class="label">策略数量</span>
        </div>
        <div class="hero-stat">
            <span class="value" data-trend="${avgReturn >= 0 ? 'up' : 'down'}">${formatValue(avgReturn, 'percent')}</span>
            <span class="label">平均收益率</span>
        </div>
    `;
}

/**
 * 判断 run 的关键指标是否缺失（数据不完整）
 */
function isRunIncomplete(run) {
    const metrics = run?.metrics;
    if (!metrics) return true;
    const tr = metrics.total_return;
    return tr === null || tr === undefined;
}

/**
 * Render a single run card
 */
function renderRunCard(run) {
    const { metrics } = run;
    const totalReturn = getMetricDisplay(metrics, 'total_return');
    const maxDrawdown = getMetricDisplay(metrics, 'max_drawdown');
    const sharpe = getMetricDisplay(metrics, 'sharpe_ratio');
    const totalTrades = metrics?.total_trades || run.trades?.length || 0;
    const incomplete = isRunIncomplete(run);
    const incompleteCls = incomplete ? ' is-incomplete' : '';
    const incompleteBadge = incomplete
        ? '<span class="card-badge card-badge-warn" title="关键指标缺失，数据可能不完整">数据不完整</span>'
        : '';
    const versionLabel = _versionIndex.get(run.run_id) || 'v0';

    const safeRunId = escapeHtml(run.run_id);
    const safeStrategy = escapeHtml(run.strategy_name);
    const safeSymbol = escapeHtml(run.symbol || '—');
    const safeFreq = escapeHtml(run.freq || '1d');
    const safeVersionAttr = escapeHtml(versionLabel);

    return `
        <article class="run-card${incompleteCls}"
                 tabindex="0"
                 role="button"
                 data-run-id="${safeRunId}"
                 onclick="window.navigateToRun('${safeRunId}')"
                 onkeydown="if(event.key==='Enter'||event.key===' ') window.navigateToRun('${safeRunId}')"
                 aria-label="查看 ${safeStrategy} ${safeVersionAttr} 回测详情">
            <header class="card-header">
                <div class="card-version" aria-label="版本号 ${safeVersionAttr}">
                    <span class="card-version__tag">${safeVersionAttr}</span>
                    <span class="card-version__time">${formatRelativeTime(run.created_at)}</span>
                </div>
                <div class="card-badges">
                    <span class="card-badge">${safeSymbol}</span>
                    ${incompleteBadge}
                </div>
            </header>

            <div class="card-meta">
                <span class="meta-item">
                    <span class="meta-icon">⏱️</span>
                    ${safeFreq}
                </span>
                <span class="meta-item meta-item--mono" title="${safeRunId}">
                    <span class="meta-icon">🔖</span>
                    ${safeRunId}
                </span>
            </div>

            <div class="card-sparkline" data-run-id="${safeRunId}"></div>

            <div class="card-metrics">
                <div class="card-metric">
                    <span class="metric-label">总收益率</span>
                    <span class="metric-value" data-trend="${totalReturn.class === 'positive' ? 'up' : totalReturn.class === 'negative' ? 'down' : ''}">${totalReturn.value}</span>
                </div>
                <div class="card-metric">
                    <span class="metric-label">最大回撤</span>
                    <span class="metric-value" data-trend="${maxDrawdown.class === 'positive' ? 'up' : maxDrawdown.class === 'negative' ? 'down' : ''}">${maxDrawdown.value}</span>
                </div>
                <div class="card-metric">
                    <span class="metric-label">交易次数</span>
                    <span class="metric-value neutral">${totalTrades}</span>
                </div>
                <div class="card-metric">
                    <span class="metric-label">夏普比率</span>
                    <span class="metric-value" data-trend="${sharpe.class === 'positive' ? 'up' : sharpe.class === 'negative' ? 'down' : ''}">${sharpe.value}</span>
                </div>
            </div>

            <footer class="card-footer">
                <span class="card-date">${new Date(run.created_at).toLocaleString('zh-CN')}</span>
                <span class="card-action">
                    查看详情 <span class="card-arrow">→</span>
                </span>
            </footer>
        </article>
    `;
}

/**
 * Render strategy section with grouped cards
 */
function renderStrategySection(strategyName, runs) {
    const icon = getStrategyIcon(strategyName);
    const displayName = getStrategyDisplayName(strategyName);
    const isMapped = displayName && displayName !== strategyName;
    const safeStrategyAttr = encodeURIComponent(strategyName);
    const safeDisplayName = escapeHtml(displayName);
    const safeRawName = escapeHtml(strategyName);
    const canCompare = runs.length >= 2;

    return `
        <section class="strategy-section" data-strategy="${safeStrategyAttr}">
            <header class="strategy-header">
                <div class="strategy-icon">${icon}</div>
                <div class="strategy-title-group">
                    <h2 class="strategy-title">${safeDisplayName}</h2>
                    ${isMapped ? `<span class="strategy-subname" title="${safeRawName}">${safeRawName}</span>` : ''}
                </div>
                <span class="strategy-count">${runs.length} 个版本</span>
                <button class="compare-btn"
                        type="button"
                        ${canCompare ? '' : 'disabled aria-disabled="true"'}
                        aria-expanded="false"
                        aria-controls="compare-panel-${safeStrategyAttr}"
                        title="${canCompare ? '展开版本对比图' : '至少需要 2 个版本才能对比'}"
                        onclick="window.toggleVersionCompare('${safeStrategyAttr}')">
                    <span class="compare-btn__icon" aria-hidden="true">▣</span>
                    <span>对比</span>
                </button>
            </header>
            <div class="compare-panel"
                 id="compare-panel-${safeStrategyAttr}"
                 data-strategy="${safeStrategyAttr}"
                 hidden>
                <div class="compare-panel__chart" data-compare-chart="${safeStrategyAttr}"></div>
            </div>
            <div class="cards-grid">
                ${runs.map(run => renderRunCard(run)).join('')}
            </div>
        </section>
    `;
}

/**
 * Render loading state (skeleton cards)
 */
function renderLoading() {
    const container = document.getElementById('runs-container');
    if (container) {
        const cards = Array.from({ length: 3 }, () => `
            <div class="skeleton-card">
                <div class="skeleton-line skeleton-line--lg"></div>
                <div style="height:var(--spacing-sm)"></div>
                <div class="skeleton-line skeleton-line--md"></div>
                <div style="height:var(--spacing-xs)"></div>
                <div class="skeleton-line skeleton-line--sm"></div>
                <div class="skeleton-metrics">
                    <div class="skeleton-metric">
                        <div class="skeleton-line skeleton-line--sm"></div>
                        <div class="skeleton-line skeleton-line--md"></div>
                    </div>
                    <div class="skeleton-metric">
                        <div class="skeleton-line skeleton-line--sm"></div>
                        <div class="skeleton-line skeleton-line--md"></div>
                    </div>
                </div>
            </div>
        `).join('');
        container.innerHTML = `<div class="skeleton-grid">${cards}</div>`;
    }
}

/**
 * Render error state
 */
function renderError(message) {
    const container = document.getElementById('runs-container');
    if (container) {
        container.innerHTML = `
            <div class="error-state">
                <div class="error-icon">⚠️</div>
                <h2>加载失败</h2>
                <p>${message}</p>
                <button class="retry-btn" onclick="refreshRuns()">重新加载</button>
            </div>
        `;
    }
}

/**
 * Render empty state
 */
function renderEmpty(message = '暂无回测记录', detail = '运行策略后会生成回测记录，请先执行一次回测') {
    const container = document.getElementById('runs-container');
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <h2>${message}</h2>
                <p>${detail}</p>
            </div>
        `;
    }
}

/**
 * Draw a mini sparkline into the given container.
 */
function drawMiniSpark(container, equityData) {
    if (!container || !equityData || equityData.length === 0) return;
    if (typeof echarts === 'undefined') return;

    const initial = equityData[0]?.equity ?? 0;
    const final = equityData[equityData.length - 1]?.equity ?? 0;
    const isUp = final >= initial;
    const lineColor = isUp ? '#10b981' : '#ef4444';
    const areaTop = isUp ? 'rgba(16,185,129,0.30)' : 'rgba(239,68,68,0.30)';
    const areaBottom = isUp ? 'rgba(16,185,129,0)' : 'rgba(239,68,68,0)';

    const chart = echarts.init(container, null, { renderer: 'canvas' });
    chart.setOption({
        animation: false,
        grid: { top: 2, bottom: 2, left: 0, right: 0 },
        xAxis: { show: false, type: 'category', boundaryGap: false,
                 data: equityData.map((_, i) => i) },
        yAxis: { show: false, type: 'value', min: 'dataMin', max: 'dataMax' },
        tooltip: { show: false },
        series: [{
            type: 'line',
            data: equityData.map(e => e.equity),
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 1.4, color: lineColor },
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
    return chart;
}

/**
 * Lazy-load mini sparklines for the first N rendered cards.
 */
async function loadMiniSparklines(runs) {
    // Clean up previously rendered sparklines.
    _sparkCharts.forEach(c => { try { c.dispose(); } catch (e) { /* noop */ } });
    _sparkCharts.clear();

    const slice = runs.slice(0, SPARKLINE_LIMIT);
    await Promise.all(slice.map(async (run) => {
        const container = document.querySelector(`.card-sparkline[data-run-id="${run.run_id}"]`);
        if (!container) return;
        try {
            const resp = await fetch(`/api/runs/${run.run_id}/visualization`);
            if (!resp.ok) return;
            const data = await resp.json();
            const eq = data?.equity_curve;
            if (!eq || eq.length < 2) return;
            // Downsample to ~40 points for snappy rendering.
            const step = Math.max(1, Math.floor(eq.length / 40));
            const sampled = eq.filter((_, i) => i % step === 0);
            const chart = drawMiniSpark(container, sampled);
            if (chart) _sparkCharts.set(run.run_id, chart);
        } catch (e) {
            // silent — sparkline is an enhancement only
        }
    }));
}

/**
 * Render the runs container from a filtered/visible set of runs.
 */
function renderRunsView(runs) {
    const container = document.getElementById('runs-container');
    if (!container) return;

    // Dispose any previously rendered compare charts before swapping DOM.
    _compareCharts.forEach(c => disposeVersionCompare(c));
    _compareCharts.clear();

    renderHeroStats(runs);

    if (runs.length === 0) {
        if (_searchQuery) {
            renderEmpty('未找到匹配结果', `没有策略名称包含 “${_searchQuery}” 的回测记录`);
        } else {
            renderEmpty();
        }
        return;
    }

    const grouped = groupByStrategy(runs);
    container.innerHTML = Object.entries(grouped)
        .map(([strategyName, strategyRuns]) =>
            renderStrategySection(strategyName, strategyRuns))
        .join('');

    // Defer sparkline loading so the DOM paints first.
    requestAnimationFrame(() => loadMiniSparklines(runs));
}

/**
 * Toggle the version-compare panel for a strategy.
 * Exposed as window.toggleVersionCompare for inline onclick handlers.
 */
export function toggleVersionCompare(encodedStrategy) {
    const strategy = decodeURIComponent(encodedStrategy);
    const panel = document.getElementById(`compare-panel-${encodedStrategy}`);
    const btn = document.querySelector(
        `.strategy-section[data-strategy="${encodedStrategy}"] .compare-btn`
    );
    if (!panel) return;

    const runsForStrategy = _strategyRunIndex.get(strategy) || [];
    if (runsForStrategy.length < 2) return;

    const willOpen = panel.hasAttribute('hidden');
    if (willOpen) {
        panel.removeAttribute('hidden');
        // Force reflow so the open animation can play.
        // eslint-disable-next-line no-unused-expressions
        panel.offsetHeight;
        panel.classList.add('is-open');
        if (btn) btn.setAttribute('aria-expanded', 'true');

        const chartEl = panel.querySelector('.compare-panel__chart');
        requestAnimationFrame(() => {
            // Ensure container has a width before init (it does once unhidden).
            const existing = _compareCharts.get(strategy);
            if (existing) disposeVersionCompare(existing);
            const chart = renderVersionCompare(chartEl, runsForStrategy);
            if (chart) _compareCharts.set(strategy, chart);
        });
    } else {
        panel.classList.remove('is-open');
        panel.setAttribute('hidden', '');
        if (btn) btn.setAttribute('aria-expanded', 'false');
        const existing = _compareCharts.get(strategy);
        if (existing) {
            disposeVersionCompare(existing);
            _compareCharts.delete(strategy);
        }
    }
}

/**
 * Apply current search query against the cached runs.
 */
function applyFilter() {
    const q = _searchQuery.trim().toLowerCase();
    if (!q) return _allRuns;
    return _allRuns.filter(r => {
        const name = (r.strategy_name || '').toLowerCase();
        const symbol = (r.symbol || '').toLowerCase();
        return name.includes(q) || symbol.includes(q);
    });
}

/**
 * Wire up the search input.
 */
export function setupSearch() {
    const input = document.getElementById('search-input');
    if (!input || input.dataset.bound) return;
    input.dataset.bound = '1';

    let timer = null;
    input.addEventListener('input', (e) => {
        _searchQuery = e.target.value || '';
        clearTimeout(timer);
        // Debounce slightly for snappier feel without thrashing layout.
        timer = setTimeout(() => {
            renderRunsView(applyFilter());
        }, 120);
    });
}

/**
 * Navigate to run detail page
 */
export function navigateToRun(runId) {
    window.location.href = `/report.html?run_id=${runId}`;
}

/**
 * Load and render runs list
 */
export async function loadRunsList() {
    renderLoading();
    setupSearch();

    try {
        const response = await fetch('/api/runs');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        _allRuns = data.runs || [];

        // Build the version index from the FULL list so that filter operations
        // do not reshuffle version numbering.
        rebuildVersionIndex(_allRuns);

        if (_allRuns.length === 0) {
            renderHeroStats([]);
            renderEmpty();
            return;
        }

        renderRunsView(applyFilter());
    } catch (error) {
        console.error('[Runs List] Error:', error);
        renderError(error.message);
    }
}

/**
 * Refresh runs list
 */
export function refreshRuns() {
    loadRunsList();
}

// Make navigateToRun available globally
window.navigateToRun = navigateToRun;
window.loadRunsList = loadRunsList;
window.refreshRuns = refreshRuns;
window.toggleVersionCompare = toggleVersionCompare;

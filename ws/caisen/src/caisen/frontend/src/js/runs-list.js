/**
 * Caisen Visualization - Runs List Page
 * 回测列表页面逻辑
 */

import { formatValue, formatTimestamp } from './components.js';
import { appState } from './app-state.js';

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
 * Get strategy icon based on name
 */
function getStrategyIcon(strategyName) {
    const icons = {
        '蔡森策略': '📈',
        'CaiSen': '📈',
        'MACD': '📉',
        'MA': '📊',
        'default': '🎯'
    };
    for (const [key, icon] of Object.entries(icons)) {
        if (strategyName.includes(key)) return icon;
    }
    return icons.default;
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
 * Render hero stats
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
            <span class="value" style="color: ${avgReturn >= 0 ? 'var(--color-up)' : 'var(--color-down)'}">${formatValue(avgReturn, 'percent')}</span>
            <span class="label">平均收益率</span>
        </div>
    `;
}

/**
 * Render a single run card
 */
function renderRunCard(run) {
    const { metrics } = run;
    const totalReturn = getMetricDisplay(metrics, 'total_return');
    const maxDrawdown = getMetricDisplay(metrics, 'max_drawdown');
    const totalTrades = metrics?.total_trades || run.trades?.length || 0;

    return `
        <article class="run-card" 
                 tabindex="0" 
                 role="button"
                 onclick="window.navigateToRun('${run.run_id}')"
                 onkeydown="if(event.key==='Enter'||event.key===' ') window.navigateToRun('${run.run_id}')"
                 aria-label="查看 ${run.strategy_name} 回测详情">
            <header class="card-header">
                <h3 class="card-title">${run.strategy_name}</h3>
                <span class="card-badge">${run.symbol || '—'}</span>
            </header>
            
            <div class="card-meta">
                <span class="meta-item">
                    <span class="meta-icon">📅</span>
                    ${formatRelativeTime(run.created_at)}
                </span>
                <span class="meta-item">
                    <span class="meta-icon">⏱️</span>
                    ${run.freq || '1d'}
                </span>
            </div>
            
            <div class="card-metrics">
                <div class="card-metric">
                    <span class="metric-label">总收益率</span>
                    <span class="metric-value ${totalReturn.class}">${totalReturn.value}</span>
                </div>
                <div class="card-metric">
                    <span class="metric-label">最大回撤</span>
                    <span class="metric-value ${maxDrawdown.class}">${maxDrawdown.value}</span>
                </div>
                <div class="card-metric">
                    <span class="metric-label">交易次数</span>
                    <span class="metric-value neutral">${totalTrades}</span>
                </div>
                <div class="card-metric">
                    <span class="metric-label">夏普比率</span>
                    <span class="metric-value ${getMetricDisplay(metrics, 'sharpe_ratio').class}">${getMetricDisplay(metrics, 'sharpe_ratio').value}</span>
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
    return `
        <section class="strategy-section">
            <header class="strategy-header">
                <div class="strategy-icon">${icon}</div>
                <h2 class="strategy-title">${strategyName}</h2>
                <span class="strategy-count">${runs.length} 个回测</span>
            </header>
            <div class="cards-grid">
                ${runs.map(run => renderRunCard(run)).join('')}
            </div>
        </section>
    `;
}

/**
 * Render loading state
 */
function renderLoading() {
    const container = document.getElementById('runs-container');
    if (container) {
        container.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>加载回测记录...</p>
            </div>
        `;
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
function renderEmpty() {
    const container = document.getElementById('runs-container');
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <h2>暂无回测记录</h2>
                <p>运行策略后会生成回测记录，请先执行一次回测</p>
            </div>
        `;
    }
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
    
    try {
        const response = await fetch('/api/runs');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        const runs = data.runs || [];
        
        if (runs.length === 0) {
            renderEmpty();
            return;
        }
        
        // Render hero stats
        renderHeroStats(runs);
        
        // Group by strategy
        const grouped = groupByStrategy(runs);
        
        // Render sections
        const container = document.getElementById('runs-container');
        container.innerHTML = Object.entries(grouped)
            .map(([strategyName, strategyRuns]) => 
                renderStrategySection(strategyName, strategyRuns))
            .join('');
            
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
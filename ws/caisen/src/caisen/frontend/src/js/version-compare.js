/**
 * Caisen Visualization - Version Compare Chart
 * 同一策略下多个版本的关键指标对比图（ECharts）
 *
 * 设计原则：
 *  - 使用全局 window.echarts（与页面 CDN 一致，避免重复打包）
 *  - 暗色玻璃配色，与首页一致
 *  - 双轴：百分比指标共用左轴，比率（夏普）走右轴
 *  - 自带 resize 监听器，调用方需在销毁时使用 disposeChart()
 */

const PALETTE = {
    totalReturn: '#10b981',
    maxDrawdown: '#ef4444',
    sharpe: '#60a5fa',
    winRate: '#f6ad55',
    axis: '#94a3b8',
    legend: '#cbd5e1',
    grid: 'rgba(148, 163, 184, 0.08)',
    tooltipBg: 'rgba(15, 23, 42, 0.92)',
    tooltipBorder: 'rgba(255, 255, 255, 0.08)',
};

/**
 * 根据 created_at（或 run_id）升序排序，最早的为 v0。
 */
function sortRunsChronologically(runs) {
    return [...runs].sort((a, b) => {
        const ka = a?.created_at || a?.run_id || '';
        const kb = b?.created_at || b?.run_id || '';
        return ka.localeCompare(kb);
    });
}

function pct(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return 0;
    return Number((num * 100).toFixed(2));
}

function ratio(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return 0;
    return Number(num.toFixed(2));
}

/**
 * 构造 ECharts option。
 * 拆分函数便于单元测试（无需真实 DOM/ECharts 实例）。
 */
export function buildVersionCompareOption(runs) {
    const sorted = sortRunsChronologically(runs);
    const versions = sorted.map((_, i) => `v${i}`);

    const totalReturn = sorted.map(r => pct(r?.metrics?.total_return));
    const maxDrawdown = sorted.map(r => pct(r?.metrics?.max_drawdown));
    const sharpe = sorted.map(r => ratio(r?.metrics?.sharpe_ratio));
    const winRate = sorted.map(r => pct(r?.metrics?.win_rate));

    return {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: PALETTE.tooltipBg,
            borderColor: PALETTE.tooltipBorder,
            borderWidth: 1,
            textStyle: { color: '#f8fafc', fontSize: 12 },
            axisPointer: {
                type: 'shadow',
                shadowStyle: { color: 'rgba(96, 165, 250, 0.06)' },
            },
        },
        legend: {
            data: ['总收益率', '最大回撤', '夏普比率', '胜率'],
            textStyle: { color: PALETTE.legend, fontSize: 12 },
            itemWidth: 14,
            itemHeight: 8,
            top: 4,
        },
        grid: { top: 56, bottom: 28, left: 56, right: 52, containLabel: true },
        xAxis: {
            type: 'category',
            data: versions,
            axisLine: { lineStyle: { color: PALETTE.grid } },
            axisTick: { show: false },
            axisLabel: {
                color: PALETTE.axis,
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                fontSize: 11,
                letterSpacing: 1,
            },
        },
        yAxis: [
            {
                type: 'value',
                name: '百分比 (%)',
                nameTextStyle: { color: PALETTE.axis, fontSize: 11 },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { lineStyle: { color: PALETTE.grid } },
                axisLabel: { color: PALETTE.axis, fontSize: 11 },
            },
            {
                type: 'value',
                name: '比率',
                nameTextStyle: { color: PALETTE.axis, fontSize: 11 },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { show: false },
                axisLabel: { color: PALETTE.axis, fontSize: 11 },
            },
        ],
        series: [
            {
                name: '总收益率',
                type: 'bar',
                data: totalReturn,
                barMaxWidth: 22,
                itemStyle: { color: PALETTE.totalReturn, borderRadius: [4, 4, 0, 0] },
            },
            {
                name: '最大回撤',
                type: 'bar',
                data: maxDrawdown,
                barMaxWidth: 22,
                itemStyle: { color: PALETTE.maxDrawdown, borderRadius: [4, 4, 0, 0] },
            },
            {
                name: '胜率',
                type: 'bar',
                data: winRate,
                barMaxWidth: 22,
                itemStyle: { color: PALETTE.winRate, borderRadius: [4, 4, 0, 0] },
            },
            {
                name: '夏普比率',
                type: 'line',
                yAxisIndex: 1,
                data: sharpe,
                smooth: true,
                symbol: 'circle',
                symbolSize: 7,
                lineStyle: { width: 2, color: PALETTE.sharpe },
                itemStyle: { color: PALETTE.sharpe, borderColor: '#0f172a', borderWidth: 1 },
            },
        ],
    };
}

/**
 * 在容器中渲染对比图，返回 echarts 实例与 dispose 句柄。
 */
export function renderVersionCompare(container, runs) {
    if (!container) return null;
    const echarts = (typeof window !== 'undefined') ? window.echarts : undefined;
    if (!echarts) {
        console.warn('[version-compare] ECharts not available');
        return null;
    }

    // 若容器已绑定实例则复用，避免重复 init。
    let chart = echarts.getInstanceByDom(container);
    if (!chart) {
        chart = echarts.init(container, null, { renderer: 'canvas' });
    }
    chart.setOption(buildVersionCompareOption(runs), true);

    const onResize = () => {
        try { chart.resize(); } catch (e) { /* noop */ }
    };
    window.addEventListener('resize', onResize);

    // 把卸载方法挂到实例上，便于 runs-list 一并清理。
    chart.__disposeCompare = () => {
        window.removeEventListener('resize', onResize);
        try { chart.dispose(); } catch (e) { /* noop */ }
    };
    return chart;
}

/**
 * 安全销毁通过 renderVersionCompare 创建的图表。
 */
export function disposeVersionCompare(chart) {
    if (!chart) return;
    if (typeof chart.__disposeCompare === 'function') {
        chart.__disposeCompare();
        return;
    }
    try { chart.dispose(); } catch (e) { /* noop */ }
}

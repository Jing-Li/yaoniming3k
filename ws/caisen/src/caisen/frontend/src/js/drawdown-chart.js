/**
 * Caisen Visualization - Drawdown Chart
 * 独立回撤区域图
 */

import { appState } from './app-state.js';
import { setupChartSync } from './chart-renderer.js';

/**
 * 计算回撤详情（包含恢复信息及最大回撤持续天数）
 */
export function calculateDrawdownDetails(equityCurve) {
    if (!equityCurve || equityCurve.length === 0) return null;

    const equityData = equityCurve.map(item => item.equity);

    // 回撤序列
    let peak = 0;
    const peaks = [];
    const drawdowns = [];

    equityData.forEach(v => {
        if (v > peak) peak = v;
        peaks.push(peak);
        drawdowns.push(peak > 0 ? (v - peak) / peak : 0);
    });

    // 最大回撤底部
    let maxDD = 0;
    let maxDDEndIdx = 0;
    drawdowns.forEach((dd, i) => {
        if (dd < maxDD) {
            maxDD = dd;
            maxDDEndIdx = i;
        }
    });

    // 最大回撤起点（最远的、达到当时峰值的索引）
    let maxDDStartIdx = 0;
    for (let i = maxDDEndIdx - 1; i >= 0; i--) {
        if (equityData[i] >= peaks[maxDDEndIdx]) {
            maxDDStartIdx = i;
            break;
        }
    }

    // 恢复点
    let recoveryIdx = null;
    const recoveryLevel = peaks[maxDDEndIdx];
    for (let i = maxDDEndIdx + 1; i < equityData.length; i++) {
        if (equityData[i] >= recoveryLevel) {
            recoveryIdx = i;
            break;
        }
    }

    // 持续时间（基于真实时间戳；fallback 到索引差作为天数近似）
    const durationDays = computeDurationDays(equityCurve, maxDDStartIdx, maxDDEndIdx);
    const recoveryDays = recoveryIdx != null
        ? computeDurationDays(equityCurve, maxDDEndIdx, recoveryIdx)
        : null;

    return {
        drawdowns,
        maxDD,
        maxDDStartIdx,
        maxDDEndIdx,
        recoveryIdx,
        durationDays,
        recoveryDays
    };
}

function computeDurationDays(equityCurve, fromIdx, toIdx) {
    if (fromIdx == null || toIdx == null || toIdx <= fromIdx) return 0;
    const a = equityCurve[fromIdx]?.timestamp;
    const b = equityCurve[toIdx]?.timestamp;
    if (a && b) {
        const diffMs = new Date(b) - new Date(a);
        if (isFinite(diffMs) && diffMs > 0) {
            return Math.max(1, Math.round(diffMs / (24 * 3600 * 1000)));
        }
    }
    // fallback: assume one bar per day
    return toIdx - fromIdx;
}

/**
 * 构建 ECharts 回撤图配置
 */
export function buildDrawdownOption(equityCurve, details) {
    if (!equityCurve || equityCurve.length === 0 || !details) return null;

    const dates = equityCurve.map(item =>
        new Date(item.timestamp).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit' })
    );

    // 最大回撤区间高亮（红色半透明 + 标注 “最大回撤 XX%”）
    const markAreaData = [];
    if (details.maxDDStartIdx !== details.maxDDEndIdx && details.maxDD < 0) {
        markAreaData.push([
            {
                xAxis: details.maxDDStartIdx,
                itemStyle: { color: 'rgba(252, 129, 129, 0.18)' },
                label: {
                    show: true,
                    formatter: `最大回撤 ${(details.maxDD * 100).toFixed(2)}%`,
                    position: 'insideTop',
                    color: '#fc8181',
                    fontSize: 11,
                    fontWeight: 600
                }
            },
            { xAxis: details.recoveryIdx != null ? details.recoveryIdx : equityCurve.length - 1 }
        ]);
    }

    // markPoints: 底部 + 恢复点（绿色三角箭头）
    const markPointData = [];
    if (details.maxDDEndIdx > 0) {
        markPointData.push({
            name: 'bottom',
            xAxis: details.maxDDEndIdx,
            yAxis: details.maxDD,
            symbol: 'circle',
            symbolSize: 8,
            itemStyle: { color: '#fc8181', borderColor: '#fff', borderWidth: 1 },
            label: { show: false }
        });
    }
    if (details.recoveryIdx != null) {
        markPointData.push({
            name: 'recovery',
            xAxis: details.recoveryIdx,
            yAxis: 0,
            symbol: 'triangle',
            symbolSize: 12,
            itemStyle: { color: '#48bb78', borderColor: '#fff', borderWidth: 1 },
            label: {
                show: true,
                formatter: '恢复',
                position: 'top',
                color: '#48bb78',
                fontSize: 10,
                fontWeight: 600
            }
        });
    }

    return {
        backgroundColor: 'transparent',
        animation: false,
        tooltip: {
            trigger: 'axis',
            backgroundColor: '#1a1f36',
            borderColor: '#4a5568',
            borderWidth: 1,
            padding: [10, 12],
            textStyle: { color: '#e2e8f0', fontSize: 12 },
            extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.4); border-radius: 6px;',
            formatter: function(params) {
                const dd = params && params[0];
                if (!dd) return '';
                const idx = dd.dataIndex;
                const pct = (dd.data * 100).toFixed(2);
                const isInDD = dd.data < -0.0001;

                // 计算从最近峰值起的持续天数
                let durStr = '';
                if (isInDD) {
                    let peakIdx = idx;
                    for (let i = idx; i >= 0; i--) {
                        if ((details.drawdowns[i] || 0) >= -1e-9) { peakIdx = i; break; }
                    }
                    const days = computeDurationDays(equityCurve, peakIdx, idx);
                    if (days > 0) durStr = `<br/>持续: <span style="color:#a0aec0">${days} 天</span>`;
                }
                return `<div style="font-weight:600;margin-bottom:4px">${dd.axisValue}</div>` +
                    `回撤: <span style="color:#fc8181;font-weight:600">${pct}%</span>${durStr}`;
            }
        },
        grid: { left: '10%', right: '8%', top: '15%', bottom: '10%' },
        xAxis: {
            type: 'category',
            data: dates,
            axisLine: { lineStyle: { color: '#4a5568' } },
            axisLabel: { color: '#718096', show: false },
            splitLine: { show: false }
        },
        yAxis: {
            type: 'value',
            axisLine: { lineStyle: { color: '#4a5568' } },
            axisLabel: {
                color: '#718096',
                formatter: v => (v * 100).toFixed(1) + '%'
            },
            splitLine: { lineStyle: { color: '#2d3748', type: 'dashed' } }
        },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 }
        ],
        series: [{
            name: '回撤',
            type: 'line',
            data: details.drawdowns,
            smooth: true,
            lineStyle: { width: 1.5, color: '#fc8181' },
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: 'rgba(252, 129, 129, 0.05)' },
                        { offset: 1, color: 'rgba(252, 129, 129, 0.4)' }
                    ]
                }
            },
            symbol: 'none',
            markArea: {
                silent: true,
                data: markAreaData
            },
            markPoint: {
                data: markPointData
            }
        }]
    };
}

/**
 * 渲染独立回撤图
 */
export function renderDrawdownChart() {
    const data = appState.getFilteredData();
    if (!data || !data.equity_curve || data.equity_curve.length === 0) return;

    const container = document.getElementById('drawdown-chart');
    if (!container) return;

    const details = calculateDrawdownDetails(data.equity_curve);
    const option = buildDrawdownOption(data.equity_curve, details);
    if (!option) return;

    let chart = appState.getDrawdownChart();
    if (!chart) {
        chart = echarts.init(container);
        appState.setDrawdownChart(chart);
    }

    chart.setOption(option, true);

    // Re-run sync so the lazily-initialized drawdown chart joins the linked group.
    setupChartSync();
}

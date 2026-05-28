/**
 * Caisen Visualization - Monthly Returns Heatmap
 * 月度收益热力图（含年度均值列与月度均值行）
 */

import { appState } from './app-state.js';

const MONTH_LABELS = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
const ANNUAL_LABEL = '年均';
const MONTHLY_LABEL = '月均';

/**
 * 计算月度收益率
 */
export function calculateMonthlyReturns(equityCurve) {
    if (!equityCurve || equityCurve.length === 0) return [];

    const monthlyData = {};

    equityCurve.forEach(item => {
        const date = new Date(item.timestamp);
        const year = date.getFullYear();
        const month = date.getMonth() + 1; // 1-12
        const key = `${year}-${month}`;

        if (!monthlyData[key] || new Date(item.timestamp) > new Date(monthlyData[key].timestamp)) {
            monthlyData[key] = {
                year,
                month,
                equity: item.equity,
                timestamp: item.timestamp
            };
        }
    });

    const sortedKeys = Object.keys(monthlyData).sort((a, b) => {
        const [ya, ma] = a.split('-').map(Number);
        const [yb, mb] = b.split('-').map(Number);
        return ya !== yb ? ya - yb : ma - mb;
    });
    const results = [];

    let prevEquity = null;
    sortedKeys.forEach(key => {
        const entry = monthlyData[key];
        if (prevEquity !== null && prevEquity > 0) {
            const ret = (entry.equity - prevEquity) / prevEquity;
            results.push({ year: entry.year, month: entry.month, value: ret });
        }
        prevEquity = entry.equity;
    });

    return results;
}

/**
 * 在原始月度收益基础上，附加年度汇总列与月度汇总行。
 * 返回值结构：{ years, xLabels, yLabels, data }
 *  - xLabels = ['2023','2024',..., '年均']
 *  - yLabels = ['1月','2月',...,'12月','月均']
 *  - data 是 [xIdx, yIdx, value] 三元组数组（兼容 ECharts heatmap）
 */
export function buildHeatmapMatrix(monthlyReturns) {
    const years = [...new Set(monthlyReturns.map(d => d.year))].sort((a, b) => a - b);
    const xLabels = [...years.map(String), ANNUAL_LABEL];
    const yLabels = [...MONTH_LABELS, MONTHLY_LABEL];

    const data = [];

    // 主体：每年每月
    monthlyReturns.forEach(d => {
        const xIdx = years.indexOf(d.year);
        const yIdx = d.month - 1;
        if (xIdx >= 0) {
            data.push([xIdx, yIdx, d.value]);
        }
    });

    // 年度均值列（最后一列）：同一年所有月份均值
    years.forEach((year, xIdx) => {
        const sameYear = monthlyReturns.filter(d => d.year === year);
        if (sameYear.length > 0) {
            const avg = sameYear.reduce((s, d) => s + d.value, 0) / sameYear.length;
            // 年均值放在最后一行 (yLabels.length - 1)
            data.push([xIdx, yLabels.length - 1, avg]);
        }
    });

    // 月度均值行（最后一列 ‘年均’）
    for (let m = 0; m < 12; m++) {
        const sameMonth = monthlyReturns.filter(d => d.month === m + 1);
        if (sameMonth.length > 0) {
            const avg = sameMonth.reduce((s, d) => s + d.value, 0) / sameMonth.length;
            data.push([xLabels.length - 1, m, avg]);
        }
    }

    // 总平均值（右下角，年均列 × 月均行）
    if (monthlyReturns.length > 0) {
        const overall = monthlyReturns.reduce((s, d) => s + d.value, 0) / monthlyReturns.length;
        data.push([xLabels.length - 1, yLabels.length - 1, overall]);
    }

    return { years, xLabels, yLabels, data };
}

/**
 * 构建 ECharts heatmap 配置
 */
export function buildHeatmapOption(monthlyReturns) {
    if (!monthlyReturns || monthlyReturns.length === 0) return null;

    const { years, xLabels, yLabels, data } = buildHeatmapMatrix(monthlyReturns);
    if (data.length === 0) return null;

    // 用于 visualMap 范围
    const values = data.map(d => d[2]).filter(v => typeof v === 'number' && isFinite(v));
    const maxAbs = Math.max(0.05, ...values.map(v => Math.abs(v)));

    return {
        backgroundColor: 'transparent',
        animation: false,
        tooltip: {
            position: 'top',
            backgroundColor: '#1a1f36',
            borderColor: '#4a5568',
            borderWidth: 1,
            padding: [8, 10],
            textStyle: { color: '#e2e8f0', fontSize: 12 },
            extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.4); border-radius: 6px;',
            formatter: function(params) {
                if (!params || !params.data) return '';
                const [xIdx, yIdx, value] = params.data;
                if (typeof value !== 'number' || !isFinite(value)) return '';
                const pct = (value * 100).toFixed(2);
                const sign = value >= 0 ? '+' : '';
                const color = value >= 0 ? '#48bb78' : '#fc8181';

                const xLabel = xLabels[xIdx];
                const yLabel = yLabels[yIdx];
                const isAggX = xLabel === ANNUAL_LABEL;
                const isAggY = yLabel === MONTHLY_LABEL;

                let header;
                if (isAggX && isAggY) {
                    header = '总体平均';
                } else if (isAggX) {
                    header = `${yLabel} · 跨年平均`;
                } else if (isAggY) {
                    header = `${xLabel}年 · 全年平均`;
                } else {
                    // 月份名形如 "1月"，直接拼出 “YYYY年M月”
                    const monthNum = yIdx + 1;
                    header = `${xLabel}年${monthNum}月`;
                }
                return `<div style="font-weight:600;margin-bottom:3px">${header}</div>` +
                    `<span style="color:${color};font-weight:600">${sign}${pct}%</span>`;
            }
        },
        grid: { left: '12%', right: '12%', top: '8%', bottom: '22%' },
        xAxis: {
            type: 'category',
            data: xLabels,
            axisLine: { lineStyle: { color: '#4a5568' } },
            axisLabel: {
                color: function(value) {
                    return value === ANNUAL_LABEL ? '#f6ad55' : '#a0aec0';
                }
            },
            splitLine: { show: false },
            splitArea: { show: false }
        },
        yAxis: {
            type: 'category',
            data: yLabels,
            axisLine: { lineStyle: { color: '#4a5568' } },
            axisLabel: {
                color: function(value) {
                    return value === MONTHLY_LABEL ? '#f6ad55' : '#a0aec0';
                }
            },
            splitLine: { show: false },
            splitArea: { show: false }
        },
        visualMap: {
            min: -maxAbs,
            max: maxAbs,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: '2%',
            textStyle: { color: '#a0aec0' },
            inRange: {
                // 三段式渐变：深红 → 白 → 深绿
                color: ['#7a1f1f', '#fc8181', '#ffffff', '#48bb78', '#1f6b3a']
            },
            formatter: function(value) {
                return (value * 100).toFixed(1) + '%';
            }
        },
        series: [{
            type: 'heatmap',
            data: data,
            label: {
                show: true,
                color: '#1a2234',
                fontSize: 10,
                fontWeight: 600,
                formatter: function(params) {
                    const v = params.data[2];
                    if (typeof v !== 'number' || !isFinite(v)) return '';
                    return (v * 100).toFixed(1);
                }
            },
            itemStyle: {
                borderColor: '#1a2234',
                borderWidth: 2
            },
            emphasis: {
                itemStyle: {
                    borderColor: '#fff',
                    borderWidth: 1.5,
                    shadowBlur: 10,
                    shadowColor: 'rgba(255,255,255,0.3)'
                }
            }
        }]
    };
}

/**
 * 渲染月度收益热力图
 */
export function renderHeatmapChart() {
    const data = appState.getFilteredData();
    if (!data || !data.equity_curve || data.equity_curve.length === 0) return;

    const container = document.getElementById('heatmap-chart');
    if (!container) return;

    const monthlyReturns = calculateMonthlyReturns(data.equity_curve);
    const option = buildHeatmapOption(monthlyReturns);
    if (!option) return;

    let chart = appState.getHeatmapChart();
    if (!chart) {
        chart = echarts.init(container);
        appState.setHeatmapChart(chart);
    }

    chart.setOption(option, true);
}

/**
 * Caisen Visualization - Trade Distribution Chart
 * 交易盈亏分布直方图（含正态拟合曲线、均值/中位数标线）
 */

import { appState } from './app-state.js';

/**
 * 配对买卖交易，计算收益率列表
 */
export function calculateTradeReturns(trades) {
    if (!trades || trades.length === 0) return [];

    const returns = [];
    let buyTrade = null;

    const sorted = [...trades].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    sorted.forEach(trade => {
        if (trade.side === 'BUY') {
            if (buyTrade === null) {
                buyTrade = trade;
            }
        } else if (trade.side === 'SELL' && buyTrade) {
            const profit = (trade.price - buyTrade.price) * buyTrade.quantity;
            const cost = buyTrade.price * buyTrade.quantity;
            const ret = cost > 0 ? profit / cost : 0;
            returns.push(ret);
            buyTrade = null;
        }
    });

    return returns;
}

/**
 * 分桶统计
 */
export function buildHistogramBuckets(returns, bucketCount = 20) {
    if (!returns || returns.length === 0) return [];

    const maxAbs = Math.max(
        Math.abs(Math.min(...returns)),
        Math.abs(Math.max(...returns)),
        0.05
    );
    const range = maxAbs * 1.2;
    const bucketWidth = (2 * range) / bucketCount;

    const buckets = [];
    for (let i = 0; i < bucketCount; i++) {
        const lower = -range + i * bucketWidth;
        const upper = lower + bucketWidth;
        const mid = (lower + upper) / 2;
        buckets.push({
            lower,
            upper,
            mid,
            count: 0,
            isProfit: mid >= 0
        });
    }

    returns.forEach(ret => {
        const idx = Math.floor((ret + range) / bucketWidth);
        const clampedIdx = Math.max(0, Math.min(bucketCount - 1, idx));
        buckets[clampedIdx].count++;
    });

    return buckets;
}

/**
 * 计算样本均值和中位数
 */
export function calcStats(returns) {
    if (!returns || returns.length === 0) return { mean: 0, median: 0, std: 0 };
    const n = returns.length;
    const mean = returns.reduce((s, v) => s + v, 0) / n;
    const variance = returns.reduce((s, v) => s + (v - mean) ** 2, 0) / Math.max(1, n - 1);
    const std = Math.sqrt(variance);

    const sorted = [...returns].sort((a, b) => a - b);
    const mid = Math.floor(n / 2);
    const median = n % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];

    return { mean, median, std };
}

/**
 * 在每个桶中点处计算正态分布的"期望计数"，便于直接叠加在直方图上：
 *   expected_count = N * bucketWidth * pdf(x)
 */
export function buildNormalCurve(buckets, stats, totalCount) {
    if (!buckets || buckets.length < 2 || !stats || stats.std <= 0) return [];
    const bucketWidth = buckets[1].mid - buckets[0].mid;
    const factor = totalCount * bucketWidth / (stats.std * Math.sqrt(2 * Math.PI));
    return buckets.map(b => {
        const z = (b.mid - stats.mean) / stats.std;
        return +(factor * Math.exp(-0.5 * z * z)).toFixed(3);
    });
}

/**
 * 构建 ECharts 配置
 */
export function buildTradeDistributionOption(buckets, returns) {
    if (!buckets || buckets.length === 0) return null;

    const labels = buckets.map(b => {
        const lo = (b.lower * 100).toFixed(1);
        const hi = (b.upper * 100).toFixed(1);
        return `${lo}%~${hi}%`;
    });
    const counts = buckets.map(b => b.count);
    const totalCount = (returns && returns.length) || counts.reduce((s, c) => s + c, 0);
    const stats = calcStats(returns || []);
    const normalCurve = buildNormalCurve(buckets, stats, totalCount);

    // 找到 mean / median 在哪个 bucket（按桶中点最接近）
    const findBucketIdx = (val) => {
        if (!isFinite(val)) return -1;
        let best = 0;
        let bestD = Infinity;
        buckets.forEach((b, i) => {
            const d = Math.abs(b.mid - val);
            if (d < bestD) { bestD = d; best = i; }
        });
        return best;
    };
    const meanIdx = findBucketIdx(stats.mean);
    const medianIdx = findBucketIdx(stats.median);

    const markLineData = [];
    if (totalCount > 0 && meanIdx >= 0) {
        markLineData.push({
            xAxis: meanIdx,
            lineStyle: { color: '#60a5fa', type: 'solid', width: 1.5 },
            label: {
                show: true,
                formatter: `均值 ${(stats.mean * 100).toFixed(2)}%`,
                position: 'insideEndTop',
                color: '#60a5fa',
                fontSize: 10
            }
        });
    }
    if (totalCount > 0 && medianIdx >= 0) {
        markLineData.push({
            xAxis: medianIdx,
            lineStyle: { color: '#f6ad55', type: 'dashed', width: 1.5 },
            label: {
                show: true,
                formatter: `中位 ${(stats.median * 100).toFixed(2)}%`,
                position: 'insideEndBottom',
                color: '#f6ad55',
                fontSize: 10
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
                if (!params || params.length === 0) return '';
                const idx = params[0].dataIndex;
                const bucket = buckets[idx];
                if (!bucket) return '';
                const lo = (bucket.lower * 100).toFixed(1);
                const hi = (bucket.upper * 100).toFixed(1);
                const color = bucket.isProfit ? '#48bb78' : '#fc8181';
                let body = `<div style="font-weight:600;margin-bottom:4px">区间 <span style="color:${color}">${lo}% ~ ${hi}%</span></div>` +
                    `<div>交易数: <span style="font-weight:600">${bucket.count}</span></div>`;
                const normalParam = params.find(p => p.seriesName === '正态拟合');
                if (normalParam && typeof normalParam.data === 'number') {
                    body += `<div style="color:#a0aec0;font-size:11px;margin-top:2px">正态拟合: ${normalParam.data.toFixed(2)}</div>`;
                }
                return body;
            }
        },
        legend: {
            data: ['交易频次', '正态拟合'],
            textStyle: { color: '#a0aec0' },
            top: 0,
            itemWidth: 14,
            itemHeight: 8
        },
        grid: { left: '10%', right: '8%', top: '15%', bottom: '25%' },
        xAxis: {
            type: 'category',
            data: labels,
            axisLine: { lineStyle: { color: '#4a5568' } },
            axisLabel: {
                color: '#718096',
                rotate: 45,
                fontSize: 10
            },
            splitLine: { show: false }
        },
        yAxis: {
            type: 'value',
            axisLine: { lineStyle: { color: '#4a5568' } },
            axisLabel: { color: '#718096' },
            splitLine: { lineStyle: { color: '#2d3748', type: 'dashed' } }
        },
        series: [
            {
                name: '交易频次',
                type: 'bar',
                data: counts.map((c, i) => ({
                    value: c,
                    itemStyle: {
                        color: buckets[i].isProfit ? '#48bb78' : '#fc8181',
                        opacity: 0.85
                    }
                })),
                barMaxWidth: 30,
                label: { show: false },
                markLine: {
                    silent: true,
                    symbol: ['none', 'none'],
                    data: markLineData
                }
            },
            {
                name: '正态拟合',
                type: 'line',
                data: normalCurve,
                smooth: true,
                showSymbol: false,
                symbol: 'none',
                lineStyle: { color: '#9f7aea', width: 2, type: 'solid' },
                z: 5
            }
        ]
    };
}

/**
 * 渲染交易盈亏分布图
 */
export function renderTradeDistribution() {
    const data = appState.getFilteredData();
    if (!data || !data.trades || data.trades.length === 0) return;

    const container = document.getElementById('trade-distribution-chart');
    if (!container) return;

    const returns = calculateTradeReturns(data.trades);
    if (returns.length === 0) return;

    const buckets = buildHistogramBuckets(returns);
    const option = buildTradeDistributionOption(buckets, returns);
    if (!option) return;

    let chart = appState.getTradeDistributionChart();
    if (!chart) {
        chart = echarts.init(container);
        appState.setTradeDistributionChart(chart);
    }

    chart.setOption(option, true);
}

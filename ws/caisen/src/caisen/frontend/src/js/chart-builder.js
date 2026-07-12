/**
 * Caisen Visualization - Chart Builder
 * ECharts 图表构建器
 */

import { CHART_COLORS } from './constants.js';
import { filterValidMarkPoints, filterValidMarkLines, buildBarIndex } from './utils.js';
import { processAnnotations } from './annotation-renderer.js';

// ============================================================
// Indicator helpers (exported for reuse / testing)
// ============================================================

/**
 * Compute simple moving average over `bars[i].close`.
 * @param {Object[]} bars - bar objects with `close`
 * @param {number} period - window size
 * @returns {(number|null)[]} array same length as bars, with leading nulls
 */
export function calculateMA(bars, period) {
    const result = [];
    if (!Array.isArray(bars) || bars.length === 0 || !period || period <= 0) {
        return result;
    }
    for (let i = 0; i < bars.length; i++) {
        if (i < period - 1) {
            result.push(null);
            continue;
        }
        let sum = 0;
        for (let k = i - period + 1; k <= i; k++) {
            sum += Number(bars[k].close) || 0;
        }
        result.push(+(sum / period).toFixed(2));
    }
    return result;
}

/**
 * Find indices where the equity curve makes a new running high.
 * The very first index always counts as a "new high".
 * @param {number[]} equityData
 * @returns {number[]} indices in `equityData`
 */
export function detectNewHighs(equityData) {
    const indices = [];
    if (!Array.isArray(equityData) || equityData.length === 0) return indices;
    let peak = -Infinity;
    for (let i = 0; i < equityData.length; i++) {
        const v = equityData[i];
        if (v > peak) {
            peak = v;
            indices.push(i);
        }
    }
    return indices;
}

/**
 * Detect drawdown periods deeper than `threshold` (positive fraction, e.g. 0.05).
 * A period is defined as `[peakIdx, endIdx]` where `endIdx` is either the recovery
 * point or the bottom (last point) if recovery never happens.
 *
 * @param {number[]} equityData
 * @param {number} [threshold=0.05]
 * @returns {{start:number,end:number,depth:number}[]}
 */
export function detectDrawdownPeriods(equityData, threshold = 0.05) {
    const periods = [];
    if (!Array.isArray(equityData) || equityData.length < 2) return periods;

    let peak = equityData[0];
    let peakIdx = 0;
    let inDrawdown = false;
    let maxDepth = 0;

    for (let i = 1; i < equityData.length; i++) {
        const v = equityData[i];
        if (v > peak) {
            // Recovery (or just a new high without ever having dipped)
            if (inDrawdown && maxDepth >= threshold) {
                periods.push({ start: peakIdx, end: i, depth: maxDepth });
            }
            peak = v;
            peakIdx = i;
            inDrawdown = false;
            maxDepth = 0;
            continue;
        }
        const dd = peak > 0 ? (peak - v) / peak : 0;
        if (dd > 0) {
            inDrawdown = true;
            if (dd > maxDepth) maxDepth = dd;
        }
    }

    // Tail: still in drawdown at end of series
    if (inDrawdown && maxDepth >= threshold) {
        periods.push({ start: peakIdx, end: equityData.length - 1, depth: maxDepth });
    }
    return periods;
}

// ============================================================
// K-Line option
// ============================================================

/**
 * Build K-Line chart option
 * @param {Object} options - Chart options
 * @param {Object} options.data - Filtered data with bars, annotations, trades
 * @param {boolean} options.isZoomEnabled - Whether zoom is enabled
 * @param {boolean} [options.showMA=true] - Whether to overlay MA lines
 * @returns {Object|null} ECharts option object
 */
export function buildKLineOption({ data, isZoomEnabled, showMA = true }) {
    if (!data || !data.bars || data.bars.length === 0) return null;

    // Prepare K-line data
    const dates = data.bars.map(bar => new Date(bar.timestamp).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    }));
    const klineData = data.bars.map(bar => [bar.open, bar.close, bar.low, bar.high]);
    const volumes = data.bars.map((bar, i) => ({
        value: bar.volume,
        itemStyle: {
            color: bar.close >= bar.open ? CHART_COLORS.upColor : CHART_COLORS.downColor,
            opacity: 0.65
        }
    }));

    // MA overlay (computed even when hidden so toggling is cheap, but only added to series if showMA)
    const ma5 = calculateMA(data.bars, 5);
    const ma20 = calculateMA(data.bars, 20);

    // Annotations
    const { markPoints, markLines } = processAnnotations(data.annotations, data.bars);
    const tradeMarkers = processTrades(data.trades, data.bars);
    const allMarkPoints = [...markPoints, ...tradeMarkers];
    let finalMarkPoints = filterValidMarkPoints(allMarkPoints);
    const finalMarkLines = filterValidMarkLines(markLines);

    // ===== Large data mode =====
    const barCount = data.bars.length;
    const isLargeData = barCount > 5000;
    const isVeryLargeData = barCount > 10000;

    // Limit markPoints to top 100 for very large datasets
    if (isVeryLargeData && finalMarkPoints.length > 100) {
        finalMarkPoints = finalMarkPoints.slice(0, 100);
    }

    const option = {
        backgroundColor: CHART_COLORS.background,
                animation: !isVeryLargeData,
        tooltip: buildTooltipOption(data),
        legend: buildKLineLegendConfig(showMA),
        toolbox: buildToolboxConfig(),
        axisPointer: {
            link: [{ xAxisIndex: 'all' }],
            label: { backgroundColor: '#2d3748' }
        },
        grid: buildGridConfig(),
        xAxis: buildXAxisConfig(dates),
        yAxis: buildYAxisConfig(),
        dataZoom: buildDataZoomConfig(isZoomEnabled),
        series: buildSeriesConfig(klineData, volumes, finalMarkPoints, finalMarkLines, ma5, ma20, showMA, isLargeData)
    };

    return option;
}

/**
 * Build tooltip option (card-style, OHLCV + change %).
 * Pre-computes a date→barIndex Map for O(1) annotation lookup on every mouse move.
 */
function buildTooltipOption(data) {
    // Pre-build date string → bar index map (done once per render, not per mouse move)
    const dateToBarIdx = new Map();
    if (data && data.bars) {
        data.bars.forEach((bar, idx) => {
            const dateStr = new Date(bar.timestamp).toLocaleString('zh-CN', {
                month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
            });
            dateToBarIdx.set(dateStr, idx);
        });
    }

    return {
        trigger: 'axis',
        axisPointer: {
            type: 'cross',
            crossStyle: { color: '#a0aec0', width: 1, type: 'dashed' }
        },
        backgroundColor: CHART_COLORS.tooltipBg,
        borderColor: CHART_COLORS.borderColor,
        borderWidth: 1,
        padding: [10, 12],
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.4); border-radius: 6px;',
        formatter: function(params) {
            return buildTooltipContent(params, data, dateToBarIdx);
        }
    };
}

function buildKLineLegendConfig(showMA) {
    if (!showMA) {
        return { show: false };
    }
    return {
        data: [
            { name: 'MA5', icon: 'rect' },
            { name: 'MA20', icon: 'rect' }
        ],
        top: 4,
        right: '10%',
        textStyle: { color: '#a0aec0', fontSize: 11 },
        itemWidth: 14,
        itemHeight: 8
    };
}

function buildToolboxConfig() {
    return {
        right: '2%',
        top: 4,
        itemSize: 14,
        iconStyle: { borderColor: '#a0aec0' },
        emphasis: { iconStyle: { borderColor: '#60a5fa' } },
        feature: {
            restore: { title: '重置缩放' },
            saveAsImage: {
                title: '保存图片',
                pixelRatio: 2,
                backgroundColor: '#0f1525'
            }
        }
    };
}

function buildGridConfig() {
    return [
        { left: '10%', right: '8%', top: '12%', height: '53%' },
        { left: '10%', right: '8%', top: '75%', height: '15%' }
    ];
}

function buildXAxisConfig(dates) {
    return [
        { type: 'category', data: dates, gridIndex: 0, axisLine: { lineStyle: { color: CHART_COLORS.lineColor } }, axisLabel: { color: CHART_COLORS.textColor, show: false }, splitLine: { show: false } },
        { type: 'category', data: dates, gridIndex: 1, axisLine: { lineStyle: { color: CHART_COLORS.lineColor } }, axisLabel: { color: CHART_COLORS.textColor, fontSize: 11 }, splitLine: { show: false } }
    ];
}

function buildYAxisConfig() {
    return [
        { scale: true, gridIndex: 0, axisLine: { lineStyle: { color: CHART_COLORS.lineColor } }, axisLabel: { color: CHART_COLORS.textColor }, splitLine: { lineStyle: { color: '#2d3748', type: 'dashed' } } },
        { scale: true, gridIndex: 1, axisLine: { lineStyle: { color: CHART_COLORS.lineColor } }, axisLabel: { color: CHART_COLORS.textColor }, splitLine: { show: false } }
    ];
}

function buildDataZoomConfig(isZoomEnabled) {
    const baseConfig = { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 };
    if (isZoomEnabled) {
        return [
            baseConfig,
            {
                type: 'slider',
                xAxisIndex: [0, 1],
                start: 0,
                end: 100,
                bottom: 8,
                height: 18,
                borderColor: '#2d3748',
                fillerColor: 'rgba(96, 165, 250, 0.18)',
                handleStyle: { color: '#60a5fa' },
                textStyle: { color: '#718096', fontSize: 10 }
            }
        ];
    }
    return [baseConfig];
}

function buildSeriesConfig(klineData, volumes, markPoints, markLines, ma5, ma20, showMA, isLargeData = false) {
    const series = [
        {
            name: 'K线',
            type: 'candlestick',
            data: klineData,
            xAxisIndex: 0,
            yAxisIndex: 0,
            itemStyle: {
                color: CHART_COLORS.upColor,
                color0: CHART_COLORS.downColor,
                borderColor: CHART_COLORS.upColor,
                borderColor0: CHART_COLORS.downColor
            },
            markPoint: buildMarkPointConfig(markPoints),
            markLine: buildMarkLineConfig(markLines),
            z: 2,
            ...(isLargeData ? { large: true, largeThreshold: 5000 } : {})
        },
        {
            name: '成交量',
            type: 'bar',
            data: volumes,
            xAxisIndex: 1,
            yAxisIndex: 1,
            barWidth: '60%',
            ...(isLargeData ? { large: true, largeThreshold: 5000 } : {})
        }
    ];

    if (showMA) {
        series.push(
            {
                name: 'MA5',
                type: 'line',
                data: ma5,
                xAxisIndex: 0,
                yAxisIndex: 0,
                smooth: true,
                showSymbol: false,
                symbol: 'none',
                lineStyle: { width: 1.2, color: '#f6ad55' },
                z: 3,
                ...(isLargeData ? { sampling: 'lttb' } : {})
            },
            {
                name: 'MA20',
                type: 'line',
                data: ma20,
                xAxisIndex: 0,
                yAxisIndex: 0,
                smooth: true,
                showSymbol: false,
                symbol: 'none',
                lineStyle: { width: 1.2, color: '#9f7aea' },
                z: 3,
                ...(isLargeData ? { sampling: 'lttb' } : {})
            }
        );
    }

    return series;
}

function buildMarkPointConfig(data) {
    return {
        symbol: 'pin',
        symbolSize: 18,
        data: data,
        label: { color: '#fff', fontSize: 9 },
        tooltip: {
            trigger: 'item',
            backgroundColor: CHART_COLORS.tooltipBg,
            borderColor: CHART_COLORS.borderColor,
            textStyle: { color: '#e2e8f0' }
        }
    };
}

function buildMarkLineConfig(data) {
    return {
        symbol: ['none', 'none'],
        data: data,
        lineStyle: { width: 1.5 },
        label: { show: true, position: 'end', color: '#fff', fontSize: 10 }
    };
}

// ============================================================
// Equity option
// ============================================================

/**
 * Build equity chart option
 */
export function buildEquityOption({ data }) {
    if (!data || !data.equity_curve || data.equity_curve.length === 0) return null;

    const equityData = data.equity_curve.map(item => item.equity);
    const dates = data.equity_curve.map(item => new Date(item.timestamp).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    }));

    const drawdowns = calculateDrawdown(equityData);
    const baselineValue = equityData[0];
    const newHighIdx = detectNewHighs(equityData);
    const drawdownPeriods = detectDrawdownPeriods(equityData, 0.05);

    // Large data optimizations for equity chart
    const isLargeEquity = equityData.length > 5000;
    const isVeryLargeEquity = equityData.length > 10000;

    // markPoints for new highs (skip the first point — it's trivially a "new high")
    let newHighMarkPoints = newHighIdx
        .filter(i => i > 0)
        .map(i => ({
            coord: [i, equityData[i]],
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: { color: '#48bb78', borderColor: '#fff', borderWidth: 1 },
            label: { show: false }
        }));

    // Limit markPoints for very large data
    if (isVeryLargeEquity && newHighMarkPoints.length > 100) {
        newHighMarkPoints = newHighMarkPoints.slice(0, 100);
    }

    // markArea for drawdown periods deeper than threshold
    const drawdownMarkAreaData = drawdownPeriods.map(p => [
        {
            xAxis: p.start,
            itemStyle: { color: 'rgba(252, 129, 129, 0.12)' },
            label: {
                show: true,
                formatter: `回撤 ${(p.depth * 100).toFixed(1)}%`,
                position: 'insideTop',
                color: '#fc8181',
                fontSize: 10
            }
        },
        { xAxis: p.end }
    ]);

    return {
        backgroundColor: CHART_COLORS.background,
        animation: isVeryLargeEquity ? false : false,
        tooltip: buildEquityTooltipOption(),
        legend: buildEquityLegendConfig(),
        axisPointer: { link: [{ xAxisIndex: 'all' }] },
        grid: { left: '10%', right: '8%', top: '30%', bottom: '15%' },
        xAxis: buildEquityXAxisConfig(dates),
        yAxis: buildEquityYAxisConfig(),
        dataZoom: [{ type: 'inside', start: 0, end: 100 }],
        series: buildEquitySeriesConfig(equityData, drawdowns, baselineValue, newHighMarkPoints, drawdownMarkAreaData, isLargeEquity)
    };
}

function calculateDrawdown(equityData) {
    const peaks = [];
    let peak = 0;
    equityData.forEach(v => {
        if (v > peak) peak = v;
        peaks.push(peak);
    });
    return equityData.map((v, i) => peaks[i] > 0 ? (v - peaks[i]) / peaks[i] : 0);
}

function buildEquityTooltipOption() {
    return {
        trigger: 'axis',
        backgroundColor: CHART_COLORS.tooltipBg,
        borderColor: CHART_COLORS.borderColor,
        borderWidth: 1,
        padding: [10, 12],
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.4); border-radius: 6px;',
        formatter: function(params) {
            const equity = params.find(p => p.seriesName === '净值');
            const dd = params.find(p => p.seriesName === '回撤');
            if (!equity) return '';
            const ddVal = dd && typeof dd.data === 'number' ? (dd.data * 100).toFixed(2) : '0.00';
            const ddColor = dd && dd.data < -0.001 ? '#fc8181' : '#a0aec0';
            return `<div style="font-weight:600;margin-bottom:4px">${equity.axisValue}</div>` +
                `<div>净值&nbsp;&nbsp;<span style="color:#60a5fa;font-weight:600">${Number(equity.data).toLocaleString()}</span></div>` +
                `<div>回撤&nbsp;&nbsp;<span style="color:${ddColor};font-weight:600">${ddVal}%</span></div>`;
        }
    };
}

function buildEquityLegendConfig() {
    return {
        data: ['净值', '回撤'],
        textStyle: { color: '#a0aec0' },
        top: 0
    };
}

function buildEquityXAxisConfig(dates) {
    return {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: CHART_COLORS.lineColor } },
        axisLabel: { color: CHART_COLORS.textColor, show: false },
        splitLine: { show: false }
    };
}

function buildEquityYAxisConfig() {
    return [
        {
            scale: true,
            position: 'left',
            axisLine: { lineStyle: { color: CHART_COLORS.lineColor } },
            axisLabel: { color: CHART_COLORS.textColor, formatter: v => v.toLocaleString() },
            splitLine: { lineStyle: { color: '#2d3748', type: 'dashed' } }
        },
        {
            scale: true,
            position: 'right',
            axisLine: { lineStyle: { color: CHART_COLORS.lineColor } },
            axisLabel: { color: CHART_COLORS.textColor, formatter: v => (v * 100).toFixed(1) + '%' },
            splitLine: { show: false }
        }
    ];
}

function buildEquitySeriesConfig(equityData, drawdowns, baselineValue, newHighMarkPoints, drawdownMarkAreaData, isLargeData = false) {
    return [
        {
            name: '净值',
            type: 'line',
            data: equityData,
            smooth: true,
            lineStyle: { width: 2, color: CHART_COLORS.equityLine },
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: 'rgba(96, 165, 250, 0.3)' },
                        { offset: 1, color: 'rgba(96, 165, 250, 0.05)' }
                    ]
                }
            },
            symbol: 'none',
            ...(isLargeData ? { sampling: 'lttb' } : {}),
            markLine: {
                silent: true,
                symbol: ['none', 'none'],
                lineStyle: { color: '#a0aec0', type: 'dashed', width: 1 },
                label: {
                    show: true,
                    position: 'insideStartTop',
                    color: '#a0aec0',
                    fontSize: 10,
                    formatter: '基准'
                },
                data: [{ yAxis: baselineValue }]
            },
            markPoint: {
                symbol: 'circle',
                data: newHighMarkPoints,
                tooltip: {
                    trigger: 'item',
                    backgroundColor: CHART_COLORS.tooltipBg,
                    borderColor: CHART_COLORS.borderColor,
                    textStyle: { color: '#e2e8f0' },
                    formatter: p => `新高<br/>净值: ${Number(p.value).toLocaleString()}`
                }
            },
            markArea: {
                silent: true,
                data: drawdownMarkAreaData
            }
        },
        {
            name: '回撤',
            type: 'line',
            data: drawdowns,
            yAxisIndex: 1,
            smooth: true,
            lineStyle: { width: 1, color: CHART_COLORS.drawdownLine },
            symbol: 'none',
            ...(isLargeData ? { sampling: 'lttb' } : {})
        }
    ];
}

// ============================================================
// Tooltip content (K-Line)
// ============================================================

/**
 * Build tooltip content for K-Line chart (card-style, with OHLCV + 涨跌幅).
 * Uses pre-computed dateToBarIdx Map for O(1) annotation lookup.
 *
 * @param {Object[]} params - ECharts tooltip params
 * @param {Object} data - Chart data (bars, annotations, etc.)
 * @param {Map} [dateToBarIdx] - Pre-computed date string → bar index map
 */
export function buildTooltipContent(params, data, dateToBarIdx) {
    if (!params || params.length === 0) return '';

    let header = '';
    let kLineBlock = '';
    let volumeBlock = '';
    let maBlock = '';

    params.forEach(param => {
        if (!param) return;
        if (param.seriesType === 'candlestick' && Array.isArray(param.data)) {
            const arr = param.data;
            const offset = arr.length >= 5 ? 1 : 0;
            const open = +arr[offset];
            const close = +arr[offset + 1];
            const low = +arr[offset + 2];
            const high = +arr[offset + 3];
            const change = close - open;
            const changePct = open !== 0 ? (change / open) * 100 : 0;
            const color = change >= 0 ? '#48bb78' : '#fc8181';
            const sign = change >= 0 ? '+' : '';

            header = `<div style="font-weight:600;margin-bottom:6px;color:#e2e8f0">${param.axisValue || ''}</div>`;
            kLineBlock =
                `<div style="display:grid;grid-template-columns:auto auto;gap:2px 12px;font-size:11px">` +
                `<span style="color:#a0aec0">开盘</span><span>${open}</span>` +
                `<span style="color:#a0aec0">收盘</span><span style="color:${color};font-weight:600">${close}</span>` +
                `<span style="color:#a0aec0">最高</span><span>${high}</span>` +
                `<span style="color:#a0aec0">最低</span><span>${low}</span>` +
                `<span style="color:#a0aec0">涨跌</span><span style="color:${color};font-weight:600">${sign}${change.toFixed(2)} (${sign}${changePct.toFixed(2)}%)</span>` +
                `</div>`;
        } else if (param.seriesType === 'bar' && param.seriesName === '成交量') {
            const vol = typeof param.data === 'object' && param.data !== null ? param.data.value : param.data;
            volumeBlock = `<div style="margin-top:4px;color:#a0aec0;font-size:11px">成交量 <span style="color:#e2e8f0">${Number(vol).toLocaleString()}</span></div>`;
        } else if (param.seriesType === 'line' && (param.seriesName === 'MA5' || param.seriesName === 'MA20')) {
            if (param.data != null) {
                const c = param.seriesName === 'MA5' ? '#f6ad55' : '#9f7aea';
                maBlock += `<div style="font-size:11px"><span style="color:${c}">●</span> ${param.seriesName}: ${param.data}</div>`;
            }
        }
    });

    let result = header + kLineBlock + volumeBlock + (maBlock ? `<div style="margin-top:4px">${maBlock}</div>` : '');

    // Annotation labels at this timestamp — O(1) lookup via pre-computed Map
    if (data && data.bars && data.annotations && dateToBarIdx) {
        const idx = dateToBarIdx.get(params[0].axisValue);
        if (idx !== undefined) {
            const ts = data.bars[idx].timestamp;
            const related = data.annotations.filter(a => a.timestamp === ts);
            related.forEach(a => {
                if (a.data && a.data.label) {
                    result += `<div style="margin-top:3px;font-size:11px;color:${a.data.color || '#fff'}">▸ ${a.data.label}</div>`;
                }
            });
        }
    }

    return result;
}

// Re-export filter utilities for external use
export { filterValidMarkPoints, filterValidMarkLines };

// Re-export processAnnotations from annotation-renderer (single source of truth)
export { processAnnotations, getAnnotationRenderer } from './annotation-renderer.js';


/**
 * Process trades into markPoints.
 * Uses buildBarIndex for O(1) exact lookups; fuzzy match uses binary search on sorted ms array.
 */
export function processTrades(trades, bars) {
    const markPoints = [];
    if (!trades || !bars || bars.length === 0) return markPoints;

    // Build fast lookup: exact timestamp → index
    const barIndex = buildBarIndex(bars);

    // Sorted ms array for binary search fuzzy match
    const msArr = bars.map((b, i) => ({ ms: new Date(b.timestamp).getTime(), idx: i }));
    msArr.sort((a, b) => a.ms - b.ms);

    trades.forEach((trade) => {
        try {
            let idx = barIndex.get(trade.timestamp);
            if (idx === undefined) {
                idx = barIndex.get(new Date(trade.timestamp).getTime());
            }
            if (idx === undefined) {
                // Binary search for closest bar within 1 hour
                const targetTime = new Date(trade.timestamp).getTime();
                let lo = 0, hi = msArr.length - 1;
                while (lo <= hi) {
                    const mid = (lo + hi) >> 1;
                    if (msArr[mid].ms < targetTime) lo = mid + 1;
                    else hi = mid - 1;
                }
                // Check neighbors within 1 hour
                for (let k = Math.max(0, lo - 1); k <= Math.min(msArr.length - 1, lo + 1); k++) {
                    if (Math.abs(msArr[k].ms - targetTime) < 3600000) {
                        idx = msArr[k].idx;
                        break;
                    }
                }
            }
            if (idx !== undefined) {
                const price = bars[idx].close;
                if (isFinite(idx) && isFinite(price)) {
                    markPoints.push({
                        coord: [idx, price],
                        value: trade.side === 'BUY' ? '买入' : '卖出',
                        symbol: 'circle',
                        symbolSize: 12,
                        itemStyle: { color: trade.side === 'BUY' ? '#48bb78' : '#fc8181' }
                    });
                }
            }
        } catch (e) {
            console.error(`[ERROR] Trade process error: ${trade.timestamp}`, e.message);
        }
    });

    return markPoints;
}

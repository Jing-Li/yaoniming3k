/**
 * Caisen Visualization - Chart Builder
 * ECharts 图表构建器
 */

import { CHART_COLORS } from './constants.js';
import { processAnnotations, processTrades, getAnnotationRenderer } from './chart-config.js';
import { filterValidMarkPoints, filterValidMarkLines } from './utils.js';

/**
 * Build K-Line chart option
 * @param {Object} options - Chart options
 * @param {Object} options.data - Filtered data with bars, annotations, trades
 * @param {boolean} options.isZoomEnabled - Whether zoom is enabled
 * @returns {Object} ECharts option object
 */
export function buildKLineOption({ data, isZoomEnabled }) {
    if (!data || !data.bars || data.bars.length === 0) return null;

    // Prepare K-line data
    const dates = data.bars.map(bar => new Date(bar.timestamp).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    }));
    const klineData = data.bars.map(bar => [bar.open, bar.close, bar.low, bar.high]);
    const volumes = data.bars.map(bar => bar.volume);

    // Collect all annotations
    const { markPoints, markLines } = processAnnotations(data.annotations, data.bars);

    // Trades markers
    const tradeMarkers = processTrades(data.trades, data.bars);
    const allMarkPoints = [...markPoints, ...tradeMarkers];

    // Filter valid markPoints and markLines
    const finalMarkPoints = allMarkPoints;
    const finalMarkLines = markLines;

    // Chart options
    const option = {
        backgroundColor: CHART_COLORS.background,
        tooltip: buildTooltipOption(data),
        legend: { show: false },
        grid: buildGridConfig(),
        xAxis: buildXAxisConfig(dates),
        yAxis: buildYAxisConfig(),
        dataZoom: buildDataZoomConfig(isZoomEnabled),
        series: buildSeriesConfig(finalMarkPoints, finalMarkLines, volumes)
    };

    return option;
}

/**
 * Build tooltip option
 */
function buildTooltipOption(data) {
    return {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: CHART_COLORS.tooltipBg,
        borderColor: CHART_COLORS.borderColor,
        textStyle: { color: '#e2e8f0' },
        formatter: function(params) {
            return buildTooltipContent(params, data);
        }
    };
}

/**
 * Build grid configuration
 */
function buildGridConfig() {
    return [
        { left: '10%', right: '8%', top: '10%', height: '55%' },
        { left: '10%', right: '8%', top: '75%', height: '15%' }
    ];
}

/**
 * Build X axis configuration
 */
function buildXAxisConfig(dates) {
    return [
        { type: 'category', data: dates, gridIndex: 0, axisLine: { lineStyle: { color: CHART_COLORS.lineColor } }, axisLabel: { color: CHART_COLORS.textColor, show: false }, splitLine: { show: false } },
        { type: 'category', data: dates, gridIndex: 1, axisLine: { lineStyle: { color: CHART_COLORS.lineColor } }, axisLabel: { color: CHART_COLORS.textColor, fontSize: 11 }, splitLine: { show: false } }
    ];
}

/**
 * Build Y axis configuration
 */
function buildYAxisConfig() {
    return [
        { scale: true, gridIndex: 0, axisLine: { lineStyle: { color: CHART_COLORS.lineColor } }, axisLabel: { color: CHART_COLORS.textColor }, splitLine: { lineStyle: { color: '#2d3748', type: 'dashed' } } },
        { scale: true, gridIndex: 1, axisLine: { lineStyle: { color: CHART_COLORS.lineColor } }, axisLabel: { color: CHART_COLORS.textColor }, splitLine: { show: false } }
    ];
}

/**
 * Build data zoom configuration
 */
function buildDataZoomConfig(isZoomEnabled) {
    const baseConfig = { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 };
    if (isZoomEnabled) {
        return [baseConfig, { type: 'slider', xAxisIndex: [0, 1], start: 0, end: 100 }];
    }
    return [baseConfig];
}

/**
 * Build series configuration
 */
function buildSeriesConfig(markPoints, markLines, volumes) {
    return [
        {
            name: 'K线',
            type: 'candlestick',
            data: [],
            xAxisIndex: 0,
            yAxisIndex: 0,
            itemStyle: {
                color: CHART_COLORS.upColor,
                color0: CHART_COLORS.downColor,
                borderColor: CHART_COLORS.upColor,
                borderColor0: CHART_COLORS.downColor
            },
            markPoint: buildMarkPointConfig(markPoints),
            markLine: buildMarkLineConfig(markLines)
        },
        {
            name: '成交量',
            type: 'bar',
            data: volumes,
            xAxisIndex: 1,
            yAxisIndex: 1,
            itemStyle: { color: CHART_COLORS.lineColor }
        }
    ];
}

/**
 * Build markPoint configuration
 */
function buildMarkPointConfig(data) {
    return {
        symbol: 'pin',
        symbolSize: 30,
        data: data,
        label: { color: '#fff', fontSize: 10 },
        tooltip: { trigger: 'item', backgroundColor: CHART_COLORS.tooltipBg, borderColor: CHART_COLORS.borderColor, textStyle: { color: '#e2e8f0' } }
    };
}

/**
 * Build markLine configuration
 */
function buildMarkLineConfig(data) {
    return {
        symbol: ['none', 'none'],
        data: data,
        lineStyle: { width: 2 },
        label: { show: true, position: 'end', color: '#fff', fontSize: 11 }
    };
}

/**
 * Build equity chart option
 */
export function buildEquityOption({ data }) {
    if (!data || !data.equity_curve || data.equity_curve.length === 0) return null;

    const equityData = data.equity_curve.map(item => item.equity);
    const dates = data.equity_curve.map(item => new Date(item.timestamp).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    }));

    // Calculate drawdown
    const drawdowns = calculateDrawdown(equityData);

    return {
        backgroundColor: CHART_COLORS.background,
        tooltip: buildEquityTooltipOption(),
        legend: buildEquityLegendConfig(),
        grid: { left: '10%', right: '8%', top: '30%', bottom: '15%' },
        xAxis: buildEquityXAxisConfig(dates),
        yAxis: buildEquityYAxisConfig(),
        dataZoom: [{ type: 'inside', start: 0, end: 100 }],
        series: buildEquitySeriesConfig(equityData, drawdowns)
    };
}

/**
 * Calculate drawdown from equity curve
 */
function calculateDrawdown(equityData) {
    const peaks = [];
    let peak = 0;
    equityData.forEach(v => {
        if (v > peak) peak = v;
        peaks.push(peak);
    });
    return equityData.map((v, i) => (v - peaks[i]) / peaks[i]);
}

/**
 * Build equity tooltip option
 */
function buildEquityTooltipOption() {
    return {
        trigger: 'axis',
        backgroundColor: CHART_COLORS.tooltipBg,
        borderColor: CHART_COLORS.borderColor,
        textStyle: { color: '#e2e8f0' },
        formatter: function(params) {
            const equity = params.find(p => p.seriesName === '净值');
            const dd = params.find(p => p.seriesName === '回撤');
            if (equity) {
                return `<strong>${equity.axisValue}</strong><br/>净值: ${equity.data.toLocaleString()}<br/>回撤: ${(dd.data * 100).toFixed(2)}%`;
            }
            return '';
        }
    };
}

/**
 * Build equity legend config
 */
function buildEquityLegendConfig() {
    return {
        data: ['净值', '回撤'],
        textStyle: { color: '#a0aec0' },
        top: 0
    };
}

/**
 * Build equity X axis config
 */
function buildEquityXAxisConfig(dates) {
    return {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: CHART_COLORS.lineColor } },
        axisLabel: { color: CHART_COLORS.textColor, show: false },
        splitLine: { show: false }
    };
}

/**
 * Build equity Y axis config
 */
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

/**
 * Build equity series config
 */
function buildEquitySeriesConfig(equityData, drawdowns) {
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
            symbol: 'none'
        },
        {
            name: '回撤',
            type: 'line',
            data: drawdowns,
            yAxisIndex: 1,
            smooth: true,
            lineStyle: { width: 1, color: CHART_COLORS.drawdownLine },
            symbol: 'none'
        }
    ];
}

/**
 * Build tooltip content for K-Line chart
 */
export function buildTooltipContent(params, data) {
    let result = '';
    if (!params || params.length === 0) return result;

    params.forEach(param => {
        if (!param) return;
        if (param.seriesType === 'candlestick' && param.data) {
            result += `<strong>${param.axisValue || ''}</strong><br/>`;
            result += `开盘: ${param.data[0]}<br/>`;
            result += `收盘: ${param.data[1]}<br/>`;
            result += `最低: ${param.data[2]}<br/>`;
            result += `最高: ${param.data[3]}<br/>`;
        } else if (param.seriesType === 'bar') {
            result += `成交量: ${param.data}<br/>`;
        }
    });

    // Check for annotations at this point
    const dates = data.bars.map(bar => new Date(bar.timestamp).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    }));
    const idx = dates.indexOf(params[0].axisValue);
    if (idx >= 0 && data.annotations) {
        const ts = data.bars[idx].timestamp;
        const relatedAnnotations = data.annotations.filter(a => a.timestamp === ts);
        relatedAnnotations.forEach(a => {
            if (a.data.label) {
                result += `<br/><span style="color:${a.data.color || '#fff'}">${a.data.label}</span>`;
            }
        });
    }

    return result;
}

// Re-export from chart-config
export { processAnnotations, processTrades, getAnnotationRenderer } from './chart-config.js';
export { filterValidMarkPoints, filterValidMarkLines } from './utils.js';
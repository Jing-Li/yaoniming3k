/**
 * Caisen Visualization - Chart Configuration Builder
 * ECharts 配置构建器，生成 K 线图和净值曲线图的配置
 */

import { 
    formatTimestamp, 
    filterValidMarkPoints, 
    filterValidMarkLines,
    isValidCoord
} from './utils.js';
import { filterAnnotations } from './annotation-filter.js';

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

    // Collect all annotations (apply filter)
    const filteredAnnotations = filterAnnotations(data.annotations);
    const { markPoints, markLines } = processAnnotations(filteredAnnotations, data.bars);

    // Trades markers
    const tradeMarkers = processTrades(data.trades, data.bars);
    const allMarkPoints = [...markPoints, ...tradeMarkers];

    // Filter valid markPoints and markLines
    const finalMarkPoints = filterValidMarkPoints(allMarkPoints);
    const finalMarkLines = filterValidMarkLines(markLines);

    // Chart options
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            backgroundColor: '#1a1f36',
            borderColor: '#4a5568',
            textStyle: { color: '#e2e8f0' },
            formatter: function(params) {
                return buildTooltipContent(params, data);
            }
        },
        legend: { show: false },
        grid: [
            { left: '10%', right: '8%', top: '10%', height: '55%' },
            { left: '10%', right: '8%', top: '75%', height: '15%' }
        ],
        xAxis: [
            { type: 'category', data: dates, gridIndex: 0, axisLine: { lineStyle: { color: '#4a5568' } }, axisLabel: { color: '#718096', show: false }, splitLine: { show: false } },
            { type: 'category', data: dates, gridIndex: 1, axisLine: { lineStyle: { color: '#4a5568' } }, axisLabel: { color: '#718096', fontSize: 11 }, splitLine: { show: false } }
        ],
        yAxis: [
            { scale: true, gridIndex: 0, axisLine: { lineStyle: { color: '#4a5568' } }, axisLabel: { color: '#718096' }, splitLine: { lineStyle: { color: '#2d3748', type: 'dashed' } } },
            { scale: true, gridIndex: 1, axisLine: { lineStyle: { color: '#4a5568' } }, axisLabel: { color: '#718096' }, splitLine: { show: false } }
        ],
        dataZoom: isZoomEnabled ? [
            { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
            { type: 'slider', xAxisIndex: [0, 1], start: 0, end: 100 }
        ] : [
            { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 }
        ],
        series: [
            {
                name: 'K线',
                type: 'candlestick',
                data: klineData,
                xAxisIndex: 0,
                yAxisIndex: 0,
                itemStyle: {
                    color: '#48bb78',
                    color0: '#fc8181',
                    borderColor: '#48bb78',
                    borderColor0: '#fc8181'
                },
                markPoint: {
                    symbol: 'pin',
                    symbolSize: 30,
                    data: finalMarkPoints,
                    label: { color: '#fff', fontSize: 10 },
                    tooltip: { trigger: 'item', backgroundColor: '#1a1f36', borderColor: '#4a5568', textStyle: { color: '#e2e8f0' } }
                },
                markLine: {
                    symbol: ['none', 'none'],
                    data: finalMarkLines,
                    lineStyle: { width: 2 },
                    label: { show: true, position: 'end', color: '#fff', fontSize: 11 }
                }
            },
            {
                name: '成交量',
                type: 'bar',
                data: volumes,
                xAxisIndex: 1,
                yAxisIndex: 1,
                itemStyle: { color: '#4a5568' }
            }
        ]
    };

    return option;
}

/**
 * Build equity chart option
 * @param {Object} options - Chart options
 * @param {Object} options.data - Filtered data with equity_curve
 * @returns {Object} ECharts option object
 */
export function buildEquityOption({ data }) {
    if (!data || !data.equity_curve || data.equity_curve.length === 0) return null;

    const equityData = data.equity_curve.map(item => item.equity);
    const dates = data.equity_curve.map(item => new Date(item.timestamp).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    }));

    // Calculate drawdown
    const peaks = [];
    let peak = 0;
    equityData.forEach(v => {
        if (v > peak) peak = v;
        peaks.push(peak);
    });
    const drawdowns = equityData.map((v, i) => (v - peaks[i]) / peaks[i]);

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: '#1a1f36',
            borderColor: '#4a5568',
            textStyle: { color: '#e2e8f0' },
            formatter: function(params) {
                const equity = params.find(p => p.seriesName === '净值');
                const dd = params.find(p => p.seriesName === '回撤');
                if (equity) {
                    return `<strong>${equity.axisValue}</strong><br/>净值: ${equity.data.toLocaleString()}<br/>回撤: ${(dd.data * 100).toFixed(2)}%`;
                }
                return '';
            }
        },
        legend: {
            data: ['净值', '回撤'],
            textStyle: { color: '#a0aec0' },
            top: 0
        },
        grid: { left: '10%', right: '8%', top: '30%', bottom: '15%' },
        xAxis: {
            type: 'category',
            data: dates,
            axisLine: { lineStyle: { color: '#4a5568' } },
            axisLabel: { color: '#718096', show: false },
            splitLine: { show: false }
        },
        yAxis: [
            {
                scale: true,
                position: 'left',
                axisLine: { lineStyle: { color: '#4a5568' } },
                axisLabel: { color: '#718096', formatter: v => v.toLocaleString() },
                splitLine: { lineStyle: { color: '#2d3748', type: 'dashed' } }
            },
            {
                scale: true,
                position: 'right',
                axisLine: { lineStyle: { color: '#4a5568' } },
                axisLabel: { color: '#718096', formatter: v => (v * 100).toFixed(1) + '%' },
                splitLine: { show: false }
            }
        ],
        dataZoom: [
            { type: 'inside', start: 0, end: 100 }
        ],
        series: [
            {
                name: '净值',
                type: 'line',
                data: equityData,
                smooth: true,
                lineStyle: { width: 2, color: '#60a5fa' },
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
                lineStyle: { width: 1, color: '#fc8181' },
                symbol: 'none'
            }
        ]
    };

    return option;
}

/**
 * Build tooltip content for K-Line chart
 * @param {Object[]} params - ECharts tooltip params
 * @param {Object} data - Full data object with annotations
 * @returns {string} HTML content for tooltip
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

/**
 * Process annotations into markPoints and markLines
 * @param {Object[]} annotations - Array of annotation objects
 * @param {Object[]} bars - Array of bar objects
 * @returns {Object} { markPoints, markLines }
 */
export function processAnnotations(annotations, bars) {
    const markPoints = [];
    const markLines = [];

    if (!annotations) return { markPoints, markLines };

    annotations.forEach((annotation) => {
        const ctx = { markPoints, markLines };
        const renderFn = getAnnotationRenderer(annotation.type);
        if (renderFn) {
            try {
                renderFn(ctx, annotation, bars);
            } catch (e) {
                console.error(`[ERROR] Annotation render error: ${annotation.type}`, e.message);
            }
        }
    });

    return { markPoints, markLines };
}

/**
 * Process trades into markPoints
 * @param {Object[]} trades - Array of trade objects
 * @param {Object[]} bars - Array of bar objects
 * @returns {Object[]} Array of markPoint objects
 */
export function processTrades(trades, bars) {
    const markPoints = [];

    if (!trades) return markPoints;

    trades.forEach((trade) => {
        try {
            const bar = bars.find(b => b.timestamp === trade.timestamp ||
                Math.abs(new Date(b.timestamp) - new Date(trade.timestamp)) < 3600000);
            if (bar) {
                const idx = bars.indexOf(bar);
                const price = bar.close;
                if (idx >= 0 && isFinite(idx) && isFinite(price)) {
                    const mp = {
                        coord: [idx, price],
                        value: trade.side === 'BUY' ? '买入' : '卖出',
                        symbol: 'circle',
                        symbolSize: 12,
                        itemStyle: { color: trade.side === 'BUY' ? '#48bb78' : '#fc8181' }
                    };
                    markPoints.push(mp);
                }
            }
        } catch (e) {
            console.error(`[ERROR] Trade process error: ${trade.timestamp}`, e.message);
        }
    });

    return markPoints;
}

/**
 * Get annotation renderer function by type
 * @param {string} type - Annotation type
 * @returns {Function|null} Renderer function
 */
export function getAnnotationRenderer(type) {
    const renderers = {
        buy_signal: renderBuySignal,
        sell_signal: renderSellSignal,
        neutral_signal: renderNeutralSignal,
        horizontal_line: renderHorizontalLine,
        trend_line: renderTrendLine,
        pattern_mark: renderPatternMark,
        support_zone: renderSupportZone,
        resistance_zone: renderResistanceZone,
        volume_spike: renderVolumeSpike,
        text_label: renderTextLabel,
        rectangle: renderRectangle,
        polygon: renderPolygon
    };
    return renderers[type] || null;
}

// Annotation renderer functions
function renderBuySignal(ctx, annotation, bars) {
    let bar = bars.find(b => new Date(b.timestamp).getTime() === new Date(annotation.timestamp).getTime());
    if (!bar) {
        bar = bars.find(b => Math.abs(new Date(b.timestamp) - new Date(annotation.timestamp)) < 3600000);
    }
    if (bar) {
        const idx = bars.indexOf(bar);
        if (idx >= 0 && bar.close !== undefined && isFinite(bar.close)) {
            const color = annotation.data.color || '#48bb78';
            const mp = {
                coord: [idx, bar.close],
                value: annotation.data.label || '买入',
                symbol: 'triangle',
                symbolSize: 14,
                itemStyle: { color: color, borderColor: '#fff', borderWidth: 1 }
            };
            ctx.markPoints.push(mp);
        }
    }
}

function renderSellSignal(ctx, annotation, bars) {
    let bar = bars.find(b => new Date(b.timestamp).getTime() === new Date(annotation.timestamp).getTime());
    if (!bar) {
        bar = bars.find(b => Math.abs(new Date(b.timestamp) - new Date(annotation.timestamp)) < 3600000);
    }
    if (bar) {
        const idx = bars.indexOf(bar);
        if (idx >= 0 && bar.close !== undefined && isFinite(bar.close)) {
            const color = annotation.data.color || '#fc8181';
            const mp = {
                coord: [idx, bar.close],
                value: annotation.data.label || '卖出',
                symbol: 'triangle',
                symbolSize: 14,
                symbolRotate: 180,
                itemStyle: { color: color, borderColor: '#fff', borderWidth: 1 }
            };
            ctx.markPoints.push(mp);
        }
    }
}

function renderNeutralSignal(ctx, annotation, bars) {
    let bar = bars.find(b => new Date(b.timestamp).getTime() === new Date(annotation.timestamp).getTime());
    if (!bar) {
        bar = bars.find(b => Math.abs(new Date(b.timestamp) - new Date(annotation.timestamp)) < 3600000);
    }
    if (bar) {
        const idx = bars.indexOf(bar);
        if (idx >= 0 && bar.close !== undefined && isFinite(bar.close)) {
            const mp = {
                coord: [idx, bar.close],
                value: annotation.data.label || '中性',
                symbol: 'diamond',
                symbolSize: 12,
                itemStyle: { color: '#a0aec0', borderColor: '#fff', borderWidth: 1 }
            };
            ctx.markPoints.push(mp);
        }
    }
}

function renderHorizontalLine(ctx, annotation, bars) {
    const price = annotation.data.price;
    if (typeof price !== 'number' || !isFinite(price)) {
        return;
    }

    const ml = {
        yAxis: price,
        lineStyle: {
            color: annotation.data.color || '#60a5fa',
            type: 'dashed',
            width: 1
        },
        label: {
            formatter: annotation.data.label || '',
            position: 'end'
        }
    };
    ctx.markLines.push(ml);
}

function renderTrendLine(ctx, annotation, bars) {
    const startTimestamp = annotation.data.start?.timestamp || annotation.data.start;
    const endTimestamp = annotation.data.end?.timestamp || annotation.data.end;

    const startBar = bars.find(b => new Date(b.timestamp).getTime() === new Date(startTimestamp).getTime());
    const endBar = bars.find(b => new Date(b.timestamp).getTime() === new Date(endTimestamp).getTime());

    if (startBar && endBar) {
        const startIdx = bars.indexOf(startBar);
        const endIdx = bars.indexOf(endBar);
        if (startIdx >= 0 && endIdx >= 0 && isFinite(startBar.close) && isFinite(endBar.close)) {
            const ml = {
                coords: [
                    [startIdx, startBar.close],
                    [endIdx, endBar.close]
                ],
                lineStyle: {
                    color: annotation.data.color || '#ed8936',
                    width: 2
                },
                label: { formatter: annotation.data.label || '', position: 'middle' }
            };
            ctx.markLines.push(ml);
        }
    }
}

function renderPatternMark(ctx, annotation, bars) {
    const points = annotation.data.points || [];
    const pattern = annotation.data.pattern;
    const color = annotation.data.color || '#9f7aea';
    const label = annotation.data.label || pattern;

    const coords = [];
    points.forEach((point) => {
        const bar = bars.find(b => {
            const targetTime = new Date(point.timestamp || point).getTime();
            return new Date(b.timestamp).getTime() === targetTime ||
                Math.abs(new Date(b.timestamp) - targetTime) < 3600000;
        });
        if (bar) {
            const idx = bars.indexOf(bar);
            const price = point.price || bar.close;
            if (idx >= 0 && isFinite(idx) && isFinite(price)) {
                coords.push([idx, price]);
            }
        }
    });

    if (coords.length >= 2) {
        const ml = {
            coords: coords,
            lineStyle: {
                color: color,
                width: 2,
                type: 'solid'
            },
            label: { formatter: label, position: 'middle', color: color }
        };
        ctx.markLines.push(ml);

        // Draw neckline for head and shoulders patterns
        if (annotation.data.neckline && coords.length >= 2) {
            const necklinePrice = annotation.data.neckline.price;
            if (typeof necklinePrice === 'number' && isFinite(necklinePrice)) {
                const startIdx = coords[0][0];
                const endIdx = coords[coords.length - 1][0];

                if (startIdx !== undefined && endIdx !== undefined && isFinite(startIdx) && isFinite(endIdx)) {
                    const mlNeck = {
                        coords: [
                            [startIdx, necklinePrice],
                            [endIdx, necklinePrice]
                        ],
                        lineStyle: {
                            color: color,
                            width: 1,
                            type: 'dashed'
                        }
                    };
                    ctx.markLines.push(mlNeck);
                }
            }
        }

        // Draw point markers
        coords.forEach((coord, idx) => {
            if (coord && coord[0] !== undefined && coord[1] !== undefined &&
                isFinite(coord[0]) && isFinite(coord[1])) {
                const pointLabel = points[idx]?.label || '';
                const mp = {
                    coord: coord,
                    value: pointLabel,
                    symbol: 'circle',
                    symbolSize: 8,
                    itemStyle: { color: color, borderColor: '#fff', borderWidth: 1 }
                };
                ctx.markPoints.push(mp);
            }
        });
    }
}

function renderSupportZone(ctx, annotation, bars) {
    const price = annotation.data.price;
    if (typeof price !== 'number' || !isFinite(price)) {
        return;
    }
    const ml = {
        yAxis: price,
        lineStyle: {
            color: '#48bb78',
            width: 2,
            type: 'dashed'
        },
        label: { formatter: annotation.data.label || '支撑', position: 'end' }
    };
    ctx.markLines.push(ml);
}

function renderResistanceZone(ctx, annotation, bars) {
    const price = annotation.data.price;
    if (typeof price !== 'number' || !isFinite(price)) {
        return;
    }
    const ml = {
        yAxis: price,
        lineStyle: {
            color: '#fc8181',
            width: 2,
            type: 'dashed'
        },
        label: { formatter: annotation.data.label || '阻力', position: 'end' }
    };
    ctx.markLines.push(ml);
}

function renderVolumeSpike(ctx, annotation, bars) {
    // Volume spikes handled in volume series, marking is visual cue
}

function renderTextLabel(ctx, annotation, bars) {
    let bar = bars.find(b => new Date(b.timestamp).getTime() === new Date(annotation.timestamp).getTime());
    if (!bar) {
        bar = bars.find(b => Math.abs(new Date(b.timestamp) - new Date(annotation.timestamp)) < 3600000);
    }
    if (bar) {
        const idx = bars.indexOf(bar);
        const price = annotation.data.price || bar.close;
        if (idx >= 0 && isFinite(idx) && isFinite(price)) {
            const mp = {
                coord: [idx, price],
                value: annotation.data.text || '',
                symbol: 'none',
                label: {
                    show: true,
                    formatter: annotation.data.text || '',
                    color: annotation.data.color || '#fff',
                    fontSize: 12,
                    backgroundColor: 'rgba(0,0,0,0.5)',
                    padding: [4, 8],
                    borderRadius: 4
                }
            };
            ctx.markPoints.push(mp);
        }
    }
}

function renderRectangle(ctx, annotation, bars) {
    const startBar = bars.find(b => new Date(b.timestamp).getTime() === new Date(annotation.data.start).getTime());
    const endBar = bars.find(b => new Date(b.timestamp).getTime() === new Date(annotation.data.end).getTime());
    if (startBar && endBar) {
        const startIdx = bars.indexOf(startBar);
        const endIdx = bars.indexOf(endBar);
        if (startIdx >= 0 && endIdx >= 0 && isFinite(startBar.close) && isFinite(endBar.close)) {
            const ml = {
                coords: [
                    [startIdx, startBar.close],
                    [endIdx, endBar.close]
                ],
                lineStyle: {
                    color: annotation.data.color || '#f6ad55',
                    width: 2
                }
            };
            ctx.markLines.push(ml);
        }
    }
}

function renderPolygon(ctx, annotation, bars) {
    const points = annotation.data.points || [];
    const coords = [];
    points.forEach((point) => {
        const bar = bars.find(b => {
            const targetTime = new Date(point).getTime();
            return new Date(b.timestamp).getTime() === targetTime ||
                Math.abs(new Date(b.timestamp) - targetTime) < 3600000;
        });
        if (bar) {
            const idx = bars.indexOf(bar);
            if (idx >= 0 && isFinite(bar.close)) {
                coords.push([idx, bar.close]);
            }
        }
    });

    if (coords.length >= 2) {
        const ml = {
            coords: coords,
            lineStyle: {
                color: annotation.data.color || '#b794f4',
                width: 2
            },
            label: { formatter: annotation.data.label || '', position: 'middle' }
        };
        ctx.markLines.push(ml);
    }
}
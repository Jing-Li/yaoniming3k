/**
 * Caisen Visualization - Annotation Renderer
 * Annotation 渲染器，将 annotation 数据转换为 ECharts markPoints/markLines
 */

import { findBarByTimestamp, isValidCoord, isFiniteNum } from './utils.js';

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

    annotations.forEach((annotation, idx) => {
        const ctx = { markPoints, markLines };
        const renderFn = getAnnotationRenderer(annotation.type);
        if (renderFn) {
            try {
                renderFn(ctx, annotation, bars);
            } catch (e) {
                console.error(`[ERROR] Annotation[${idx}] render error: ${annotation.type}`, e.message);
            }
        } else {
            console.warn(`[WARN] No renderer for annotation type: ${annotation.type}`);
        }
    });

    return { markPoints, markLines };
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

/**
 * Get all supported annotation types
 * @returns {string[]} Array of supported annotation types
 */
export function getSupportedAnnotationTypes() {
    return [
        'buy_signal',
        'sell_signal',
        'neutral_signal',
        'horizontal_line',
        'trend_line',
        'pattern_mark',
        'support_zone',
        'resistance_zone',
        'volume_spike',
        'text_label',
        'rectangle',
        'polygon'
    ];
}

// ============ Annotation Renderer Functions ============

/**
 * Render buy signal annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderBuySignal(ctx, annotation, bars) {
    const bar = findBarByTimestamp(bars, annotation.timestamp);
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

/**
 * Render sell signal annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderSellSignal(ctx, annotation, bars) {
    const bar = findBarByTimestamp(bars, annotation.timestamp);
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

/**
 * Render neutral signal annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderNeutralSignal(ctx, annotation, bars) {
    const bar = findBarByTimestamp(bars, annotation.timestamp);
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

/**
 * Render horizontal line annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderHorizontalLine(ctx, annotation, bars) {
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

/**
 * Render trend line annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderTrendLine(ctx, annotation, bars) {
    const startTimestamp = annotation.data.start?.timestamp || annotation.data.start;
    const endTimestamp = annotation.data.end?.timestamp || annotation.data.end;

    const startBar = findBarByTimestamp(bars, startTimestamp);
    const endBar = findBarByTimestamp(bars, endTimestamp);

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

/**
 * Render pattern mark annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderPatternMark(ctx, annotation, bars) {
    const points = annotation.data.points || [];
    const pattern = annotation.data.pattern;
    const color = annotation.data.color || '#9f7aea';
    const label = annotation.data.label || pattern;

    const coords = [];
    points.forEach((point, pIdx) => {
        const bar = findBarByTimestamp(bars, point.timestamp || point);
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

/**
 * Render support zone annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderSupportZone(ctx, annotation, bars) {
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

/**
 * Render resistance zone annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderResistanceZone(ctx, annotation, bars) {
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

/**
 * Render volume spike annotation (no-op, handled in volume series)
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderVolumeSpike(ctx, annotation, bars) {
    // Volume spikes handled in volume series, marking is visual cue
}

/**
 * Render text label annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderTextLabel(ctx, annotation, bars) {
    const bar = findBarByTimestamp(bars, annotation.timestamp);
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

/**
 * Render rectangle annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderRectangle(ctx, annotation, bars) {
    const startBar = findBarByTimestamp(bars, annotation.data.start);
    const endBar = findBarByTimestamp(bars, annotation.data.end);
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

/**
 * Render polygon annotation
 * @param {Object} ctx - Render context with markPoints, markLines arrays
 * @param {Object} annotation - Annotation object
 * @param {Object[]} bars - Array of bar objects
 */
export function renderPolygon(ctx, annotation, bars) {
    const points = annotation.data.points || [];
    const coords = [];
    points.forEach((point, pIdx) => {
        const bar = findBarByTimestamp(bars, point);
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
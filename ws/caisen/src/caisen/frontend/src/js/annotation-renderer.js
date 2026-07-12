/**
 * Caisen Visualization - Annotation Renderer
 * Annotation 渲染器，将 annotation 数据转换为 ECharts markPoints/markLines
 *
 * 性能优化：使用 buildBarIndex 预建 O(1) 时间戳→索引 Map，
 * 避免每根标注都做 O(n) 线性扫描。
 */

import { buildBarIndex, findBarByIndex, isFiniteNum } from './utils.js';
import { ANNOTATION_TYPES, ANNOTATION_CONFIG } from './annotation-schema.js';

/**
 * Process annotations into markPoints and markLines.
 * Builds a timestamp→index Map once for O(1) lookups across all renderers.
 *
 * @param {Object[]} annotations - Array of annotation objects
 * @param {Object[]} bars - Array of bar objects
 * @returns {Object} { markPoints, markLines }
 */
export function processAnnotations(annotations, bars) {
    const markPoints = [];
    const markLines = [];

    if (!annotations) return { markPoints, markLines };

    // Build O(1) index map once per render cycle
    const barIndex = buildBarIndex(bars);
    const ctx = { markPoints, markLines, barIndex };

    annotations.forEach((annotation, idx) => {
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
        [ANNOTATION_TYPES.BUY_SIGNAL]: renderBuySignal,
        [ANNOTATION_TYPES.SELL_SIGNAL]: renderSellSignal,
        [ANNOTATION_TYPES.NEUTRAL_SIGNAL]: renderNeutralSignal,
        [ANNOTATION_TYPES.HORIZONTAL_LINE]: renderHorizontalLine,
        [ANNOTATION_TYPES.TREND_LINE]: renderTrendLine,
        [ANNOTATION_TYPES.PATTERN_MARK]: renderPatternMark,
        [ANNOTATION_TYPES.SUPPORT_ZONE]: renderSupportZone,
        [ANNOTATION_TYPES.RESISTANCE_ZONE]: renderResistanceZone,
        [ANNOTATION_TYPES.VOLUME_SPIKE]: renderVolumeSpike,
        [ANNOTATION_TYPES.TEXT_LABEL]: renderTextLabel,
        [ANNOTATION_TYPES.RECTANGLE]: renderRectangle,
        [ANNOTATION_TYPES.POLYGON]: renderPolygon
    };
    return renderers[type] || null;
}

/**
 * Get all supported annotation types
 * @returns {string[]} Array of supported annotation types
 */
export function getSupportedAnnotationTypes() {
    return Object.values(ANNOTATION_TYPES);
}

// ============ Internal helper ============

/**
 * O(1) lookup: find bar index using pre-built Map.
 * Returns { index, bar } or null.
 */
function _find(bars, ctx, timestamp) {
    return findBarByIndex(bars, ctx.barIndex, timestamp);
}

// ============ Annotation Renderer Functions ============

/**
 * Render buy signal annotation
 */
export function renderBuySignal(ctx, annotation, bars) {
    const found = _find(bars, ctx, annotation.timestamp);
    if (!found) return;
    const { index: idx, bar } = found;
    if (idx >= 0 && bar.close !== undefined && isFinite(bar.close)) {
        const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.BUY_SIGNAL];
        const color = annotation.data.color || config.color;
        ctx.markPoints.push({
            coord: [idx, bar.close],
            value: annotation.data.label || config.defaultLabel,
            symbol: config.symbol,
            symbolSize: config.symbolSize,
            itemStyle: { color, borderColor: '#fff', borderWidth: 1 }
        });
    }
}

/**
 * Render sell signal annotation
 */
export function renderSellSignal(ctx, annotation, bars) {
    const found = _find(bars, ctx, annotation.timestamp);
    if (!found) return;
    const { index: idx, bar } = found;
    if (idx >= 0 && bar.close !== undefined && isFinite(bar.close)) {
        const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.SELL_SIGNAL];
        const color = annotation.data.color || config.color;
        ctx.markPoints.push({
            coord: [idx, bar.close],
            value: annotation.data.label || config.defaultLabel,
            symbol: config.symbol,
            symbolSize: config.symbolSize,
            symbolRotate: config.symbolRotate,
            itemStyle: { color, borderColor: '#fff', borderWidth: 1 }
        });
    }
}

/**
 * Render neutral signal annotation
 */
export function renderNeutralSignal(ctx, annotation, bars) {
    const found = _find(bars, ctx, annotation.timestamp);
    if (!found) return;
    const { index: idx, bar } = found;
    if (idx >= 0 && bar.close !== undefined && isFinite(bar.close)) {
        const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.NEUTRAL_SIGNAL];
        ctx.markPoints.push({
            coord: [idx, bar.close],
            value: annotation.data.label || config.defaultLabel,
            symbol: config.symbol,
            symbolSize: config.symbolSize,
            itemStyle: { color: config.color, borderColor: '#fff', borderWidth: 1 }
        });
    }
}

/**
 * Render horizontal line annotation
 */
export function renderHorizontalLine(ctx, annotation, bars) {
    const price = annotation.data.price;
    if (typeof price !== 'number' || !isFinite(price)) return;

    const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.HORIZONTAL_LINE];
    ctx.markLines.push({
        yAxis: price,
        lineStyle: {
            color: annotation.data.color || config.color,
            type: config.lineStyle,
            width: config.lineWidth
        },
        label: { formatter: annotation.data.label || '', position: 'end' }
    });
}

/**
 * Render trend line annotation
 */
export function renderTrendLine(ctx, annotation, bars) {
    const startTimestamp = annotation.data.start?.timestamp || annotation.data.start;
    const endTimestamp = annotation.data.end?.timestamp || annotation.data.end;

    const startFound = _find(bars, ctx, startTimestamp);
    const endFound = _find(bars, ctx, endTimestamp);

    if (startFound && endFound) {
        const { index: startIdx, bar: startBar } = startFound;
        const { index: endIdx, bar: endBar } = endFound;
        if (startIdx >= 0 && endIdx >= 0 && isFinite(startBar.close) && isFinite(endBar.close)) {
            const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.TREND_LINE];
            ctx.markLines.push({
                coords: [[startIdx, startBar.close], [endIdx, endBar.close]],
                lineStyle: {
                    color: annotation.data.color || config.color,
                    width: config.lineWidth
                },
                label: { formatter: annotation.data.label || '', position: 'middle' }
            });
        }
    }
}

/**
 * Render pattern mark annotation — draws connecting lines + point markers.
 */
export function renderPatternMark(ctx, annotation, bars) {
    const points = annotation.data.points || [];
    const pattern = annotation.data.pattern;
    const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.PATTERN_MARK];
    const color = annotation.data.color || config.color;
    const label = annotation.data.label || pattern;

    const coords = [];
    points.forEach((point) => {
        const found = _find(bars, ctx, point.timestamp || point);
        if (found) {
            const price = point.price || found.bar.close;
            if (isFinite(found.index) && isFinite(price)) {
                coords.push([found.index, price]);
            }
        }
    });

    if (coords.length >= 2) {
        ctx.markLines.push({
            coords,
            lineStyle: { color, width: config.lineWidth, type: 'solid' },
            label: { formatter: label, position: 'middle', color }
        });

        // Draw neckline for head and shoulders patterns
        if (annotation.data.neckline && coords.length >= 2) {
            const necklinePrice = annotation.data.neckline.price;
            if (typeof necklinePrice === 'number' && isFinite(necklinePrice)) {
                const startIdx = coords[0][0];
                const endIdx = coords[coords.length - 1][0];
                if (isFinite(startIdx) && isFinite(endIdx)) {
                    ctx.markLines.push({
                        coords: [[startIdx, necklinePrice], [endIdx, necklinePrice]],
                        lineStyle: { color, width: 1, type: 'dashed' }
                    });
                }
            }
        }

        // Draw point markers at each key point
        coords.forEach((coord, idx) => {
            if (coord && isFinite(coord[0]) && isFinite(coord[1])) {
                ctx.markPoints.push({
                    coord,
                    value: points[idx]?.label || '',
                    symbol: 'circle',
                    symbolSize: 8,
                    itemStyle: { color, borderColor: '#fff', borderWidth: 1 }
                });
            }
        });
    } else if (coords.length === 1) {
        // Single point: show as a marker without line
        const coord = coords[0];
        if (isFinite(coord[0]) && isFinite(coord[1])) {
            ctx.markPoints.push({
                coord,
                value: label || '',
                symbol: 'diamond',
                symbolSize: 12,
                itemStyle: { color, borderColor: '#fff', borderWidth: 1 }
            });
        }
    } else if (points.length === 0 && annotation.timestamp) {
        // No key points provided — show a marker at the annotation timestamp
        const found = _find(bars, ctx, annotation.timestamp);
        if (found && isFinite(found.index) && isFinite(found.bar.close)) {
            ctx.markPoints.push({
                coord: [found.index, found.bar.close],
                value: label || '',
                symbol: 'diamond',
                symbolSize: 14,
                itemStyle: { color, borderColor: '#fff', borderWidth: 1 }
            });
        }
    }
}

/**
 * Render support zone annotation
 */
export function renderSupportZone(ctx, annotation, bars) {
    const price = annotation.data.price;
    if (typeof price !== 'number' || !isFinite(price)) return;
    const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.SUPPORT_ZONE];
    ctx.markLines.push({
        yAxis: price,
        lineStyle: {
            color: annotation.data.color || config.color,
            width: config.lineWidth,
            type: config.lineStyle
        },
        label: { formatter: annotation.data.label || config.defaultLabel, position: 'end' }
    });
}

/**
 * Render resistance zone annotation
 */
export function renderResistanceZone(ctx, annotation, bars) {
    const price = annotation.data.price;
    if (typeof price !== 'number' || !isFinite(price)) return;
    const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.RESISTANCE_ZONE];
    ctx.markLines.push({
        yAxis: price,
        lineStyle: {
            color: annotation.data.color || config.color,
            width: config.lineWidth,
            type: config.lineStyle
        },
        label: { formatter: annotation.data.label || config.defaultLabel, position: 'end' }
    });
}

/**
 * Render volume spike annotation (no-op, handled in volume series)
 */
export function renderVolumeSpike(ctx, annotation, bars) {
    // Volume spikes handled in volume series, marking is visual cue
}

/**
 * Render text label annotation
 */
export function renderTextLabel(ctx, annotation, bars) {
    const found = _find(bars, ctx, annotation.timestamp);
    if (!found) return;
    const { index: idx, bar } = found;
    const price = annotation.data.price || bar.close;
    if (idx >= 0 && isFinite(idx) && isFinite(price)) {
        const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.TEXT_LABEL];
        ctx.markPoints.push({
            coord: [idx, price],
            value: annotation.data.text || '',
            symbol: 'none',
            label: {
                show: true,
                formatter: annotation.data.text || '',
                color: annotation.data.color || config.color,
                fontSize: config.fontSize,
                backgroundColor: config.backgroundColor,
                padding: [4, 8],
                borderRadius: 4
            }
        });
    }
}

/**
 * Render rectangle annotation
 */
export function renderRectangle(ctx, annotation, bars) {
    const startFound = _find(bars, ctx, annotation.data.start);
    const endFound = _find(bars, ctx, annotation.data.end);
    if (startFound && endFound) {
        const { index: startIdx, bar: startBar } = startFound;
        const { index: endIdx, bar: endBar } = endFound;
        if (startIdx >= 0 && endIdx >= 0 && isFinite(startBar.close) && isFinite(endBar.close)) {
            const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.RECTANGLE];
            ctx.markLines.push({
                coords: [[startIdx, startBar.close], [endIdx, endBar.close]],
                lineStyle: {
                    color: annotation.data.color || config.color,
                    width: config.lineWidth
                }
            });
        }
    }
}

/**
 * Render polygon annotation
 */
export function renderPolygon(ctx, annotation, bars) {
    const points = annotation.data.points || [];
    const coords = [];
    points.forEach((point) => {
        const found = _find(bars, ctx, point);
        if (found) {
            if (isFinite(found.bar.close)) {
                coords.push([found.index, found.bar.close]);
            }
        }
    });

    if (coords.length >= 2) {
        const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.POLYGON];
        ctx.markLines.push({
            coords,
            lineStyle: {
                color: annotation.data.color || config.color,
                width: config.lineWidth
            },
            label: { formatter: annotation.data.label || '', position: 'middle' }
        });
    }
}

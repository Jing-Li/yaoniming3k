/**
 * Caisen Visualization - Annotation Overlay
 * Canvas 叠加层，在 Lightweight Charts 上绘制复杂标注
 *
 * 处理 trend_line, pattern_mark, rectangle, polygon, text_label 等
 * 不适合用 LWC priceLine/markers 的复杂图形标注
 */

import { buildBarIndex, findBarByIndex, isFiniteNum } from './utils.js';
import { ANNOTATION_TYPES, ANNOTATION_CONFIG } from './annotation-schema.js';
import { PATTERN_COLORS } from './constants.js';
import { createLogger } from './logger.js';

const log = createLogger('AnnotationOverlay');

// ============================================================
// Overlay creation
// ============================================================

/**
 * Create a canvas overlay positioned on top of the LWC chart container.
 * The overlay is transparent to mouse events so chart interaction works normally.
 *
 * @param {HTMLElement} chartContainer - The LWC chart container element
 * @returns {{ canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D }}
 */
export function createOverlay(chartContainer) {
  // Ensure container is positioned
  if (getComputedStyle(chartContainer).position === 'static') {
    chartContainer.style.position = 'relative';
  }

  const canvas = document.createElement('canvas');
  canvas.className = 'annotation-overlay';
  canvas.style.cssText = `
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 10;
  `;

  chartContainer.appendChild(canvas);

  const dpr = window.devicePixelRatio || 1;
  const rect = chartContainer.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  return { canvas, ctx };
}

/**
 * Resize overlay canvas to match container
 */
function resizeOverlay(canvas, chartContainer) {
  const dpr = window.devicePixelRatio || 1;
  const rect = chartContainer.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  return ctx;
}

// ============================================================
// Main render function
// ============================================================

/**
 * Render all complex annotations onto the canvas overlay.
 * Called on initial render and on chart scroll/zoom.
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {HTMLCanvasElement} canvas
 * @param {Object} chart - LWC chart instance
 * @param {Object} candleSeries - LWC candlestick series
 * @param {Object} data - { bars, annotations }
 */
export function renderAnnotationOverlay(ctx, canvas, chart, candleSeries, data) {
  if (!data?.annotations || !data?.bars || data.bars.length === 0) return;

  const dpr = window.devicePixelRatio || 1;
  const w = canvas.width / dpr;
  const h = canvas.height / dpr;

  // Clear canvas
  ctx.clearRect(0, 0, w, h);

  const barIndex = buildBarIndex(data.bars);
  const timeScale = chart.timeScale();
  
  // Viewport culling: only render visible annotations
  const visibleRange = timeScale.getVisibleLogicalRange();
  if (!visibleRange) return;
  
  const firstVisibleTime = timeScale.coordinateToTime(0);
  const lastVisibleTime = timeScale.coordinateToTime(w);
  if (firstVisibleTime === null || lastVisibleTime === null) return;

  // Helper: convert (barIndex, price) → canvas (x, y)
  const toXY = (idx, price) => {
    if (idx < 0 || idx >= data.bars.length) return null;
    const time = Math.floor(new Date(data.bars[idx].timestamp).getTime() / 1000);
    const x = timeScale.timeToCoordinate(time);
    const y = candleSeries.priceToCoordinate(price);
    if (x === null || y === null) return null;
    return { x, y };
  };

  // Helper: find bar index by timestamp
  const findIdx = (timestamp) => {
    const found = findBarByIndex(data.bars, barIndex, timestamp);
    return found ? found.index : -1;
  };

  // Process each annotation (with viewport culling)
  data.annotations.forEach((ann, i) => {
    try {
      // Quick viewport check for pattern_mark
      if (ann.type === ANNOTATION_TYPES.PATTERN_MARK) {
        const annTime = Math.floor(new Date(ann.timestamp).getTime() / 1000);
        if (annTime < firstVisibleTime || annTime > lastVisibleTime) return;
      }
      renderAnnotation(ctx, ann, data.bars, barIndex, toXY, findIdx);
    } catch (e) {
      // Silently skip failed annotations
    }
  });
}

// ============================================================
// Individual annotation renderers
// ============================================================

function renderAnnotation(ctx, ann, bars, barIndex, toXY, findIdx) {
  switch (ann.type) {
    case ANNOTATION_TYPES.TREND_LINE:
      renderTrendLine(ctx, ann, bars, findIdx, toXY);
      break;
    case ANNOTATION_TYPES.PATTERN_MARK:
      renderPatternMark(ctx, ann, bars, barIndex, findIdx, toXY);
      break;
    case ANNOTATION_TYPES.RECTANGLE:
      renderRectangle(ctx, ann, bars, findIdx, toXY);
      break;
    case ANNOTATION_TYPES.POLYGON:
      renderPolygon(ctx, ann, bars, barIndex, findIdx, toXY);
      break;
    case ANNOTATION_TYPES.TEXT_LABEL:
      renderTextLabel(ctx, ann, bars, findIdx, toXY);
      break;
    case ANNOTATION_TYPES.FIB_LINE:
      renderFibLine(ctx, ann, bars, findIdx, toXY);
      break;
    case ANNOTATION_TYPES.BUY_SIGNAL:
    case ANNOTATION_TYPES.SELL_SIGNAL:
    case ANNOTATION_TYPES.NEUTRAL_SIGNAL:
      renderSignalMarker(ctx, ann, bars, findIdx, toXY);
      break;
    // horizontal_line, support_zone, resistance_zone → handled by LWC priceLine
    default:
      break;
  }
}

/**
 * Draw a trend line between two points
 */
function renderTrendLine(ctx, ann, bars, findIdx, toXY) {
  const startTs = ann.data.start?.timestamp || ann.data.start;
  const endTs = ann.data.end?.timestamp || ann.data.end;

  const startIdx = findIdx(startTs);
  const endIdx = findIdx(endTs);

  if (startIdx < 0 || endIdx < 0) return;

  const startBar = bars[startIdx];
  const endBar = bars[endIdx];

  const p1 = toXY(startIdx, startBar.close);
  const p2 = toXY(endIdx, endBar.close);
  if (!p1 || !p2) return;

  const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.TREND_LINE];
  const color = ann.data.color || config.color;

  ctx.beginPath();
  ctx.moveTo(p1.x, p1.y);
  ctx.lineTo(p2.x, p2.y);
  ctx.strokeStyle = color;
  ctx.lineWidth = config.lineWidth || 2;
  ctx.setLineDash([]);
  ctx.stroke();

  // Label
  if (ann.data.label) {
    const midX = (p1.x + p2.x) / 2;
    const midY = (p1.y + p2.y) / 2;
    drawLabel(ctx, midX, midY - 10, ann.data.label, color);
  }
}

/**
 * Draw pattern markers — connected lines + point circles
 */
function renderPatternMark(ctx, ann, bars, barIndex, findIdx, toXY) {
  const points = ann.data.points || [];
  const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.PATTERN_MARK];
  // Use PATTERN_COLORS for pattern-specific coloring (normalize names)
  const patternType = normalizePatternName(ann.data.pattern || ann.data.patternType);
  const color = PATTERN_COLORS[patternType] || ann.data.color || config.color;

  const coords = [];
  points.forEach(point => {
    const ts = point.timestamp || point;
    const idx = findIdx(ts);
    if (idx >= 0) {
      const price = point.price || bars[idx].close;
      const xy = toXY(idx, price);
      if (xy) coords.push({ ...xy, price });
    }
  });

  if (coords.length >= 2) {
    // Draw connecting lines
    ctx.beginPath();
    ctx.moveTo(coords[0].x, coords[0].y);
    for (let i = 1; i < coords.length; i++) {
      ctx.lineTo(coords[i].x, coords[i].y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = config.lineWidth || 2;
    ctx.setLineDash([]);
    ctx.stroke();

    // Neckline
    if (ann.data.neckline && coords.length >= 2) {
      const necklinePrice = ann.data.neckline.price;
      if (typeof necklinePrice === 'number' && isFinite(necklinePrice)) {
        const startIdx = findIdx(points[0]?.timestamp || points[0]);
        const endIdx = findIdx(points[points.length - 1]?.timestamp || points[points.length - 1]);
        if (startIdx >= 0 && endIdx >= 0) {
          const p1 = toXY(startIdx, necklinePrice);
          const p2 = toXY(endIdx, necklinePrice);
          if (p1 && p2) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.stroke();
            ctx.setLineDash([]);
          }
        }
      }
    }

    // Stop loss line (dashed red)
    if (ann.data.stop_loss && typeof ann.data.stop_loss === 'number') {
      const firstIdx = findIdx(points[0]?.timestamp || points[0]);
      const lastIdx = findIdx(points[points.length - 1]?.timestamp || points[points.length - 1]);
      if (firstIdx >= 0 && lastIdx >= 0) {
        const p1 = toXY(firstIdx, ann.data.stop_loss);
        const p2 = toXY(lastIdx, ann.data.stop_loss);
        if (p1 && p2) {
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = '#fc8181';
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 3]);
          ctx.stroke();
          ctx.setLineDash([]);
          
          // Label
          drawLabel(ctx, p2.x + 40, p2.y, '止损', '#fc8181', 10);
        }
      }
    }

    // Target line (dashed green)
    if (ann.data.target && typeof ann.data.target === 'number') {
      const firstIdx = findIdx(points[0]?.timestamp || points[0]);
      const lastIdx = findIdx(points[points.length - 1]?.timestamp || points[points.length - 1]);
      if (firstIdx >= 0 && lastIdx >= 0) {
        const p1 = toXY(firstIdx, ann.data.target);
        const p2 = toXY(lastIdx, ann.data.target);
        if (p1 && p2) {
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = '#48bb78';
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 3]);
          ctx.stroke();
          ctx.setLineDash([]);
          
          // Label
          drawLabel(ctx, p2.x + 40, p2.y, '目标', '#48bb78', 10);
        }
      }
    }

    // Point markers
    coords.forEach((c, i) => {
      ctx.beginPath();
      ctx.arc(c.x, c.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    // Label
    const label = ann.data.label || ann.data.pattern;
    if (label) {
      const midIdx = Math.floor(coords.length / 2);
      drawLabel(ctx, coords[midIdx].x, coords[midIdx].y - 14, label, color);
    }
  } else if (coords.length === 1) {
    // Single point diamond
    drawDiamond(ctx, coords[0].x, coords[0].y, 6, color);
  }
}

/**
 * Draw a rectangle annotation
 */
function renderRectangle(ctx, ann, bars, findIdx, toXY) {
  const startIdx = findIdx(ann.data.start);
  const endIdx = findIdx(ann.data.end);
  if (startIdx < 0 || endIdx < 0) return;

  const p1 = toXY(startIdx, bars[startIdx].close);
  const p2 = toXY(endIdx, bars[endIdx].close);
  if (!p1 || !p2) return;

  const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.RECTANGLE];
  const color = ann.data.color || config.color;

  const x = Math.min(p1.x, p2.x);
  const y = Math.min(p1.y, p2.y);
  const w = Math.abs(p2.x - p1.x);
  const h = Math.abs(p2.y - p1.y);

  ctx.fillStyle = color + '20'; // 12% opacity
  ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = color;
  ctx.lineWidth = config.lineWidth || 2;
  ctx.setLineDash([]);
  ctx.strokeRect(x, y, w, h);
}

/**
 * Draw a polygon annotation
 */
function renderPolygon(ctx, ann, bars, barIndex, findIdx, toXY) {
  const points = ann.data.points || [];
  const coords = [];

  points.forEach(point => {
    const idx = findIdx(point);
    if (idx >= 0) {
      const xy = toXY(idx, bars[idx].close);
      if (xy) coords.push(xy);
    }
  });

  if (coords.length < 2) return;

  const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.POLYGON];
  const color = ann.data.color || config.color;

  ctx.beginPath();
  ctx.moveTo(coords[0].x, coords[0].y);
  for (let i = 1; i < coords.length; i++) {
    ctx.lineTo(coords[i].x, coords[i].y);
  }
  ctx.strokeStyle = color;
  ctx.lineWidth = config.lineWidth || 2;
  ctx.setLineDash([]);
  ctx.stroke();

  if (ann.data.label) {
    const mid = coords[Math.floor(coords.length / 2)];
    drawLabel(ctx, mid.x, mid.y - 10, ann.data.label, color);
  }
}

/**
 * Normalize pattern names from backend to match PATTERN_COLORS keys
 * e.g., cup_handle → cup_and_handle
 */
function normalizePatternName(pattern) {
  if (!pattern) return '';
  const nameMap = {
    cup_handle: 'cup_and_handle',
    head_and_shoulders: 'head_and_shoulders_bottom',
  };
  return nameMap[pattern] || pattern;
}

/**
 * Draw Fibonacci retracement lines between two price levels
 */
function renderFibLine(ctx, ann, bars, findIdx, toXY) {
  const startTs = ann.data.start?.timestamp || ann.data.start;
  const endTs = ann.data.end?.timestamp || ann.data.end;
  const startPrice = ann.data.start?.price || ann.data.startPrice;
  const endPrice = ann.data.end?.price || ann.data.endPrice;

  const startIdx = findIdx(startTs);
  const endIdx = findIdx(endTs);

  if (startIdx < 0 || endIdx < 0 || !startPrice || !endPrice) return;

  const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.FIB_LINE];
  const color = ann.data.color || config.color;

  // Standard Fibonacci levels
  const fibLevels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0];
  const priceDiff = endPrice - startPrice;

  fibLevels.forEach(level => {
    const price = startPrice + priceDiff * level;
    const p1 = toXY(startIdx, price);
    const p2 = toXY(endIdx, price);
    if (!p1 || !p2) return;

    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.strokeStyle = color;
    ctx.lineWidth = config.lineWidth || 1;
    ctx.setLineDash([2, 2]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Label
    const label = `${(level * 100).toFixed(1)}%`;
    drawLabel(ctx, p2.x + 30, p2.y, label, color, 10);
  });
}

/**
 * Draw text label annotation
 */
function renderTextLabel(ctx, ann, bars, findIdx, toXY) {
  const idx = findIdx(ann.timestamp);
  if (idx < 0) return;

  const price = ann.data.price || bars[idx].close;
  const xy = toXY(idx, price);
  if (!xy) return;

  const config = ANNOTATION_CONFIG[ANNOTATION_TYPES.TEXT_LABEL];
  const text = ann.data.text || '';
  const color = ann.data.color || config.color;

  drawLabel(ctx, xy.x, xy.y - 8, text, color, config.fontSize || 12);
}

/**
 * Draw signal markers (buy/sell/neutral) as small shapes on canvas
 * These complement the LWC markers for more visual customization
 */
function renderSignalMarker(ctx, ann, bars, findIdx, toXY) {
  const idx = findIdx(ann.timestamp);
  if (idx < 0) return;

  const bar = bars[idx];
  const price = bar.close;
  const xy = toXY(idx, price);
  if (!xy) return;

  // Signal markers are handled by LWC trade markers, skip here
  // unless we want extra visual emphasis
}

// ============================================================
// Drawing primitives
// ============================================================

function drawLabel(ctx, x, y, text, color, fontSize = 11) {
  if (!text) return;
  ctx.font = `${fontSize}px Inter, sans-serif`;
  const metrics = ctx.measureText(text);
  const pad = 4;
  const w = metrics.width + pad * 2;
  const h = fontSize + pad * 2;

  ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
  ctx.beginPath();
  roundRect(ctx, x - w / 2, y - h / 2, w, h, 3);
  ctx.fill();

  ctx.fillStyle = color;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, x, y);
}

function drawDiamond(ctx, x, y, size, color) {
  ctx.beginPath();
  ctx.moveTo(x, y - size);
  ctx.lineTo(x + size, y);
  ctx.lineTo(x, y + size);
  ctx.lineTo(x - size, y);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 1;
  ctx.stroke();
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
}

// ============================================================
// Overlay lifecycle
// ============================================================

/**
 * Setup auto-redraw: re-render overlay when chart scrolls/zooms
 */
export function setupOverlaySync(chart, candleSeries, canvas, ctx, data) {
  const redraw = () => {
    renderAnnotationOverlay(ctx, canvas, chart, candleSeries, data);
  };

  // Subscribe to visible time range changes
  chart.timeScale().subscribeVisibleLogicalRangeChange(redraw);

  // Also redraw on crosshair move (for consistent overlay)
  chart.subscribeCrosshairMove(redraw);

  // Resize observer
  const container = canvas.parentElement;
  if (container) {
    const ro = new ResizeObserver(() => {
      const newCtx = resizeOverlay(canvas, container);
      renderAnnotationOverlay(newCtx, canvas, chart, candleSeries, data);
    });
    ro.observe(container);
  }

  // Initial draw (deferred to next frame so chart layout is ready)
  requestAnimationFrame(redraw);
}

/**
 * Remove overlay canvas from DOM
 */
export function removeOverlay(chartContainer) {
  const existing = chartContainer.querySelector('.annotation-overlay');
  if (existing) existing.remove();
}

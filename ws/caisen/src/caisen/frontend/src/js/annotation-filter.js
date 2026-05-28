/**
 * Caisen Visualization - Annotation Filter Panel
 * 注解过滤面板 - 按形态类型过滤显示/隐藏注解
 */

import { appState } from './app-state.js';
import { PATTERN_COLORS } from './constants.js';
import { renderKLineChart } from './chart-renderer.js';

const PATTERN_LABELS = {
    w_bottom: 'W底',
    m_top: 'M头',
    head_and_shoulders_bottom: '头肩底',
    head_and_shoulders_top: '头肩顶',
    triangle: '三角形',
    flag: '旗形',
    rectangle: '矩形',
    rounding_bottom: '圆弧底',
    cup_handle: '杯柄',
    breakout_pullback: '过前高',
    breakdown_pullback: '破底翻',
    fake_breakout: '假突破',
};

/**
 * 从注解列表中提取所有唯一的 pattern 名称
 */
function extractPatternTypes(annotations) {
    const patterns = new Set();
    if (!annotations) return [];
    annotations.forEach(ann => {
        if (ann.type === 'pattern_mark' && ann.data?.pattern) {
            patterns.add(ann.data.pattern);
        }
    });
    return [...patterns].sort();
}

/**
 * 根据过滤状态过滤注解
 */
export function filterAnnotations(annotations) {
    const filterState = appState.getAnnotationFilter();
    if (!filterState || annotations === undefined) return annotations;
    if (!annotations) return annotations;

    return annotations.filter(ann => {
        if (ann.type === 'pattern_mark' && ann.data?.pattern) {
            return filterState.get(ann.data.pattern) !== false;
        }
        // 信号和线条注解
        const key = ann.type;
        return filterState.get(key) !== false;
    });
}

/**
 * 构建过滤面板 HTML 并插入 DOM
 */
export function buildFilterPanel(annotations) {
    const container = document.getElementById('annotation-filter-panel');
    if (!container) return;

    const patternTypes = extractPatternTypes(annotations);
    const signalTypes = ['buy_signal', 'sell_signal', 'neutral_signal'];
    const lineTypes = ['horizontal_line', 'trend_line', 'support_zone', 'resistance_zone'];

    // 初始化过滤状态（全部显示）
    const filterMap = new Map();
    patternTypes.forEach(p => filterMap.set(p, true));
    signalTypes.forEach(s => filterMap.set(s, true));
    lineTypes.forEach(l => filterMap.set(l, true));
    appState.setAnnotationFilter(filterMap);

    // 生成 HTML
    let html = '<div class="filter-header">';
    html += '<span class="filter-title">注解过滤</span>';
    html += '<div class="filter-actions">';
    html += '<button class="filter-btn" onclick="annotationFilterSelectAll()">全选</button>';
    html += '<button class="filter-btn" onclick="annotationFilterSelectNone()">全不选</button>';
    html += '<button class="filter-btn filter-collapse-btn" onclick="toggleAnnotationFilterPanel()">收起</button>';
    html += '</div></div>';
    html += '<div class="filter-body">';

    // 形态标注组
    if (patternTypes.length > 0) {
        html += '<div class="filter-group"><div class="filter-group-label">形态标注</div>';
        html += '<div class="filter-items">';
        patternTypes.forEach(pattern => {
            const color = PATTERN_COLORS[pattern] || '#9f7aea';
            const label = PATTERN_LABELS[pattern] || pattern;
            html += `<label class="filter-item">
                <input type="checkbox" checked data-filter-key="${pattern}" onchange="annotationFilterToggle('${pattern}', this.checked)">
                <span class="filter-color" style="background:${color}"></span>
                <span class="filter-label">${label}</span>
            </label>`;
        });
        html += '</div></div>';
    }

    // 信号标注组
    html += '<div class="filter-group"><div class="filter-group-label">信号标注</div>';
    html += '<div class="filter-items">';
    signalTypes.forEach(type => {
        const color = type === 'buy_signal' ? '#48bb78' : type === 'sell_signal' ? '#fc8181' : '#a0aec0';
        const label = type === 'buy_signal' ? '买入' : type === 'sell_signal' ? '卖出' : '中性';
        html += `<label class="filter-item">
            <input type="checkbox" checked data-filter-key="${type}" onchange="annotationFilterToggle('${type}', this.checked)">
            <span class="filter-color" style="background:${color}"></span>
            <span class="filter-label">${label}</span>
        </label>`;
    });
    html += '</div></div>';

    // 线条标注组
    html += '<div class="filter-group"><div class="filter-group-label">线条标注</div>';
    html += '<div class="filter-items">';
    const lineLabels = { horizontal_line: '水平线', trend_line: '趋势线', support_zone: '支撑线', resistance_zone: '阻力线' };
    lineTypes.forEach(type => {
        html += `<label class="filter-item">
            <input type="checkbox" checked data-filter-key="${type}" onchange="annotationFilterToggle('${type}', this.checked)">
            <span class="filter-color" style="background:#60a5fa"></span>
            <span class="filter-label">${lineLabels[type] || type}</span>
        </label>`;
    });
    html += '</div></div>';

    html += '</div>';
    container.innerHTML = html;
}

/**
 * 切换单个注解类型的显示/隐藏
 */
export function annotationFilterToggle(key, visible) {
    const filterMap = appState.getAnnotationFilter();
    if (!filterMap) return;
    filterMap.set(key, visible);
    appState.setAnnotationFilter(filterMap);
    renderKLineChart();
}

/**
 * 全选
 */
export function annotationFilterSelectAll() {
    const filterMap = appState.getAnnotationFilter();
    if (!filterMap) return;
    filterMap.forEach((_, key) => filterMap.set(key, true));
    appState.setAnnotationFilter(filterMap);
    // 更新 checkbox 状态
    document.querySelectorAll('#annotation-filter-panel input[type=checkbox]').forEach(cb => cb.checked = true);
    renderKLineChart();
}

/**
 * 全不选
 */
export function annotationFilterSelectNone() {
    const filterMap = appState.getAnnotationFilter();
    if (!filterMap) return;
    filterMap.forEach((_, key) => filterMap.set(key, false));
    appState.setAnnotationFilter(filterMap);
    document.querySelectorAll('#annotation-filter-panel input[type=checkbox]').forEach(cb => cb.checked = false);
    renderKLineChart();
}

/**
 * 展开/收起过滤面板
 */
export function toggleAnnotationFilterPanel() {
    const container = document.getElementById('annotation-filter-panel');
    if (!container) return;
    container.classList.toggle('collapsed');
}

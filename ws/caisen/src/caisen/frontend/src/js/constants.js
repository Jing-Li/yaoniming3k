/**
 * Caisen Visualization - Constants
 * 全局常量定义
 */

/**
 * Strategy display name map
 * 将技术性策略类名映射为形态化的英文代号
 *  - Phoenix : 凤凰，蔡森十二形态
 *  - Tide    : 潮汐，均线交叉
 *  - Eagle   : 鹰眼，突破
 *  - Storm   : 风暴，动量
 *  - Anchor  : 锚点，均值回归
 */
export const STRATEGY_DISPLAY_NAMES = {
    'CaiSenStrategy': 'Phoenix',
    'MACrossStrategy': 'Tide',
    'BreakoutStrategy': 'Eagle',
    'MomentumStrategy': 'Storm',
    'MeanReversionStrategy': 'Anchor',
};

/**
 * Get strategy display name, fall back to the raw name when unmapped.
 */
export function getStrategyDisplayName(rawName) {
    if (!rawName) return '';
    return STRATEGY_DISPLAY_NAMES[rawName] || rawName;
}

/**
 * Pattern colors map
 */
export const PATTERN_COLORS = {
    head_and_shoulders_bottom: '#9f7aea',
    head_and_shoulders_top: '#ed8936',
    w_bottom: '#48bb78',
    m_top: '#fc8181',
    triangle_ascending: '#60a5fa',
    triangle_descending: '#f6ad55',
    flag: '#f687b3',
    double_top: '#b794f4',
    double_bottom: '#68d391',
    cup_and_handle: '#38b2ac',
    arc_bottom: '#ed64a6',
    through_high: '#4299e1',
    breakdown_pullback: '#38b2ac',
    fake_breakout: '#e53e3e'
};

/**
 * Chart theme colors
 */
export const CHART_COLORS = {
    background: 'transparent',
    upColor: '#48bb78',
    downColor: '#fc8181',
    lineColor: '#4a5568',
    textColor: '#718096',
    borderColor: '#4a5568',
    tooltipBg: '#1a1f36',
    equityLine: '#60a5fa',
    drawdownLine: '#fc8181'
};

/**
 * Layout constants
 */
export const LAYOUT = {
    container: {
        maxWidth: '1600px',
        padding: '20px'
    },
    chart: {
        klineHeight: '500px',
        equityHeight: '200px'
    },
    grid: {
        gap: '16px',
        marginBottom: '20px'
    }
};

/**
 * Annotation type registry
 */
export const ANNOTATION_TYPES = {
    SIGNALS: ['buy_signal', 'sell_signal', 'neutral_signal'],
    LINES: ['horizontal_line', 'trend_line', 'support_zone', 'resistance_zone'],
    PATTERNS: ['pattern_mark'],
    MARKERS: ['volume_spike', 'text_label'],
    SHAPES: ['rectangle', 'polygon']
};

/**
 * Debug configuration — auto-disabled in production builds via Vite env.
 */
export const DEBUG_CONFIG = {
    enabled: import.meta.env.DEV === true,
    log: function(...args) {
        if (this.enabled) console.log('[DEBUG]', new Date().toISOString(), ...args);
    },
    error: function(...args) {
        if (this.enabled) console.error('[ERROR]', new Date().toISOString(), ...args);
    },
    warn: function(...args) {
        if (this.enabled) console.warn('[WARN]', new Date().toISOString(), ...args);
    }
};
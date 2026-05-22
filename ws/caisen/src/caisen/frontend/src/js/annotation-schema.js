/**
 * Caisen Annotation Schema
 * 标注类型单一真相源：定义所有标注类型及其渲染配置
 *
 * 与后端 core/annotation.py 的 AnnotationType 枚举保持同步
 */

export const ANNOTATION_TYPES = {
  // 点位标注
  BUY_SIGNAL: 'buy_signal',
  SELL_SIGNAL: 'sell_signal',
  NEUTRAL_SIGNAL: 'neutral_signal',

  // 线条标注
  HORIZONTAL_LINE: 'horizontal_line',
  TREND_LINE: 'trend_line',
  FIB_LINE: 'fib_line',

  // 区域标注
  SUPPORT_ZONE: 'support_zone',
  RESISTANCE_ZONE: 'resistance_zone',
  VOLUME_SPIKE: 'volume_spike',

  // 文本标注
  TEXT_LABEL: 'text_label',
  PATTERN_MARK: 'pattern_mark',

  // 图形标注
  RECTANGLE: 'rectangle',
  POLYGON: 'polygon',
};

/**
 * 标注渲染配置
 */
export const ANNOTATION_CONFIG = {
  [ANNOTATION_TYPES.BUY_SIGNAL]: {
    color: '#48bb78',
    defaultLabel: '买入',
    symbol: 'triangle',
    symbolSize: 14,
    symbolRotate: 0,
  },
  [ANNOTATION_TYPES.SELL_SIGNAL]: {
    color: '#fc8181',
    defaultLabel: '卖出',
    symbol: 'triangle',
    symbolSize: 14,
    symbolRotate: 180,
  },
  [ANNOTATION_TYPES.NEUTRAL_SIGNAL]: {
    color: '#a0aec0',
    defaultLabel: '中性',
    symbol: 'diamond',
    symbolSize: 12,
  },
  [ANNOTATION_TYPES.HORIZONTAL_LINE]: {
    color: '#60a5fa',
    lineStyle: 'dashed',
    lineWidth: 1,
  },
  [ANNOTATION_TYPES.TREND_LINE]: {
    color: '#ed8936',
    lineWidth: 2,
  },
  [ANNOTATION_TYPES.FIB_LINE]: {
    color: '#9f7aea',
    lineWidth: 1,
  },
  [ANNOTATION_TYPES.SUPPORT_ZONE]: {
    color: '#48bb78',
    lineStyle: 'dashed',
    lineWidth: 2,
    defaultLabel: '支撑',
  },
  [ANNOTATION_TYPES.RESISTANCE_ZONE]: {
    color: '#fc8181',
    lineStyle: 'dashed',
    lineWidth: 2,
    defaultLabel: '阻力',
  },
  [ANNOTATION_TYPES.VOLUME_SPIKE]: {
    color: '#f6ad55',
  },
  [ANNOTATION_TYPES.TEXT_LABEL]: {
    color: '#fff',
    fontSize: 12,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  [ANNOTATION_TYPES.PATTERN_MARK]: {
    color: '#9f7aea',
    lineWidth: 2,
  },
  [ANNOTATION_TYPES.RECTANGLE]: {
    color: '#f6ad55',
    lineWidth: 2,
  },
  [ANNOTATION_TYPES.POLYGON]: {
    color: '#b794f4',
    lineWidth: 2,
  },
};

/**
 * 获取所有支持的标注类型
 * @returns {string[]}
 */
export function getSupportedAnnotationTypes() {
  return Object.values(ANNOTATION_TYPES);
}

/**
 * 检查标注类型是否支持
 * @param {string} type
 * @returns {boolean}
 */
export function isAnnotationTypeSupported(type) {
  return Object.values(ANNOTATION_TYPES).includes(type);
}

/**
 * 获取标注渲染配置
 * @param {string} type
 * @returns {Object|undefined}
 */
export function getAnnotationConfig(type) {
  return ANNOTATION_CONFIG[type];
}
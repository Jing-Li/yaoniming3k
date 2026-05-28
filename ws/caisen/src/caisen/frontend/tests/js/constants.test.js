import { describe, it, expect } from 'vitest';
import {
  PATTERN_COLORS,
  CHART_COLORS,
  LAYOUT,
  ANNOTATION_TYPES,
  DEBUG_CONFIG,
  STRATEGY_DISPLAY_NAMES,
  getStrategyDisplayName,
} from '../../src/js/constants.js';

describe('constants', () => {
  it('should have pattern color definitions', () => {
    expect(PATTERN_COLORS).toBeDefined();
    expect(PATTERN_COLORS.w_bottom).toBeDefined();
    expect(PATTERN_COLORS.m_top).toBeDefined();
  });

  it('should have chart theme colors', () => {
    expect(CHART_COLORS).toBeDefined();
    expect(CHART_COLORS.upColor).toBeDefined();
    expect(CHART_COLORS.downColor).toBeDefined();
  });

  it('should have layout constants', () => {
    expect(LAYOUT).toBeDefined();
    expect(LAYOUT.container).toBeDefined();
    expect(LAYOUT.chart).toBeDefined();
  });

  it('should have annotation type registry', () => {
    expect(ANNOTATION_TYPES).toBeDefined();
    expect(ANNOTATION_TYPES.SIGNALS).toBeDefined();
    expect(ANNOTATION_TYPES.LINES).toBeDefined();
    expect(ANNOTATION_TYPES.PATTERNS).toBeDefined();
  });

  it('should have debug configuration', () => {
    expect(DEBUG_CONFIG).toBeDefined();
    expect(DEBUG_CONFIG.enabled).toBeDefined();
    expect(typeof DEBUG_CONFIG.log).toBe('function');
    expect(typeof DEBUG_CONFIG.error).toBe('function');
    expect(typeof DEBUG_CONFIG.warn).toBe('function');
  });
});

describe('strategy display names', () => {
  it('exposes the canonical strategy form map', () => {
    expect(STRATEGY_DISPLAY_NAMES.CaiSenStrategy).toBe('Phoenix');
    expect(STRATEGY_DISPLAY_NAMES.MACrossStrategy).toBe('Tide');
    expect(STRATEGY_DISPLAY_NAMES.BreakoutStrategy).toBe('Eagle');
    expect(STRATEGY_DISPLAY_NAMES.MomentumStrategy).toBe('Storm');
    expect(STRATEGY_DISPLAY_NAMES.MeanReversionStrategy).toBe('Anchor');
  });

  it('returns the mapped form name for known strategies', () => {
    expect(getStrategyDisplayName('CaiSenStrategy')).toBe('Phoenix');
    expect(getStrategyDisplayName('MACrossStrategy')).toBe('Tide');
  });

  it('falls back to the raw name for unknown strategies', () => {
    expect(getStrategyDisplayName('UnknownStrategy')).toBe('UnknownStrategy');
  });

  it('returns empty string for falsy input', () => {
    expect(getStrategyDisplayName('')).toBe('');
    expect(getStrategyDisplayName(undefined)).toBe('');
    expect(getStrategyDisplayName(null)).toBe('');
  });
});

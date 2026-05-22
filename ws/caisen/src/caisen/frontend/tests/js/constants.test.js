import { describe, it, expect } from 'vitest';
import { COLORS, CHART_CONFIG, API_ENDPOINTS } from '../../src/js/constants.js';

describe('constants', () => {
  it('should have color definitions', () => {
    expect(COLORS).toBeDefined();
    expect(COLORS.up).toBeDefined();
    expect(COLORS.down).toBeDefined();
  });

  it('should have chart config', () => {
    expect(CHART_CONFIG).toBeDefined();
    expect(CHART_CONFIG.defaultHeight).toBeDefined();
  });

  it('should have API endpoints', () => {
    expect(API_ENDPOINTS).toBeDefined();
    expect(API_ENDPOINTS.runs).toBeDefined();
  });
});

import { describe, it, expect } from 'vitest';
import { formatValue, formatTimestamp, calculateAnnualReturn, isFiniteNum, isValidCoordPoint, isValidCoord, filterValidMarkPoints, filterValidMarkLines, findBarByTimestamp, applyDateFilterToData } from '../../src/js/utils.js';
import { PATTERN_COLORS } from '../../src/js/constants.js';

describe('utils', () => {
  describe('formatValue', () => {
    it('should format percent type', () => {
      expect(formatValue(0.1234, 'percent')).toBe('12.34%');
    });

    it('should format negative percent', () => {
      expect(formatValue(-0.05, 'percent')).toBe('-5.00%');
    });

    it('should format currency type', () => {
      const result = formatValue(1234567, 'currency');
      expect(result).toContain('1,234,567');
    });

    it('should format ratio type', () => {
      expect(formatValue(2.5, 'ratio')).toBe('2.50');
    });

    it('should return dash for null/undefined/NaN', () => {
      expect(formatValue(null)).toBe('-');
      expect(formatValue(undefined)).toBe('-');
      expect(formatValue(NaN)).toBe('-');
    });

    it('should handle infinity in ratio', () => {
      expect(formatValue(Infinity, 'ratio')).toBe('∞');
    });
  });

  describe('formatTimestamp', () => {
    it('should format ISO string', () => {
      const result = formatTimestamp('2024-01-15T10:30:00');
      expect(result).toContain('2024');
    });

    it('should format Date object', () => {
      const date = new Date('2024-01-15T10:30:00');
      const result = formatTimestamp(date);
      expect(result).toContain('2024');
    });
  });

  describe('calculateAnnualReturn', () => {
    it('should return 0 for insufficient data', () => {
      expect(calculateAnnualReturn(null)).toBe(0);
      expect(calculateAnnualReturn({ equity_curve: [] })).toBe(0);
      expect(calculateAnnualReturn({ equity_curve: [{ equity: 100 }] })).toBe(0);
    });

    it('should calculate annual return from equity curve', () => {
      const data = { equity_curve: [{ equity: 100 }, { equity: 200 }], meta: { freq: '1d' } };
      const result = calculateAnnualReturn(data);
      expect(result).toBeGreaterThan(0);
    });
  });

  describe('isFiniteNum', () => {
    it('should return true for finite numbers', () => {
      expect(isFiniteNum(42)).toBe(true);
      expect(isFiniteNum(0)).toBe(true);
    });

    it('should return false for non-finite or non-numbers', () => {
      expect(isFiniteNum(Infinity)).toBe(false);
      expect(isFiniteNum(NaN)).toBe(false);
      expect(isFiniteNum('42')).toBe(false);
      expect(isFiniteNum(null)).toBe(false);
    });
  });

  describe('isValidCoordPoint', () => {
    it('should validate coordinate array with 2+ elements', () => {
      expect(isValidCoordPoint([1, 2])).toBe(true);
      expect(isValidCoordPoint([1, 2, 3])).toBe(true);
    });

    it('should reject invalid coordinate', () => {
      expect(isValidCoordPoint(null)).toBeFalsy();
      expect(isValidCoordPoint([1])).toBe(false);
      expect(isValidCoordPoint([NaN, 2])).toBe(false);
    });
  });

  describe('isValidCoord', () => {
    it('should validate coordinate', () => {
      expect(isValidCoord([1, 2])).toBe(true);
    });

    it('should reject invalid coordinate', () => {
      expect(isValidCoord(null)).toBeFalsy();
      expect(isValidCoord([NaN, 2])).toBe(false);
    });
  });

  describe('filterValidMarkPoints', () => {
    it('should filter out invalid markPoints', () => {
      const points = [
        { coord: [1, 2] },
        { coord: [NaN, 2] },
        null
      ];
      expect(filterValidMarkPoints(points)).toHaveLength(1);
    });
  });

  describe('filterValidMarkLines', () => {
    it('should keep yAxis format lines', () => {
      const lines = [{ yAxis: 100 }, { yAxis: NaN }, null];
      expect(filterValidMarkLines(lines)).toHaveLength(1);
    });

    it('should keep coords format lines with 2+ valid points', () => {
      const lines = [{ coords: [[1, 2], [3, 4]] }, { coords: [[1]] }];
      expect(filterValidMarkLines(lines)).toHaveLength(1);
    });
  });

  describe('PATTERN_COLORS', () => {
    it('should have color for known patterns', () => {
      expect(PATTERN_COLORS.w_bottom).toBeDefined();
      expect(PATTERN_COLORS.m_top).toBeDefined();
    });
  });

  describe('findBarByTimestamp', () => {
    it('should find bar by exact timestamp', () => {
      const bars = [{ timestamp: '2024-01-15' }, { timestamp: '2024-01-16' }];
      expect(findBarByTimestamp(bars, '2024-01-15').timestamp).toBe('2024-01-15');
    });

    it('should return null for empty timestamp', () => {
      expect(findBarByTimestamp([], null)).toBeNull();
    });
  });

  describe('applyDateFilterToData', () => {
    it('should filter data by date range', () => {
      const data = {
        bars: [{ timestamp: '2024-01-10' }, { timestamp: '2024-01-20' }],
        equity_curve: [{ timestamp: '2024-01-10', equity: 100 }, { timestamp: '2024-01-20', equity: 200 }],
        trades: [{ timestamp: '2024-01-10' }],
        annotations: [{ timestamp: '2024-01-10' }]
      };
      const result = applyDateFilterToData(data, '2024-01-15', '2024-01-25');
      expect(result.bars).toHaveLength(1);
      expect(result.bars[0].timestamp).toBe('2024-01-20');
    });
  });
});

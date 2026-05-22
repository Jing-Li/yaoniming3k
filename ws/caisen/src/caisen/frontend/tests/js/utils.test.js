import { describe, it, expect } from 'vitest';
import { formatDate, formatNumber, formatPercent } from '../../src/js/utils.js';

describe('utils', () => {
  describe('formatDate', () => {
    it('should format date string', () => {
      expect(formatDate('2024-01-15')).toBe('2024-01-15');
    });

    it('should handle Date object', () => {
      const date = new Date('2024-01-15');
      expect(formatDate(date)).toContain('2024');
    });
  });

  describe('formatNumber', () => {
    it('should format number with commas', () => {
      expect(formatNumber(1234567)).toBe('1,234,567');
    });

    it('should format decimal numbers', () => {
      expect(formatNumber(1234.56)).toBe('1,234.56');
    });
  });

  describe('formatPercent', () => {
    it('should format as percentage', () => {
      expect(formatPercent(0.1234)).toBe('12.34%');
    });

    it('should handle negative values', () => {
      expect(formatPercent(-0.05)).toBe('-5.00%');
    });
  });
});

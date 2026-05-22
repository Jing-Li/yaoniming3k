/**
 * Caisen Visualization - Utils Tests
 */

import { describe, it, expect } from 'vitest';
import {
    formatValue,
    formatTimestamp,
    calculateAnnualReturn,
    isFiniteNum,
    isValidCoordPoint,
    isValidCoord,
    filterValidMarkPoints,
    filterValidMarkLines,
    PATTERN_COLORS,
    findBarByTimestamp,
    applyDateFilterToData
} from '../../src/caisen/visualization/js/utils.js';

describe('utils.js', () => {
    describe('formatValue', () => {
        it('should return "-" for null/undefined/NaN', () => {
            expect(formatValue(null)).toBe('-');
            expect(formatValue(undefined)).toBe('-');
            expect(formatValue(NaN)).toBe('-');
        });

        it('should format percent type correctly', () => {
            expect(formatValue(0.1234, 'percent')).toBe('12.34%');
            expect(formatValue(-0.05, 'percent')).toBe('-5.00%');
            expect(formatValue(1.0, 'percent')).toBe('100.00%');
        });

        it('should format ratio type correctly', () => {
            expect(formatValue(1.5, 'ratio')).toBe('1.50');
            expect(formatValue(Infinity, 'ratio')).toBe('∞');
            expect(formatValue(-0.5, 'ratio')).toBe('-0.50');
        });

        it('should format currency type correctly', () => {
            expect(formatValue(1234.56, 'currency')).toContain('1,234.56');
        });
    });

    describe('formatTimestamp', () => {
        it('should format timestamp to locale string', () => {
            const result = formatTimestamp('2024-01-15T10:30:00');
            expect(result).toContain('2024');
            expect(result).toContain('1');
            expect(result).toContain('15');
        });

        it('should handle Date objects', () => {
            const date = new Date('2024-06-20T14:00:00');
            const result = formatTimestamp(date);
            expect(result).toContain('2024');
        });
    });

    describe('isFiniteNum', () => {
        it('should return true for finite numbers', () => {
            expect(isFiniteNum(0)).toBe(true);
            expect(isFiniteNum(1)).toBe(true);
            expect(isFiniteNum(-1)).toBe(true);
            expect(isFiniteNum(1.5)).toBe(true);
        });

        it('should return false for non-finite values', () => {
            expect(isFiniteNum(Infinity)).toBe(false);
            expect(isFiniteNum(-Infinity)).toBe(false);
            expect(isFiniteNum(NaN)).toBe(false);
            expect(isFiniteNum('1')).toBe(false);
            expect(isFiniteNum(null)).toBe(false);
            expect(isFiniteNum(undefined)).toBe(false);
        });
    });

    describe('isValidCoordPoint', () => {
        it('should validate coordinate points correctly', () => {
            expect(isValidCoordPoint([1, 2])).toBe(true);
            expect(isValidCoordPoint([0, 0])).toBe(true);
            expect(isValidCoordPoint([-1, 100])).toBe(true);
        });

        it('should reject invalid coordinate points', () => {
            expect(isValidCoordPoint([Infinity, 1])).toBe(false);
            expect(isValidCoordPoint([1, NaN])).toBe(false);
            expect(isValidCoordPoint(null)).toBeFalsy();
            expect(isValidCoordPoint([1])).toBe(false); // Only one element
            expect(isValidCoordPoint([])).toBe(false);
        });
    });

    describe('isValidCoord', () => {
        it('should validate coordinates correctly', () => {
            expect(isValidCoord([1, 2])).toBe(true);
            expect(isValidCoord([0, 0])).toBe(true);
        });

        it('should reject invalid coordinates', () => {
            expect(isValidCoord([Infinity, 1])).toBe(false);
            expect(isValidCoord(null)).toBeFalsy();
        });
    });

    describe('filterValidMarkPoints', () => {
        it('should filter markPoints with valid coords', () => {
            const markPoints = [
                { coord: [0, 100] },
                { coord: [1, NaN] }, // Invalid
                { coord: null }, // Invalid
                { coord: [2, 200] },
                {} // Invalid
            ];
            const result = filterValidMarkPoints(markPoints);
            expect(result.length).toBe(2);
            expect(result[0].coord).toEqual([0, 100]);
            expect(result[1].coord).toEqual([2, 200]);
        });

        it('should return empty array for empty input', () => {
            expect(filterValidMarkPoints([])).toEqual([]);
        });
    });

    describe('filterValidMarkLines', () => {
        it('should filter yAxis format markLines', () => {
            const markLines = [
                { yAxis: 100 },
                { yAxis: NaN }, // Invalid
                { yAxis: 200 }
            ];
            const result = filterValidMarkLines(markLines);
            expect(result.length).toBe(2);
        });

        it('should filter coords format markLines', () => {
            const markLines = [
                { coords: [[0, 100], [1, 200]] },
                { coords: [[0, 100]] }, // Too few points
                { coords: [[0, 100], [1, 200], [2, 300]] }
            ];
            const result = filterValidMarkLines(markLines);
            expect(result.length).toBe(2);
        });

        it('should reject mixed invalid markLines', () => {
            const markLines = [
                { yAxis: NaN },
                { coords: [[0, 100]] },
                { other: 'field' }
            ];
            const result = filterValidMarkLines(markLines);
            expect(result.length).toBe(0);
        });
    });

    describe('PATTERN_COLORS', () => {
        it('should contain all expected pattern colors', () => {
            expect(PATTERN_COLORS.head_and_shoulders_bottom).toBe('#9f7aea');
            expect(PATTERN_COLORS.w_bottom).toBe('#48bb78');
            expect(PATTERN_COLORS.triangle_ascending).toBe('#60a5fa');
        });
    });

    describe('findBarByTimestamp', () => {
        const bars = [
            { timestamp: '2024-01-01T00:00:00', close: 100 },
            { timestamp: '2024-01-02T00:00:00', close: 105 },
            { timestamp: '2024-01-03T00:00:00', close: 110 }
        ];

        it('should find bar by exact timestamp', () => {
            const result = findBarByTimestamp(bars, '2024-01-02T00:00:00');
            expect(result).toEqual(bars[1]);
        });

        it('should find bar by approximate timestamp (within 1 hour)', () => {
            const result = findBarByTimestamp(bars, '2024-01-02T00:30:00');
            expect(result).toEqual(bars[1]);
        });

        it('should return null for non-existent timestamp', () => {
            const result = findBarByTimestamp(bars, '2024-01-10T00:00:00');
            expect(result).toBeFalsy();
        });

        it('should return null for empty timestamp', () => {
            const result = findBarByTimestamp(bars, null);
            expect(result).toBeNull();
        });
    });

    describe('calculateAnnualReturn', () => {
        it('should calculate annual return correctly', () => {
            const rawData = {
                equity_curve: [
                    { equity: 10000 },
                    { equity: 11000 },
                    { equity: 12100 }
                ],
                meta: { freq: '1d' }
            };
            // 4 data points for daily data = 4/250 years ≈ 0.016 years
            // (12100/10000)^(1/0.016) - 1 would be huge
            // Let's test with a simpler case
            const rawData2 = {
                equity_curve: [
                    { equity: 10000 },
                    { equity: 20000 }
                ],
                meta: { freq: '1d' }
            };
            const result = calculateAnnualReturn(rawData2);
            // 2 points = 2/250 years, (20000/10000)^(1/(2/250)) - 1
            expect(result).toBeGreaterThan(0);
        });

        it('should return 0 for insufficient data', () => {
            expect(calculateAnnualReturn(null)).toBe(0);
            expect(calculateAnnualReturn({ equity_curve: [] })).toBe(0);
            expect(calculateAnnualReturn({ equity_curve: [{ equity: 100 }] })).toBe(0);
        });

        it('should return 0 for invalid initial equity', () => {
            const rawData = {
                equity_curve: [
                    { equity: 0 },
                    { equity: 100 }
                ]
            };
            expect(calculateAnnualReturn(rawData)).toBe(0);
        });
    });

    describe('applyDateFilterToData', () => {
        const sampleData = {
            bars: [
                { timestamp: '2024-01-01T00:00:00', close: 100 },
                { timestamp: '2024-02-01T00:00:00', close: 105 },
                { timestamp: '2024-03-01T00:00:00', close: 110 },
                { timestamp: '2024-04-01T00:00:00', close: 115 }
            ],
            equity_curve: [
                { timestamp: '2024-01-01T00:00:00', equity: 10000 },
                { timestamp: '2024-02-01T00:00:00', equity: 10500 },
                { timestamp: '2024-03-01T00:00:00', equity: 11000 },
                { timestamp: '2024-04-01T00:00:00', equity: 11500 }
            ],
            trades: [
                { timestamp: '2024-01-01T00:00:00', side: 'BUY' },
                { timestamp: '2024-03-01T00:00:00', side: 'SELL' }
            ],
            annotations: [
                { timestamp: '2024-02-01T00:00:00', type: 'buy_signal' },
                { timestamp: '2024-04-01T00:00:00', type: 'sell_signal' }
            ]
        };

        it('should filter by start date', () => {
            const result = applyDateFilterToData(sampleData, '2024-02-15', null);
            // After 2024-02-15: bars from 03-01 and 04-01 (2 bars)
            expect(result.bars.length).toBe(2);
            expect(result.equity_curve.length).toBe(2);
            expect(result.trades.length).toBe(1);
            expect(result.annotations.length).toBe(1);
        });

        it('should filter by end date', () => {
            const result = applyDateFilterToData(sampleData, null, '2024-02-15');
            expect(result.bars.length).toBe(2);
            expect(result.equity_curve.length).toBe(2);
            expect(result.trades.length).toBe(1);
            expect(result.annotations.length).toBe(1);
        });

        it('should filter by both dates', () => {
            const result = applyDateFilterToData(sampleData, '2024-02-01', '2024-03-15');
            // From 02-01 to 03-15: only 03-01 (01-01 is before start, 04-01 is after end)
            expect(result.bars.length).toBe(1);
        });

        it('should not modify original data', () => {
            const originalLength = sampleData.bars.length;
            applyDateFilterToData(sampleData, '2024-02-01', null);
            expect(sampleData.bars.length).toBe(originalLength);
        });
    });
});
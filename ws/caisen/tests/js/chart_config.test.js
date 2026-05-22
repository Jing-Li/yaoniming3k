/**
 * Caisen Visualization - Chart Config Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
    buildKLineOption,
    buildEquityOption,
    buildTooltipContent,
    processAnnotations,
    processTrades,
    getAnnotationRenderer
} from '../../src/caisen/visualization/js/chart-config.js';

describe('chart-config.js', () => {
    // Sample data for testing
    const sampleBars = [
        { timestamp: '2024-01-01T00:00:00', open: 100, close: 105, low: 99, high: 107, volume: 1000 },
        { timestamp: '2024-01-02T00:00:00', open: 105, close: 110, low: 104, high: 112, volume: 1200 },
        { timestamp: '2024-01-03T00:00:00', open: 110, close: 108, low: 106, high: 113, volume: 900 },
        { timestamp: '2024-01-04T00:00:00', open: 108, close: 115, low: 107, high: 116, volume: 1100 },
        { timestamp: '2024-01-05T00:00:00', open: 115, close: 120, low: 114, high: 122, volume: 1300 }
    ];

    const sampleEquity = [
        { timestamp: '2024-01-01T00:00:00', equity: 10000 },
        { timestamp: '2024-01-02T00:00:00', equity: 10500 },
        { timestamp: '2024-01-03T00:00:00', equity: 11000 },
        { timestamp: '2024-01-04T00:00:00', equity: 10800 },
        { timestamp: '2024-01-05T00:00:00', equity: 11500 }
    ];

    const createSampleData = (options = {}) => ({
        bars: sampleBars,
        equity_curve: sampleEquity,
        trades: options.trades || [
            { timestamp: '2024-01-02T00:00:00', side: 'BUY', price: 110, quantity: 100, commission: 10 }
        ],
        annotations: options.annotations || [
            { type: 'buy_signal', timestamp: '2024-01-02T00:00:00', data: { label: '买入' } }
        ],
        meta: { symbol: 'AAPL', freq: '1d', strategy_name: 'TestStrategy' }
    });

    describe('buildKLineOption', () => {
        it('should return null for empty data', () => {
            expect(buildKLineOption({ data: null, isZoomEnabled: false })).toBeNull();
            expect(buildKLineOption({ data: { bars: [] }, isZoomEnabled: false })).toBeNull();
        });

        it('should build valid K-Line chart option', () => {
            const data = createSampleData();
            const option = buildKLineOption({ data, isZoomEnabled: false });

            expect(option).not.toBeNull();
            expect(option.series).toHaveLength(2);
            expect(option.series[0].type).toBe('candlestick');
            expect(option.series[1].type).toBe('bar');
        });

        it('should include dataZoom when enabled', () => {
            const data = createSampleData();
            const option = buildKLineOption({ data, isZoomEnabled: true });

            expect(option.dataZoom).toHaveLength(2);
            expect(option.dataZoom[0].type).toBe('inside');
            expect(option.dataZoom[1].type).toBe('slider');
        });

        it('should not include slider zoom when disabled', () => {
            const data = createSampleData();
            const option = buildKLineOption({ data, isZoomEnabled: false });

            expect(option.dataZoom).toHaveLength(1);
            expect(option.dataZoom[0].type).toBe('inside');
        });

        it('should include grid configuration', () => {
            const data = createSampleData();
            const option = buildKLineOption({ data, isZoomEnabled: false });

            expect(option.grid).toHaveLength(2);
            expect(option.grid[0].height).toBe('55%');
            expect(option.grid[1].height).toBe('15%');
        });

        it('should include xAxis and yAxis', () => {
            const data = createSampleData();
            const option = buildKLineOption({ data, isZoomEnabled: false });

            expect(option.xAxis).toHaveLength(2);
            expect(option.yAxis).toHaveLength(2);
        });

        it('should process annotations into markPoints/markLines', () => {
            const annotations = [
                { type: 'buy_signal', timestamp: '2024-01-02T00:00:00', data: {} },
                { type: 'horizontal_line', timestamp: '2024-01-01T00:00:00', data: { price: 110 } }
            ];
            const data = createSampleData({ annotations });
            const option = buildKLineOption({ data, isZoomEnabled: false });

            expect(option.series[0].markPoint.data.length).toBeGreaterThan(0);
            expect(option.series[0].markLine.data.length).toBeGreaterThan(0);
        });

        it('should include tooltip configuration', () => {
            const data = createSampleData();
            const option = buildKLineOption({ data, isZoomEnabled: false });

            expect(option.tooltip).toBeDefined();
            expect(option.tooltip.trigger).toBe('axis');
            expect(option.tooltip.backgroundColor).toBe('#1a1f36');
        });
    });

    describe('buildEquityOption', () => {
        it('should return null for empty data', () => {
            expect(buildEquityOption({ data: null })).toBeNull();
            expect(buildEquityOption({ data: { equity_curve: [] } })).toBeNull();
        });

        it('should build valid equity chart option', () => {
            const data = createSampleData();
            const option = buildEquityOption({ data });

            expect(option).not.toBeNull();
            expect(option.series).toHaveLength(2);
            expect(option.series[0].type).toBe('line');
            expect(option.series[0].name).toBe('净值');
            expect(option.series[1].name).toBe('回撤');
        });

        it('should calculate drawdown correctly', () => {
            const data = createSampleData();
            const option = buildEquityOption({ data });

            // Check drawdown series (second series)
            const drawdownSeries = option.series[1];
            expect(drawdownSeries.type).toBe('line');
            expect(drawdownSeries.yAxisIndex).toBe(1);
        });

        it('should include dual yAxis for equity and drawdown', () => {
            const data = createSampleData();
            const option = buildEquityOption({ data });

            expect(option.yAxis).toHaveLength(2);
            expect(option.yAxis[0].position).toBe('left');
            expect(option.yAxis[1].position).toBe('right');
        });

        it('should include areaStyle for equity line', () => {
            const data = createSampleData();
            const option = buildEquityOption({ data });

            expect(option.series[0].areaStyle).toBeDefined();
            expect(option.series[0].smooth).toBe(true);
        });

        it('should include legend configuration', () => {
            const data = createSampleData();
            const option = buildEquityOption({ data });

            expect(option.legend).toBeDefined();
            expect(option.legend.data).toContain('净值');
            expect(option.legend.data).toContain('回撤');
        });
    });

    describe('buildTooltipContent', () => {
        it('should build tooltip for candlestick data', () => {
            const data = createSampleData();
            const params = [
                {
                    seriesType: 'candlestick',
                    axisValue: '2024-01-02',
                    data: [105, 110, 104, 112]
                }
            ];

            const result = buildTooltipContent(params, data);
            expect(result).toContain('开盘');
            expect(result).toContain('110');
        });

        it('should include volume data', () => {
            const data = createSampleData();
            const params = [
                { seriesType: 'bar', data: 1200 }
            ];

            const result = buildTooltipContent(params, data);
            expect(result).toContain('成交量');
        });

        it('should return empty string for empty params', () => {
            const data = createSampleData();
            expect(buildTooltipContent([], data)).toBe('');
            expect(buildTooltipContent(null, data)).toBe('');
        });
    });

    describe('processAnnotations', () => {
        it('should return empty arrays for null annotations', () => {
            const result = processAnnotations(null, sampleBars);
            expect(result.markPoints).toEqual([]);
            expect(result.markLines).toEqual([]);
        });

        it('should process multiple annotation types', () => {
            const annotations = [
                { type: 'buy_signal', timestamp: '2024-01-02T00:00:00', data: {} },
                { type: 'sell_signal', timestamp: '2024-01-04T00:00:00', data: {} }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markPoints.length).toBe(2);
        });
    });

    describe('processTrades', () => {
        it('should convert trades to markPoints', () => {
            const trades = [
                { timestamp: '2024-01-02T00:00:00', side: 'BUY' },
                { timestamp: '2024-01-04T00:00:00', side: 'SELL' }
            ];
            const result = processTrades(trades, sampleBars);
            expect(result.length).toBe(2);
            expect(result[0].symbol).toBe('circle');
        });

        it('should return empty array for null trades', () => {
            expect(processTrades(null, sampleBars)).toEqual([]);
        });

        it('should use correct colors for BUY/SELL', () => {
            const trades = [
                { timestamp: '2024-01-02T00:00:00', side: 'BUY' },
                { timestamp: '2024-01-03T00:00:00', side: 'SELL' }
            ];
            const result = processTrades(trades, sampleBars);
            expect(result[0].itemStyle.color).toBe('#48bb78');
            expect(result[1].itemStyle.color).toBe('#fc8181');
        });
    });

    describe('getAnnotationRenderer', () => {
        it('should return renderer function for each type', () => {
            const types = [
                'buy_signal', 'sell_signal', 'neutral_signal',
                'horizontal_line', 'trend_line', 'pattern_mark',
                'support_zone', 'resistance_zone', 'text_label'
            ];

            types.forEach(type => {
                expect(getAnnotationRenderer(type)).toBeDefined();
                expect(typeof getAnnotationRenderer(type)).toBe('function');
            });
        });

        it('should return null for unknown types', () => {
            expect(getAnnotationRenderer('unknown')).toBeNull();
        });
    });

    describe('Integration Tests', () => {
        it('should build complete chart options with annotations and trades', () => {
            const data = createSampleData({
                annotations: [
                    { type: 'buy_signal', timestamp: '2024-01-02T00:00:00', data: {} },
                    { type: 'sell_signal', timestamp: '2024-01-04T00:00:00', data: {} },
                    { type: 'horizontal_line', timestamp: '2024-01-01T00:00:00', data: { price: 115 } }
                ],
                trades: [
                    { timestamp: '2024-01-02T00:00:00', side: 'BUY' },
                    { timestamp: '2024-01-04T00:00:00', side: 'SELL' }
                ]
            });

            const klineOption = buildKLineOption({ data, isZoomEnabled: false });
            const equityOption = buildEquityOption({ data });

            expect(klineOption).not.toBeNull();
            expect(equityOption).not.toBeNull();
            expect(klineOption.series[0].markPoint.data.length).toBe(4); // 2 annotations + 2 trades
            expect(klineOption.series[0].markLine.data.length).toBe(1);
        });
    });
});
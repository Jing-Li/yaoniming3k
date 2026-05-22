/**
 * Caisen Visualization - Annotation Renderer Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
    processAnnotations,
    getAnnotationRenderer,
    getSupportedAnnotationTypes,
    renderBuySignal,
    renderSellSignal,
    renderNeutralSignal,
    renderHorizontalLine,
    renderTrendLine,
    renderPatternMark,
    renderSupportZone,
    renderResistanceZone,
    renderVolumeSpike,
    renderTextLabel,
    renderRectangle,
    renderPolygon
} from '../../src/caisen/visualization/js/annotation-renderer.js';

describe('annotation-renderer.js', () => {
    // Sample bars data for testing
    const sampleBars = [
        { timestamp: '2024-01-01T00:00:00', open: 100, close: 105, low: 99, high: 107, volume: 1000 },
        { timestamp: '2024-01-02T00:00:00', open: 105, close: 110, low: 104, high: 112, volume: 1200 },
        { timestamp: '2024-01-03T00:00:00', open: 110, close: 108, low: 106, high: 113, volume: 900 },
        { timestamp: '2024-01-04T00:00:00', open: 108, close: 115, low: 107, high: 116, volume: 1100 },
        { timestamp: '2024-01-05T00:00:00', open: 115, close: 120, low: 114, high: 122, volume: 1300 }
    ];

    describe('getSupportedAnnotationTypes', () => {
        it('should return all supported annotation types', () => {
            const types = getSupportedAnnotationTypes();
            expect(types).toContain('buy_signal');
            expect(types).toContain('sell_signal');
            expect(types).toContain('horizontal_line');
            expect(types).toContain('trend_line');
            expect(types).toContain('pattern_mark');
            expect(types).toContain('support_zone');
            expect(types).toContain('resistance_zone');
            expect(types.length).toBe(12);
        });
    });

    describe('getAnnotationRenderer', () => {
        it('should return renderer for valid types', () => {
            expect(getAnnotationRenderer('buy_signal')).toBe(renderBuySignal);
            expect(getAnnotationRenderer('sell_signal')).toBe(renderSellSignal);
            expect(getAnnotationRenderer('pattern_mark')).toBe(renderPatternMark);
        });

        it('should return null for invalid types', () => {
            expect(getAnnotationRenderer('invalid_type')).toBeNull();
            expect(getAnnotationRenderer('')).toBeNull();
            expect(getAnnotationRenderer(null)).toBeNull();
        });
    });

    describe('processAnnotations', () => {
        it('should process empty annotations', () => {
            const result = processAnnotations([], sampleBars);
            expect(result.markPoints).toEqual([]);
            expect(result.markLines).toEqual([]);
        });

        it('should process null annotations', () => {
            const result = processAnnotations(null, sampleBars);
            expect(result.markPoints).toEqual([]);
            expect(result.markLines).toEqual([]);
        });

        it('should process buy_signal annotation', () => {
            const annotations = [
                { type: 'buy_signal', timestamp: '2024-01-02T00:00:00', data: { label: '买入信号' } }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markPoints.length).toBe(1);
            expect(result.markPoints[0].value).toBe('买入信号');
            expect(result.markPoints[0].symbol).toBe('triangle');
        });

        it('should process sell_signal annotation', () => {
            const annotations = [
                { type: 'sell_signal', timestamp: '2024-01-03T00:00:00', data: { label: '卖出信号' } }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markPoints.length).toBe(1);
            expect(result.markPoints[0].value).toBe('卖出信号');
            expect(result.markPoints[0].symbol).toBe('triangle');
            expect(result.markPoints[0].symbolRotate).toBe(180);
        });

        it('should process neutral_signal annotation', () => {
            const annotations = [
                { type: 'neutral_signal', timestamp: '2024-01-02T00:00:00', data: {} }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markPoints.length).toBe(1);
            expect(result.markPoints[0].symbol).toBe('diamond');
        });

        it('should process horizontal_line annotation', () => {
            const annotations = [
                { type: 'horizontal_line', timestamp: '2024-01-01T00:00:00', data: { price: 105, label: '阻力线' } }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markLines.length).toBe(1);
            expect(result.markLines[0].yAxis).toBe(105);
            expect(result.markLines[0].label.formatter).toBe('阻力线');
        });

        it('should process support_zone annotation', () => {
            const annotations = [
                { type: 'support_zone', timestamp: '2024-01-01T00:00:00', data: { price: 100 } }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markLines.length).toBe(1);
            expect(result.markLines[0].yAxis).toBe(100);
            expect(result.markLines[0].lineStyle.color).toBe('#48bb78');
        });

        it('should process resistance_zone annotation', () => {
            const annotations = [
                { type: 'resistance_zone', timestamp: '2024-01-01T00:00:00', data: { price: 120 } }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markLines.length).toBe(1);
            expect(result.markLines[0].yAxis).toBe(120);
            expect(result.markLines[0].lineStyle.color).toBe('#fc8181');
        });

        it('should process trend_line annotation', () => {
            const annotations = [
                {
                    type: 'trend_line',
                    timestamp: '2024-01-01T00:00:00',
                    data: {
                        start: '2024-01-01T00:00:00',
                        end: '2024-01-03T00:00:00',
                        label: '趋势线'
                    }
                }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markLines.length).toBe(1);
            expect(result.markLines[0].coords.length).toBe(2);
        });

        it('should process pattern_mark annotation', () => {
            const annotations = [
                {
                    type: 'pattern_mark',
                    timestamp: '2024-01-02T00:00:00',
                    data: {
                        pattern: 'w_bottom',
                        label: 'W底',
                        points: [
                            { timestamp: '2024-01-01T00:00:00', price: 100 },
                            { timestamp: '2024-01-02T00:00:00', price: 105 },
                            { timestamp: '2024-01-03T00:00:00', price: 108 }
                        ]
                    }
                }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markLines.length).toBe(1);
            expect(result.markPoints.length).toBe(3);
        });

        it('should process pattern_mark with neckline', () => {
            const annotations = [
                {
                    type: 'pattern_mark',
                    timestamp: '2024-01-03T00:00:00',
                    data: {
                        pattern: 'head_and_shoulders_bottom',
                        label: '头肩底',
                        points: [
                            { timestamp: '2024-01-01T00:00:00', price: 100 },
                            { timestamp: '2024-01-02T00:00:00', price: 95 },
                            { timestamp: '2024-01-03T00:00:00', price: 100 }
                        ],
                        neckline: { price: 100 }
                    }
                }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markLines.length).toBe(2); // Main line + neckline
        });

        it('should process text_label annotation', () => {
            const annotations = [
                {
                    type: 'text_label',
                    timestamp: '2024-01-02T00:00:00',
                    data: { text: '重要提示', price: 115 }
                }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markPoints.length).toBe(1);
            expect(result.markPoints[0].label.formatter).toBe('重要提示');
        });

        it('should process volume_spike annotation (no-op)', () => {
            const annotations = [
                { type: 'volume_spike', timestamp: '2024-01-02T00:00:00', data: {} }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markPoints.length).toBe(0);
            expect(result.markLines.length).toBe(0);
        });

        it('should process multiple annotations', () => {
            const annotations = [
                { type: 'buy_signal', timestamp: '2024-01-02T00:00:00', data: {} },
                { type: 'sell_signal', timestamp: '2024-01-04T00:00:00', data: {} },
                { type: 'horizontal_line', timestamp: '2024-01-01T00:00:00', data: { price: 115 } }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markPoints.length).toBe(2);
            expect(result.markLines.length).toBe(1);
        });

        it('should handle annotations with invalid data gracefully', () => {
            const annotations = [
                { type: 'horizontal_line', timestamp: '2024-01-01T00:00:00', data: { price: NaN } }
            ];
            const result = processAnnotations(annotations, sampleBars);
            expect(result.markLines.length).toBe(0);
        });
    });

    describe('Individual Renderers', () => {
        let ctx;

        beforeEach(() => {
            ctx = { markPoints: [], markLines: [] };
        });

        describe('renderBuySignal', () => {
            it('should create correct markPoint', () => {
                const annotation = {
                    timestamp: '2024-01-02T00:00:00',
                    data: { label: '买入' }
                };
                renderBuySignal(ctx, annotation, sampleBars);
                expect(ctx.markPoints.length).toBe(1);
                expect(ctx.markPoints[0].symbol).toBe('triangle');
                expect(ctx.markPoints[0].value).toBe('买入');
            });

            it('should use custom color', () => {
                const annotation = {
                    timestamp: '2024-01-02T00:00:00',
                    data: { color: '#00ff00' }
                };
                renderBuySignal(ctx, annotation, sampleBars);
                expect(ctx.markPoints[0].itemStyle.color).toBe('#00ff00');
            });
        });

        describe('renderSellSignal', () => {
            it('should create correct markPoint with rotation', () => {
                const annotation = {
                    timestamp: '2024-01-03T00:00:00',
                    data: { label: '卖出' }
                };
                renderSellSignal(ctx, annotation, sampleBars);
                expect(ctx.markPoints.length).toBe(1);
                expect(ctx.markPoints[0].symbolRotate).toBe(180);
            });
        });

        describe('renderNeutralSignal', () => {
            it('should create diamond markPoint', () => {
                const annotation = {
                    timestamp: '2024-01-02T00:00:00',
                    data: {}
                };
                renderNeutralSignal(ctx, annotation, sampleBars);
                expect(ctx.markPoints[0].symbol).toBe('diamond');
            });
        });

        describe('renderHorizontalLine', () => {
            it('should create yAxis markLine', () => {
                const annotation = {
                    data: { price: 110, label: '测试线', color: '#ff0000' }
                };
                renderHorizontalLine(ctx, annotation, sampleBars);
                expect(ctx.markLines.length).toBe(1);
                expect(ctx.markLines[0].yAxis).toBe(110);
                expect(ctx.markLines[0].lineStyle.color).toBe('#ff0000');
            });

            it('should skip invalid price', () => {
                const annotation = { data: { price: NaN } };
                renderHorizontalLine(ctx, annotation, sampleBars);
                expect(ctx.markLines.length).toBe(0);
            });
        });

        describe('renderTrendLine', () => {
            it('should create coords-based markLine', () => {
                const annotation = {
                    data: {
                        start: '2024-01-01T00:00:00',
                        end: '2024-01-03T00:00:00'
                    }
                };
                renderTrendLine(ctx, annotation, sampleBars);
                expect(ctx.markLines.length).toBe(1);
                expect(ctx.markLines[0].coords.length).toBe(2);
            });
        });

        describe('renderPatternMark', () => {
            it('should create coords line and point markers', () => {
                const annotation = {
                    data: {
                        pattern: 'test_pattern',
                        points: [
                            { timestamp: '2024-01-01T00:00:00', price: 100 },
                            { timestamp: '2024-01-02T00:00:00', price: 110 }
                        ]
                    }
                };
                renderPatternMark(ctx, annotation, sampleBars);
                expect(ctx.markLines.length).toBe(1);
                expect(ctx.markPoints.length).toBe(2);
            });

            it('should skip if not enough points', () => {
                const annotation = {
                    data: {
                        pattern: 'test',
                        points: [{ timestamp: '2024-01-01T00:00:00' }]
                    }
                };
                renderPatternMark(ctx, annotation, sampleBars);
                expect(ctx.markLines.length).toBe(0);
                expect(ctx.markPoints.length).toBe(0);
            });
        });

        describe('renderSupportZone', () => {
            it('should create dashed green line', () => {
                const annotation = { data: { price: 100 } };
                renderSupportZone(ctx, annotation, sampleBars);
                expect(ctx.markLines[0].lineStyle.color).toBe('#48bb78');
                expect(ctx.markLines[0].lineStyle.type).toBe('dashed');
            });
        });

        describe('renderResistanceZone', () => {
            it('should create dashed red line', () => {
                const annotation = { data: { price: 120 } };
                renderResistanceZone(ctx, annotation, sampleBars);
                expect(ctx.markLines[0].lineStyle.color).toBe('#fc8181');
            });
        });

        describe('renderVolumeSpike', () => {
            it('should not create any markers', () => {
                const annotation = { data: {} };
                renderVolumeSpike(ctx, annotation, sampleBars);
                expect(ctx.markPoints.length).toBe(0);
                expect(ctx.markLines.length).toBe(0);
            });
        });

        describe('renderTextLabel', () => {
            it('should create text label markPoint', () => {
                const annotation = {
                    timestamp: '2024-01-02T00:00:00',
                    data: { text: '重要信息', color: '#ffff00' }
                };
                renderTextLabel(ctx, annotation, sampleBars);
                expect(ctx.markPoints[0].label.formatter).toBe('重要信息');
                expect(ctx.markPoints[0].symbol).toBe('none');
            });
        });

        describe('renderRectangle', () => {
            it('should create markLine between two points', () => {
                const annotation = {
                    data: {
                        start: '2024-01-01T00:00:00',
                        end: '2024-01-03T00:00:00'
                    }
                };
                renderRectangle(ctx, annotation, sampleBars);
                expect(ctx.markLines.length).toBe(1);
                expect(ctx.markLines[0].coords.length).toBe(2);
            });
        });

        describe('renderPolygon', () => {
            it('should create markLine through all points', () => {
                const annotation = {
                    data: {
                        points: [
                            '2024-01-01T00:00:00',
                            '2024-01-02T00:00:00',
                            '2024-01-03T00:00:00'
                        ]
                    }
                };
                renderPolygon(ctx, annotation, sampleBars);
                expect(ctx.markLines.length).toBe(1);
                expect(ctx.markLines[0].coords.length).toBe(3);
            });
        });
    });
});
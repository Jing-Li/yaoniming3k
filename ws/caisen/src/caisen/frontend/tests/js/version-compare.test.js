import { describe, it, expect } from 'vitest';
import { buildVersionCompareOption } from '../../src/js/version-compare.js';

describe('buildVersionCompareOption', () => {
  const runs = [
    {
      run_id: 'CaiSenStrategy_20260520_1',
      created_at: '2026-05-20T09:00:00Z',
      metrics: { total_return: 0.12, max_drawdown: 0.08, sharpe_ratio: 1.5, win_rate: 0.55 },
    },
    {
      run_id: 'CaiSenStrategy_20260518_1',
      created_at: '2026-05-18T09:00:00Z',
      metrics: { total_return: 0.05, max_drawdown: 0.03, sharpe_ratio: 0.9, win_rate: 0.48 },
    },
    {
      run_id: 'CaiSenStrategy_20260522_1',
      created_at: '2026-05-22T09:00:00Z',
      metrics: { total_return: -0.02, max_drawdown: 0.12, sharpe_ratio: -0.3, win_rate: 0.42 },
    },
  ];

  it('orders versions chronologically as v0, v1, v2', () => {
    const opt = buildVersionCompareOption(runs);
    expect(opt.xAxis.data).toEqual(['v0', 'v1', 'v2']);
  });

  it('converts ratio metrics to percentages for return / drawdown / win-rate series', () => {
    const opt = buildVersionCompareOption(runs);
    const series = Object.fromEntries(opt.series.map(s => [s.name, s.data]));
    expect(series['总收益率']).toEqual([5, 12, -2]);
    expect(series['最大回撤']).toEqual([3, 8, 12]);
    expect(series['胜率']).toEqual([48, 55, 42]);
  });

  it('keeps sharpe ratio on the secondary axis with raw ratio values', () => {
    const opt = buildVersionCompareOption(runs);
    const sharpe = opt.series.find(s => s.name === '夏普比率');
    expect(sharpe).toBeDefined();
    expect(sharpe.yAxisIndex).toBe(1);
    expect(sharpe.type).toBe('line');
    expect(sharpe.data).toEqual([0.9, 1.5, -0.3]);
  });

  it('treats missing metrics as zero without throwing', () => {
    const opt = buildVersionCompareOption([
      { run_id: 'A', created_at: '2026-01-01T00:00:00Z' },
      { run_id: 'B', created_at: '2026-02-01T00:00:00Z', metrics: {} },
    ]);
    expect(opt.xAxis.data).toEqual(['v0', 'v1']);
    opt.series.forEach(s => {
      s.data.forEach(v => expect(v).toBe(0));
    });
  });

  it('returns a transparent background suitable for the glass panel', () => {
    const opt = buildVersionCompareOption(runs);
    expect(opt.backgroundColor).toBe('transparent');
  });
});

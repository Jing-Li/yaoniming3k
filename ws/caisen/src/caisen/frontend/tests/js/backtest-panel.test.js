import { describe, it, expect } from 'vitest';
import {
  buildWsUrl,
  renderParamsSchema,
  buildRunRequest,
  handleWsMessage,
} from '../../src/js/backtest-panel.js';

// ---------------------------------------------------------------------------
// 1. tracer bullet：buildWsUrl 构造正确的 WebSocket URL
// ---------------------------------------------------------------------------

describe('buildWsUrl', () => {
  it('constructs ws URL with run_id and query params', () => {
    const url = buildWsUrl('MyRun_001', {
      strategy_name: 'CaiSenStrategy',
      symbol: '000001.SZ',
      freq: '1d',
      start: '2023-01-01',
      end: '2024-12-31',
    });
    expect(url).toContain('/ws/runs/MyRun_001/progress');
    expect(url).toContain('strategy_name=CaiSenStrategy');
    expect(url).toContain('symbol=000001.SZ');
    expect(url).toContain('start=2023-01-01');
  });
});

// ---------------------------------------------------------------------------
// 2. renderParamsSchema：float/bool/select 生成正确 HTML
// ---------------------------------------------------------------------------

describe('renderParamsSchema', () => {
  it('renders number input for float type', () => {
    const html = renderParamsSchema([
      { name: 'stop_loss_factor', type: 'float', default: 0.95, min: 0.9, max: 1.0 },
    ]);
    expect(html).toContain('type="number"');
    expect(html).toContain('name="stop_loss_factor"');
    expect(html).toContain('step="any"');
    expect(html).toContain('min="0.9"');
  });

  it('renders checkbox for bool type', () => {
    const html = renderParamsSchema([
      { name: 'use_filter', type: 'bool', default: true },
    ]);
    expect(html).toContain('type="checkbox"');
    expect(html).toContain('name="use_filter"');
    expect(html).toContain('checked');
  });

  it('returns empty string for empty schema', () => {
    expect(renderParamsSchema([])).toBe('');
    expect(renderParamsSchema(null)).toBe('');
  });
});

// ---------------------------------------------------------------------------
// 3. buildRunRequest：构造 POST 请求体
// ---------------------------------------------------------------------------

describe('buildRunRequest', () => {
  it('builds correct request body', () => {
    const req = buildRunRequest({
      strategy_name: 'CaiSenStrategy',
      symbol: '000001.SZ',
      freq: '1d',
      start: '2023-01-01',
      end: '2024-12-31',
      params: { stop_loss_factor: 0.95 },
    });
    expect(req.strategy_name).toBe('CaiSenStrategy');
    expect(req.symbol).toBe('000001.SZ');
    expect(req.params.stop_loss_factor).toBe(0.95);
  });

  it('defaults params to empty object', () => {
    const req = buildRunRequest({
      strategy_name: 'X', symbol: 'A', freq: '1d', start: '2023-01-01', end: '2023-12-31',
    });
    expect(req.params).toEqual({});
  });
});

// ---------------------------------------------------------------------------
// 4. handleWsMessage：消息分发
// ---------------------------------------------------------------------------

describe('handleWsMessage', () => {
  it('done message returns redirect action with report URL', () => {
    const result = handleWsMessage({ status: 'done', run_id: 'CaiSen_20240526' });
    expect(result.action).toBe('redirect');
    expect(result.payload).toContain('report.html');
    expect(result.payload).toContain('CaiSen_20240526');
  });

  it('running message returns progress with percent', () => {
    const result = handleWsMessage({ status: 'running', processed: 100, total: 400, current_date: '2023-05-01' });
    expect(result.action).toBe('progress');
    expect(result.payload.percent).toBe(25);
    expect(result.payload.current_date).toBe('2023-05-01');
  });

  it('error message returns error action', () => {
    const result = handleWsMessage({ status: 'error', message: '数据为空' });
    expect(result.action).toBe('error');
    expect(result.payload).toContain('数据为空');
  });
});

/**
 * optimize-charts.js
 * 优化结果可视化
 *
 * 功能：
 * - Top-N 排行表
 * - 参数热力图（ECharts heatmap）
 * - 雷达图对比
 * - 进化趋势图
 */

import { createLogger } from './logger.js';

const log = createLogger('OptimizeCharts');

/** 当前结果数据 */
let _results = null;
/** 选中对比的行索引 */
let _selectedRows = new Set();
/** ECharts 实例 */
let _heatmapInstance = null;
let _radarInstance = null;
let _evolveChartInstance = null;

/**
 * 初始化
 */
export function initOptimizeCharts() {
  // 监听窗口 resize
  window.addEventListener('resize', () => {
    _heatmapInstance?.resize();
    _radarInstance?.resize();
    _evolveChartInstance?.resize();
  });
}

/**
 * 显示优化结果
 */
export function showResults(data) {
  _results = data;
  _selectedRows.clear();

  const emptyEl = document.getElementById('results-empty');
  const tableWrap = document.getElementById('results-table-wrap');
  const chartsEl = document.getElementById('results-charts');

  if (emptyEl) emptyEl.style.display = 'none';
  if (tableWrap) tableWrap.style.display = '';

  renderResultsTable(data.results || []);

  if (data.results && data.results.length > 0) {
    if (chartsEl) chartsEl.style.display = '';
    renderHeatmap(data.results);
  }
}

/**
 * 显示进化结果
 */
export function showEvolveResults(data) {
  const chartWrap = document.getElementById('evo-chart-wrap');
  if (chartWrap) chartWrap.style.display = '';

  renderEvolveTrend(data.generations || []);
}

/**
 * 添加进化代数据（实时更新）
 */
export function addEvolveGeneration(genData) {
  if (!_evolveChartInstance) {
    const el = document.getElementById('evo-chart');
    if (!el) return;
    _evolveChartInstance = echarts.init(el, null, { renderer: 'canvas' });
  }

  const chartWrap = document.getElementById('evo-chart-wrap');
  if (chartWrap) chartWrap.style.display = '';

  // 获取现有数据或初始化
  const existingOption = _evolveChartInstance.getOption();
  let xData = [];
  let yData = [];

  if (existingOption && existingOption.series && existingOption.series[0]) {
    xData = [...(existingOption.xAxis[0].data || [])];
    yData = [...(existingOption.series[0].data || [])];
  }

  xData.push(`第${genData.gen}代`);
  yData.push(genData.score);

  _evolveChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { color: '#cbd5e1' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    },
    yAxis: {
      type: 'value',
      name: '评分',
      axisLabel: { color: '#cbd5e1' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
    },
    series: [{
      type: 'line',
      data: yData,
      smooth: true,
      lineStyle: { color: '#8b5cf6', width: 3 },
      itemStyle: { color: '#8b5cf6' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(139, 92, 246, 0.3)' },
            { offset: 1, color: 'rgba(139, 92, 246, 0.02)' },
          ],
        },
      },
      markPoint: {
        data: [{ type: 'max', name: '最优' }],
        itemStyle: { color: '#10b981' },
      },
    }],
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    backgroundColor: 'transparent',
  });
}

/**
 * 渲染 Top-N 排行表
 */
function renderResultsTable(results) {
  const tbody = document.getElementById('results-tbody');
  if (!tbody) return;

  tbody.innerHTML = results.map((r, idx) => {
    const pct = v => (v * 100).toFixed(1) + '%';
    const scoreClass = r.score >= 0.7 ? 'sp-score--high' :
                       r.score >= 0.4 ? 'sp-score--mid' : 'sp-score--low';

    return `
      <tr class="sp-result-row" data-idx="${idx}">
        <td><span class="sp-rank sp-rank--${idx < 3 ? 'top' : 'normal'}">${r.rank}</span></td>
        <td><span class="sp-score ${scoreClass}">${r.score.toFixed(4)}</span></td>
        <td class="${r.annual_return >= 0 ? 'sp-val--up' : 'sp-val--down'}">${pct(r.annual_return)}</td>
        <td class="sp-val--down">${pct(r.max_drawdown)}</td>
        <td>${r.sharpe_ratio.toFixed(2)}</td>
        <td>${pct(r.win_rate)}</td>
        <td>${r.total_trades}</td>
        <td>
          <label class="sp-compare-check">
            <input type="checkbox" class="sp-compare-cb" data-idx="${idx}">
            对比
          </label>
        </td>
      </tr>
    `;
  }).join('');

  // 绑定对比选择
  tbody.querySelectorAll('.sp-compare-cb').forEach(cb => {
    cb.addEventListener('change', () => {
      const idx = parseInt(cb.dataset.idx, 10);
      if (cb.checked) {
        if (_selectedRows.size >= 3) {
          cb.checked = false;
          return;
        }
        _selectedRows.add(idx);
      } else {
        _selectedRows.delete(idx);
      }
      updateRadarChart();
    });
  });

  // 点击行展开参数详情
  tbody.querySelectorAll('.sp-result-row').forEach(row => {
    row.addEventListener('click', (e) => {
      if (e.target.closest('.sp-compare-check')) return;
      const idx = parseInt(row.dataset.idx, 10);
      const r = results[idx];
      showParamDetail(r);
    });
  });
}

/**
 * 显示参数详情弹出
 */
function showParamDetail(result) {
  // 复用表格下方区域展示
  let detailEl = document.getElementById('param-detail-popup');
  if (!detailEl) {
    detailEl = document.createElement('div');
    detailEl.id = 'param-detail-popup';
    detailEl.className = 'sp-panel-card sp-param-detail';
    document.getElementById('results-table-wrap')?.appendChild(detailEl);
  }

  const paramsHtml = Object.entries(result.params || {})
    .map(([k, v]) => `<div class="sp-param-item"><span class="sp-param-key">${k}</span><span class="sp-param-val">${typeof v === 'number' ? v.toFixed?.(4) ?? v : v}</span></div>`)
    .join('');

  detailEl.innerHTML = `
    <h4>第 ${result.rank} 名参数详情</h4>
    <div class="sp-param-grid">${paramsHtml}</div>
  `;
  detailEl.style.display = '';
}

/**
 * 渲染参数热力图
 */
function renderHeatmap(results) {
  const el = document.getElementById('heatmap-chart');
  if (!el) return;

  if (_heatmapInstance) _heatmapInstance.dispose();
  _heatmapInstance = echarts.init(el, null, { renderer: 'canvas' });

  // 收集所有参数名
  const paramNames = new Set();
  results.forEach(r => {
    Object.keys(r.params || {}).forEach(k => paramNames.add(k));
  });
  const paramList = [...paramNames];

  // 构建热力图数据: [paramIndex, resultIndex, score]
  const heatData = [];
  let maxScore = 0;

  results.forEach((r, ri) => {
    paramList.forEach((pn, pi) => {
      const val = r.params?.[pn];
      if (val !== undefined) {
        // 用归一化值表示热力
        const normalized = typeof val === 'number' ? val : (val === true ? 1 : 0);
        heatData.push([pi, ri, r.score]);
        maxScore = Math.max(maxScore, r.score);
      }
    });
  });

  _heatmapInstance.setOption({
    tooltip: {
      position: 'top',
      formatter: (p) => {
        const ri = p.value[1];
        const pi = p.value[0];
        return `#${ri + 1} ${paramList[pi]}<br/>评分: ${p.value[2].toFixed(4)}`;
      },
    },
    xAxis: {
      type: 'category',
      data: paramList,
      axisLabel: {
        color: '#cbd5e1',
        rotate: 30,
        fontSize: 11,
      },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    },
    yAxis: {
      type: 'category',
      data: results.map((_, i) => `#${i + 1}`),
      axisLabel: { color: '#cbd5e1' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    },
    visualMap: {
      min: 0,
      max: maxScore || 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: {
        color: ['#1a2234', '#3b82f6', '#10b981', '#f59e0b'],
      },
      textStyle: { color: '#cbd5e1' },
    },
    series: [{
      type: 'heatmap',
      data: heatData,
      label: { show: false },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' },
      },
    }],
    grid: { left: 50, right: 20, top: 10, bottom: 60 },
    backgroundColor: 'transparent',
  });
}

/**
 * 更新雷达图对比
 */
function updateRadarChart() {
  const el = document.getElementById('radar-chart');
  if (!el || _selectedRows.size === 0) return;

  if (!_radarInstance) {
    _radarInstance = echarts.init(el, null, { renderer: 'canvas' });
  }

  const colors = ['#3b82f6', '#10b981', '#f59e0b'];
  const series = [];
  let i = 0;

  _selectedRows.forEach(idx => {
    const r = _results.results[idx];
    if (!r) return;

    series.push({
      name: `#${r.rank}`,
      value: [
        Math.max(0, r.annual_return),
        r.sharpe_ratio,
        r.win_rate,
        r.profit_factor || 1,
        1 - r.max_drawdown,
      ],
      lineStyle: { color: colors[i], width: 2 },
      itemStyle: { color: colors[i] },
      areaStyle: { color: colors[i], opacity: 0.15 },
    });
    i++;
  });

  _radarInstance.setOption({
    tooltip: {},
    legend: {
      data: series.map(s => s.name),
      textStyle: { color: '#cbd5e1' },
      bottom: 0,
    },
    radar: {
      indicator: [
        { name: '年化收益', max: 1 },
        { name: '夏普比率', max: 3 },
        { name: '胜率', max: 1 },
        { name: '盈亏比', max: 3 },
        { name: '1-回撤', max: 1 },
      ],
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#cbd5e1' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
      splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.04)'] } },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    },
    series: [{
      type: 'radar',
      data: series,
    }],
    backgroundColor: 'transparent',
  });
}

/**
 * 渲染进化趋势图
 */
function renderEvolveTrend(generations) {
  const el = document.getElementById('evo-chart');
  if (!el) return;

  if (_evolveChartInstance) _evolveChartInstance.dispose();
  _evolveChartInstance = echarts.init(el, null, { renderer: 'canvas' });

  const xData = generations.map(g => `第${g.gen}代`);
  const yData = generations.map(g => g.score);

  _evolveChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0];
        const gen = generations[p.dataIndex];
        return `第${gen.gen}代<br/>评分: ${gen.score.toFixed(4)}<br/>交易数: ${gen.trade_count}<br/><span style="font-size:11px">${gen.rules_summary?.substring(0, 100) || ''}</span>`;
      },
    },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { color: '#cbd5e1' },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    },
    yAxis: {
      type: 'value',
      name: '评分',
      axisLabel: { color: '#cbd5e1' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
    },
    series: [{
      type: 'line',
      data: yData,
      smooth: true,
      lineStyle: { color: '#8b5cf6', width: 3 },
      itemStyle: { color: '#8b5cf6' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(139, 92, 246, 0.3)' },
            { offset: 1, color: 'rgba(139, 92, 246, 0.02)' },
          ],
        },
      },
      markPoint: {
        data: [{ type: 'max', name: '最优' }],
        itemStyle: { color: '#10b981' },
      },
    }],
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    backgroundColor: 'transparent',
  });
}

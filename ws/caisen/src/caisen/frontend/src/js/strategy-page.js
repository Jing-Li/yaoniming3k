/**
 * strategy-page.js
 * 策略中心页面主控制器
 */

import { createLogger } from './logger.js';
import { toast } from './toast.js';
import { initStrategyExplorer, selectStrategyByName } from './strategy-explorer.js';
import { initOptimizePanel } from './optimize-panel.js';
import { initEvolvePanel } from './evolve-panel.js';
import { initOptimizeCharts } from './optimize-charts.js';

const log = createLogger('StrategyPage');

export const pageState = {
  strategies: [],
  dataSources: [],
  activePanel: null,
  selectedStrategy: null,
};

export async function initStrategyPage() {
  log.info('策略中心页面初始化');

  try {
    await Promise.all([loadStrategies(), loadDataSources()]);
  } catch (err) {
    log.error('初始化加载失败', { error: err.message });
    toast.error('初始化加载失败，请刷新重试');
  }

  initStrategyExplorer(pageState.strategies);
  initOptimizePanel(pageState);
  initEvolvePanel(pageState);
  initOptimizeCharts();

  // 填充策略下拉框
  populateStrategySelects();
  // 填充品种下拉框
  populateSymbolSelects();

  // 绑定策略下拉框变更
  ['opt-strategy', 'evo-strategy'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', () => onStrategySelectChange(el.value));
  });

  // 默认选中第一个策略
  if (pageState.strategies.length > 0) {
    onStrategySelectChange(pageState.strategies[0].name);
  }
}

/**
 * 策略下拉框变更 → 切换面板 + 同步侧栏 + 更新参数
 */
export async function onStrategySelectChange(name) {
  if (!name) return;
  const strategy = pageState.strategies.find(s => s.name === name);
  if (!strategy) return;

  // 切换面板
  switchPanel(strategy.type);
  // 同步侧栏高亮
  selectStrategyByName(name);
  // 同步两个下拉框
  syncStrategySelects(name);
}

/** 同步所有策略下拉框的值 */
function syncStrategySelects(name) {
  ['opt-strategy', 'evo-strategy'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = name;
  });
}

/** 填充策略下拉框 */
function populateStrategySelects() {
  ['opt-strategy', 'evo-strategy'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = pageState.strategies.map(s =>
      `<option value="${s.name}">${s.display_name || s.name}</option>`
    ).join('');
  });
}

/** 填充品种下拉框 */
function populateSymbolSelects() {
  const symbols = [...new Set(pageState.dataSources.map(ds => ds.symbol))].sort();
  ['opt-symbol', 'evo-symbol'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    if (symbols.length === 0) {
      el.innerHTML = '<option value="">无数据</option>';
      return;
    }
    el.innerHTML = symbols.map(sym =>
      `<option value="${sym}">${sym}</option>`
    ).join('');
  });

  // 品种变更时自动填入日期范围
  ['opt-symbol', 'evo-symbol'].forEach(selId => {
    const sel = document.getElementById(selId);
    if (!sel) return;
    sel.addEventListener('change', () => autoFillDates(sel.value, selId.startsWith('opt') ? 'opt' : 'evo'));
  });
}

/** 根据品种自动填入可用日期范围 */
function autoFillDates(symbol, prefix) {
  const ds = pageState.dataSources.find(d => d.symbol === symbol);
  if (!ds || !ds.date_range) return;
  const startEl = document.getElementById(`${prefix}-start`);
  const endEl = document.getElementById(`${prefix}-end`);
  if (startEl && !startEl.value) startEl.value = ds.date_range.start;
  if (endEl && !endEl.value) endEl.value = ds.date_range.end;
}

/** 切换右侧面板 */
export function switchPanel(strategyType) {
  const emptyHint = document.getElementById('sp-empty-hint');
  const gridPanel = document.getElementById('sp-panel-grid');
  const evolvePanel = document.getElementById('sp-panel-evolve');

  if (emptyHint) emptyHint.style.display = 'none';
  if (gridPanel) gridPanel.style.display = strategyType === 'code' ? '' : 'none';
  if (evolvePanel) evolvePanel.style.display = strategyType === 'llm' ? '' : 'none';

  pageState.activePanel = strategyType === 'code' ? 'grid' : 'evolve';
  log.info('面板切换', { type: strategyType, panel: pageState.activePanel });
}

async function loadStrategies() {
  const res = await fetch('/api/strategies');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  pageState.strategies = data.strategies || [];
  log.info('策略列表加载完成', { count: pageState.strategies.length });
}

async function loadDataSources() {
  const res = await fetch('/api/data-sources');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  pageState.dataSources = data.data_sources || [];
  log.info('数据源加载完成', { count: pageState.dataSources.length });
}

/**
 * optimize-panel.js
 * 网格搜索面板 — 使用后端 optimize_config 的真实参数范围
 */

import { createLogger } from './logger.js';
import { toast } from './toast.js';
import { pageState } from './strategy-page.js';
import { showResults } from './optimize-charts.js';

const log = createLogger('OptimizePanel');

let _paramRanges = {};
let _currentWs = null;

export function initOptimizePanel(state) {
  const form = document.getElementById('opt-form');
  if (form) form.addEventListener('submit', handleSubmit);
}

/**
 * 更新参数范围 — 使用 optimize_config 的真实搜索范围
 */
export function updateParamRanges(strategy) {
  const container = document.getElementById('opt-param-ranges');
  const patternContainer = document.getElementById('opt-pattern-presets');
  if (!container) return;

  _paramRanges = {};

  const optConfig = strategy.optimize_config;

  // 如果没有 optimize_config 或不是 grid_search 类型，显示基础参数
  if (!optConfig || optConfig.type !== 'grid_search') {
    container.innerHTML = '<p class="sp-muted">该策略不支持网格搜索优化</p>';
    if (patternContainer) patternContainer.innerHTML = '';
    updateTotalCount();
    return;
  }

  const params = optConfig.params || {};

  container.innerHTML = Object.entries(params).map(([key, cfg]) => {
    const values = cfg.values || [];
    const displayName = cfg.display_name || key;
    _paramRanges[key] = [...values];

    return `
      <div class="opt-param-row">
        <div class="opt-param-label">${displayName}</div>
        <div class="opt-param-control">
          <div class="opt-range-values">
            ${values.map(v => `
              <label class="opt-range-chip">
                <input type="checkbox" class="opt-range-input" data-param="${key}"
                       data-value="${v}" checked>
                <span>${v}</span>
              </label>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }).join('');

  // 绑定 checkbox 变更
  container.querySelectorAll('.opt-range-input').forEach(input => {
    input.addEventListener('change', () => {
      rebuildParamRanges();
      updateTotalCount();
    });
  });

  // 渲染形态预设
  renderPatternPresets(optConfig.pattern_presets || []);

  // 更新总组合数
  const totalEl = document.getElementById('opt-total-count');
  if (totalEl && optConfig.total_combinations) {
    totalEl.textContent = `全量组合数: ${optConfig.total_combinations.toLocaleString()}`;
  }

  updateTotalCount();
}

/** 渲染形态组合预设 */
function renderPatternPresets(presets) {
  const container = document.getElementById('opt-pattern-presets');
  if (!container) return;

  if (presets.length === 0) {
    container.innerHTML = '<p class="sp-muted">无形态预设</p>';
    return;
  }

  container.innerHTML = presets.map((p, i) => `
    <div class="opt-preset-card ${i === 1 ? 'opt-preset-card--active' : ''}" data-preset="${i}">
      <div class="opt-preset-card__name">${p.name}</div>
      <div class="opt-preset-card__desc">${p.desc}</div>
    </div>
  `).join('');

  // 默认选中"平衡"预设
  container.querySelectorAll('.opt-preset-card').forEach(card => {
    card.addEventListener('click', () => {
      container.querySelectorAll('.opt-preset-card').forEach(c => c.classList.remove('opt-preset-card--active'));
      card.classList.add('opt-preset-card--active');
    });
  });
}

function rebuildParamRanges() {
  const inputs = document.querySelectorAll('.opt-range-input:checked');
  _paramRanges = {};

  inputs.forEach(input => {
    const param = input.dataset.param;
    const value = parseFloat(input.dataset.value);
    if (!_paramRanges[param]) _paramRanges[param] = [];
    if (!_paramRanges[param].includes(value)) _paramRanges[param].push(value);
  });
}

function updateTotalCount() {
  let total = 1;
  const values = Object.values(_paramRanges);

  if (values.length === 0) {
    total = 0;
  } else {
    values.forEach(arr => {
      if (arr.length === 0) { total = 0; return; }
      total *= arr.length;
    });
  }

  const countEl = document.getElementById('opt-total-count');
  const timeEl = document.getElementById('opt-est-time');

  if (countEl) countEl.textContent = `当前组合数: ${total.toLocaleString()}`;

  if (timeEl && total > 0) {
    const workers = parseInt(document.getElementById('opt-workers')?.value || '4', 10);
    const seconds = Math.ceil(total * 2 / workers);
    if (seconds < 60) timeEl.textContent = `预估耗时: ~${seconds}秒`;
    else if (seconds < 3600) timeEl.textContent = `预估耗时: ~${Math.ceil(seconds / 60)}分钟`;
    else timeEl.textContent = `预估耗时: ~${(seconds / 3600).toFixed(1)}小时`;
  }
}

async function handleSubmit(e) {
  e.preventDefault();

  const symbol = document.getElementById('opt-symbol')?.value;
  const freq = document.getElementById('opt-freq')?.value;
  const start = document.getElementById('opt-start')?.value;
  const end = document.getElementById('opt-end')?.value;
  const workers = parseInt(document.getElementById('opt-workers')?.value || '4', 10);
  const topN = parseInt(document.getElementById('opt-topn')?.value || '10', 10);

  if (!symbol || !freq || !start || !end) {
    toast.warn('请填写完整的品种、频率和日期范围');
    return;
  }

  rebuildParamRanges();
  const paramRanges = {};
  for (const [key, values] of Object.entries(_paramRanges)) {
    if (values.length > 0) paramRanges[key] = values;
  }

  const body = {
    strategy_name: pageState.selectedStrategy?.name || 'CaiSenStrategy',
    symbol, freq, start, end,
    workers, top_n: topN,
    param_ranges: Object.keys(paramRanges).length > 0 ? paramRanges : null,
  };

  log.info('提交优化任务', body);

  const submitBtn = document.getElementById('opt-submit');
  if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = '提交中...'; }

  try {
    const res = await fetch('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const { job_id } = await res.json();
    toast.success('优化任务已提交');
    connectWebSocket(job_id);

  } catch (err) {
    log.error('提交失败', { error: err.message });
    toast.error(`提交失败: ${err.message}`);
  } finally {
    if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = '开始优化'; }
  }
}

function connectWebSocket(jobId) {
  if (_currentWs) { _currentWs.onmessage = null; _currentWs.close(); _currentWs = null; }

  const progressEl = document.getElementById('opt-progress');
  const barEl = document.getElementById('opt-progress-bar');
  const pctEl = document.getElementById('opt-progress-pct');
  const infoEl = document.getElementById('opt-progress-info');

  if (progressEl) progressEl.style.display = '';

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${location.host}/ws/optimize/${jobId}/progress`);
  _currentWs = ws;

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.status === 'running') {
      const pct = msg.total > 0 ? Math.round((msg.progress / msg.total) * 100) : 0;
      if (barEl) barEl.style.width = `${pct}%`;
      if (pctEl) pctEl.textContent = `${pct}%`;
      if (infoEl) infoEl.textContent = `${msg.message} (${msg.progress}/${msg.total})`;
    }

    if (msg.status === 'done') {
      if (barEl) barEl.style.width = '100%';
      if (pctEl) pctEl.textContent = '100%';
      if (infoEl) infoEl.textContent = msg.message || '优化完成';
      toast.success('优化完成！');
      if (msg.results) {
        showResults(msg.results);
        const resultsArea = document.getElementById('opt-results-area');
        if (resultsArea) resultsArea.style.display = '';
      }
      ws.close();
    }

    if (msg.status === 'error') {
      if (infoEl) infoEl.textContent = `错误: ${msg.message}`;
      toast.error(`优化失败: ${msg.message}`);
      ws.close();
    }
  };

  ws.onerror = () => { toast.error('WebSocket 连接失败'); _currentWs = null; };
}

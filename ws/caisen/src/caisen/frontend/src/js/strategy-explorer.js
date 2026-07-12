/**
 * strategy-explorer.js
 * 策略浏览模块 — 左侧栏策略卡片 + 详情面板
 */

import { createLogger } from './logger.js';
import { toast } from './toast.js';
import { pageState, switchPanel, onStrategySelectChange } from './strategy-page.js';
import { updateParamRanges } from './optimize-panel.js';

const log = createLogger('StrategyExplorer');

let _strategies = [];

export function initStrategyExplorer(strategies) {
  _strategies = strategies;
  renderStrategyList();
}

function renderStrategyList() {
  const container = document.getElementById('sp-strategy-list');
  if (!container) return;

  if (_strategies.length === 0) {
    container.innerHTML = '<p class="sp-muted">暂无可用策略</p>';
    return;
  }

  container.innerHTML = _strategies.map(s => {
    const typeClass = s.type === 'llm' ? 'sp-type--llm' : 'sp-type--code';
    const typeLabel = s.type === 'llm' ? 'LLM' : 'Code';
    const paramCount = (s.params_schema || []).length;
    const presetCount = (s.config_presets || []).length;

    return `
      <div class="sp-card" data-strategy="${s.name}">
        <div class="sp-card__header">
          <span class="sp-card__name">${s.display_name || s.name}</span>
          <span class="sp-type-badge ${typeClass}">${typeLabel}</span>
        </div>
        <div class="sp-card__meta">
          <span>参数: ${paramCount}</span>
          <span>预设: ${presetCount}</span>
        </div>
        ${s.note ? `<div class="sp-card__note">${s.note}</div>` : ''}
      </div>
    `;
  }).join('');

  container.querySelectorAll('.sp-card').forEach(card => {
    card.addEventListener('click', () => {
      const name = card.dataset.strategy;
      // 高亮
      container.querySelectorAll('.sp-card').forEach(c => c.classList.remove('sp-card--active'));
      card.classList.add('sp-card--active');
      // 通过统一入口切换
      onStrategySelectChange(name);
    });
  });
}

/**
 * 选中策略 → 显示详情 + 更新参数范围（由 strategy-page 调用）
 */
export async function selectStrategyByName(name) {
  log.info('选中策略', { name });

  try {
    const res = await fetch(`/api/strategies/${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const strategy = await res.json();

    pageState.selectedStrategy = strategy;

    // 切换面板
    switchPanel(strategy.type);

    // 渲染详情
    renderStrategyDetail(strategy);

    // 更新优化面板参数范围
    updateParamRanges(strategy);

    // 高亮侧栏卡片
    const container = document.getElementById('sp-strategy-list');
    if (container) {
      container.querySelectorAll('.sp-card').forEach(c => {
        c.classList.toggle('sp-card--active', c.dataset.strategy === name);
      });
    }

  } catch (err) {
    log.error('加载策略详情失败', { name, error: err.message });
    toast.error('加载策略详情失败');
  }
}

function renderStrategyDetail(strategy) {
  const detail = document.getElementById('sp-strategy-detail');
  if (!detail) return;
  detail.style.display = '';

  const nameEl = document.getElementById('sp-detail-name');
  const typeEl = document.getElementById('sp-detail-type');
  const noteEl = document.getElementById('sp-detail-note');

  if (nameEl) nameEl.textContent = strategy.display_name || strategy.name;
  if (typeEl) {
    const isLLM = strategy.type === 'llm';
    typeEl.textContent = isLLM ? 'LLM' : 'Code';
    typeEl.className = `sp-type-badge ${isLLM ? 'sp-type--llm' : 'sp-type--code'}`;
  }
  if (noteEl) {
    noteEl.textContent = strategy.note || '';
    noteEl.style.display = strategy.note ? '' : 'none';
  }

  renderParamsTable(strategy.params_schema || []);
  renderPresets(strategy.config_presets || []);
}

function renderParamsTable(schema) {
  const container = document.getElementById('sp-params-table');
  if (!container) return;

  if (schema.length === 0) {
    container.innerHTML = '<p class="sp-muted">无可调参数</p>';
    return;
  }

  const rows = schema.map(p => {
    const displayName = p.display_name || p.name;

    if (p.type === 'text') {
      // LLM prompt 模板 — 展示可展开文本块
      return `
        <tr>
          <td class="sp-param-name" colspan="3">
            <div class="sp-param-display">${displayName}</div>
            <details class="sp-param-text-block">
              <summary>查看完整模板</summary>
              <pre class="sp-param-pre">${p.full_text || p.default || ''}</pre>
            </details>
          </td>
        </tr>
      `;
    }

    if (p.type === 'bool') {
      return `
        <tr>
          <td class="sp-param-name">${displayName}</td>
          <td class="sp-param-value">
            <span class="sp-bool-tag ${p.default ? 'sp-bool--on' : 'sp-bool--off'}">${p.default ? '开' : '关'}</span>
          </td>
          <td class="sp-param-range">${p.options ? p.options.join(', ') : '—'}</td>
        </tr>
      `;
    }

    // float / int — 显示 options 或 min~max
    let rangeStr = '—';
    if (p.options && p.options.length > 0) {
      rangeStr = p.options.join(', ');
    } else if (p.min != null && p.max != null) {
      rangeStr = `${p.min} ~ ${p.max}`;
    }

    return `
      <tr>
        <td class="sp-param-name">${displayName}</td>
        <td class="sp-param-value"><code>${p.default ?? '—'}</code></td>
        <td class="sp-param-range">${rangeStr}</td>
      </tr>
    `;
  }).join('');

  container.innerHTML = `
    <table class="sp-table sp-table--compact">
      <thead>
        <tr>
          <th>参数</th>
          <th>默认值</th>
          <th>搜索范围</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderPresets(presets) {
  const container = document.getElementById('sp-presets-list');
  if (!container) return;

  if (presets.length === 0) {
    container.innerHTML = '<p class="sp-muted">无配置预设</p>';
    return;
  }

  container.innerHTML = presets.map(p =>
    `<div class="sp-preset-chip">${p}</div>`
  ).join('');
}

/**
 * backtest-panel.js
 * 新建回测面板逻辑：纯函数 + DOM 操作
 *
 * 策略参数由服务端 configs/strategies/*.yaml 管理，前端只选配置预设名。
 */

import { createLogger } from './logger.js';
import { toast } from './toast.js';

const log = createLogger('BacktestPanel');

const STORAGE_KEY = 'caisen_bp_form';

// ---------------------------------------------------------------------------
// 纯函数（可测试）
// ---------------------------------------------------------------------------

/**
 * 构造 WebSocket 进度端点 URL
 * @param {string} runId
 * @param {Object} params - { strategy_name, symbol, freq, start, end, config_name? }
 * @returns {string}
 */
export function buildWsUrl(runId, params) {
  const entries = Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== '');
  const qs = entries
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${location.host}/ws/runs/${runId}/progress?${qs}`;
}

/**
 * 从表单字段值构造 POST /api/runs 请求体
 * @param {Object} fields - { strategy_name, symbol, freq, start, end, config_name? }
 * @returns {Object}
 */
export function buildRunRequest(fields) {
  const { strategy_name, symbol, freq, start, end, config_name } = fields;
  const body = { strategy_name, symbol, freq, start, end };
  if (config_name) body.config_name = config_name;
  return body;
}

/**
 * 处理 WebSocket 消息，返回副作用描述（不直接操作 DOM，便于测试）
 * @param {Object} msg - { status, processed, total, current_date, run_id, message }
 * @returns {{ action: string, payload: any }}
 */
export function handleWsMessage(msg) {
  switch (msg.status) {
    case 'running':
      return {
        action: 'progress',
        payload: {
          processed: msg.processed,
          total: msg.total,
          percent: Math.round((msg.processed / msg.total) * 100),
          current_date: msg.current_date,
        },
      };
    case 'done':
      return {
        action: 'redirect',
        payload: `report.html?run_id=${msg.run_id}`,
      };
    case 'error':
      return {
        action: 'error',
        payload: msg.message,
      };
    default:
      return { action: 'unknown', payload: msg };
  }
}

// ---------------------------------------------------------------------------
// 日期快选 Chips
// ---------------------------------------------------------------------------

const RANGE_DAYS = {
  '1w': 7,
  '1m': 30,
  '3m': 90,
  '6m': 180,
  '1y': 365,
};

/**
 * 格式化日期为 YYYY-MM-DD
 */
function _fmtDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/**
 * 点击日期快选 chip 时计算并填充日期
 * @param {string} rangeKey - '1w' | '1m' | '3m' | '6m' | '1y' | 'all'
 */
function _onChipClick(rangeKey) {
  const startEl = document.getElementById('bp-start');
  const endEl = document.getElementById('bp-end');
  if (!startEl || !endEl) return;

  // 获取数据源的可用范围
  const dsRange = _getCurrentDataSourceRange();

  if (rangeKey === 'all') {
    // "全部" = 数据源的完整范围
    if (dsRange) {
      startEl.value = dsRange.start;
      endEl.value = dsRange.end;
    }
  } else {
    const days = RANGE_DAYS[rangeKey];
    if (!days) return;

    // end = 数据源的结束日期 或 今天
    const endStr = dsRange?.end || _fmtDate(new Date());
    const endDate = new Date(endStr);

    // start = end - N days
    const startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - days);

    // 不能早于数据源的起始日期
    if (dsRange && startDate < new Date(dsRange.start)) {
      startDate.setTime(new Date(dsRange.start).getTime());
    }

    endEl.value = endStr;
    startEl.value = _fmtDate(startDate);
  }

  // 高亮当前 chip
  _highlightChip(rangeKey);
  _saveFormState();
  log.info('日期快选 →', rangeKey, { start: startEl.value, end: endEl.value });
}

/**
 * 获取当前选中数据源的日期范围
 */
function _getCurrentDataSourceRange() {
  const dsVal = document.getElementById('bp-datasource')?.value;
  if (!dsVal) return null;
  const [symbol, freq] = dsVal.split('|');
  const source = _dataSourcesCache.find(s => s.symbol === symbol && s.freq === freq);
  return source?.date_range || null;
}

/**
 * 高亮选中的 chip，取消其他 chip
 */
function _highlightChip(rangeKey) {
  document.querySelectorAll('#bp-date-chips .bp-chip').forEach(btn => {
    btn.classList.toggle('is-active', btn.dataset.range === rangeKey);
  });
}

/**
 * 清除 chip 高亮（手动修改日期时调用）
 */
function _clearChipSelection() {
  document.querySelectorAll('#bp-date-chips .bp-chip').forEach(btn => {
    btn.classList.remove('is-active');
  });
}

// ---------------------------------------------------------------------------
// DOM 操作（页面加载时初始化）
// ---------------------------------------------------------------------------

/** 策略列表缓存（strategy_name → strategy 对象），供切换策略时查预设 */
let _strategiesCache = [];
/** 数据源缓存 */
let _dataSourcesCache = [];

/**
 * 保存表单状态到 localStorage
 */
function _saveFormState() {
  try {
    const state = {
      strategy: document.getElementById('bp-strategy')?.value || '',
      datasource: document.getElementById('bp-datasource')?.value || '',
      preset: document.getElementById('bp-preset')?.value || '',
      start: document.getElementById('bp-start')?.value || '',
      end: document.getElementById('bp-end')?.value || '',
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    log.debug('表单状态已保存', state);
  } catch (e) {
    log.warn('保存表单状态失败', e);
  }
}

/**
 * 恢复表单状态从 localStorage
 */
function _restoreFormState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const state = JSON.parse(raw);

    const strategyEl = document.getElementById('bp-strategy');
    const dsEl = document.getElementById('bp-datasource');
    const startEl = document.getElementById('bp-start');
    const endEl = document.getElementById('bp-end');

    if (state.strategy && strategyEl) strategyEl.value = state.strategy;
    if (state.datasource && dsEl) dsEl.value = state.datasource;
    if (state.start && startEl) startEl.value = state.start;
    if (state.end && endEl) endEl.value = state.end;

    // Trigger strategy change to update presets
    if (state.strategy) {
      _onStrategyChange({ target: strategyEl });
      if (state.preset) {
        const presetEl = document.getElementById('bp-preset');
        if (presetEl) presetEl.value = state.preset;
      }
    }

    // Trigger datasource change to update range hint (without overwriting dates)
    if (state.datasource && dsEl) {
      const [sym, frq] = (state.datasource || '').split('|');
      const src = _dataSourcesCache.find(s => s.symbol === sym && s.freq === frq);
      _updateDsRangeHint(src?.date_range || null);
    }

    log.info('表单状态已恢复', state);
  } catch (e) {
    log.warn('恢复表单状态失败', e);
  }
}

/**
 * 初始化"新建回测"面板
 * 从 /api/strategies 和 /api/data-sources 加载选项
 */
export async function initBacktestPanel() {
  const panel = document.getElementById('backtest-panel');
  if (!panel) return;

  log.info('初始化开始');

  // 并行加载策略和数据源
  const [strategiesOk, sourcesOk] = await Promise.all([
    _loadStrategies(),
    _loadDataSources(),
  ]);

  if (!strategiesOk) log.warn('策略列表加载失败，表单不可用');
  if (!sourcesOk) log.warn('数据源列表加载失败，表单不可用');

  // 策略切换 → 更新配置预设下拉
  const strategySelect = document.getElementById('bp-strategy');
  if (strategySelect) {
    strategySelect.addEventListener('change', _onStrategyChange);
  }

  // 数据源切换 → 自动填充日期 + 显示范围
  const dsSelect = document.getElementById('bp-datasource');
  if (dsSelect) {
    dsSelect.addEventListener('change', _onDataSourceChange);
  }

  // 日期快选 chips
  const chipsWrap = document.getElementById('bp-date-chips');
  if (chipsWrap) {
    chipsWrap.addEventListener('click', (e) => {
      const chip = e.target.closest('.bp-chip');
      if (chip?.dataset.range) _onChipClick(chip.dataset.range);
    });
  }

  // 手动修改日期 → 清除 chip 高亮
  const startInput = document.getElementById('bp-start');
  const endInput = document.getElementById('bp-end');
  if (startInput) startInput.addEventListener('change', _clearChipSelection);
  if (endInput) endInput.addEventListener('change', _clearChipSelection);

  // 表单提交
  const form = document.getElementById('bp-form');
  if (form) {
    form.addEventListener('submit', _onFormSubmit);
    // 表单变化时保存状态
    form.addEventListener('change', _saveFormState);
  }

  // 恢复上次填写的表单状态
  _restoreFormState();

  log.info('初始化完成');
}

async function _loadStrategies() {
  log.time('GET /api/strategies');
  try {
    const resp = await fetch('/api/strategies');
    if (!resp.ok) {
      log.error('GET /api/strategies 返回', resp.status);
      toast.error('策略列表加载失败', { detail: `HTTP ${resp.status}` });
      return false;
    }
    const data = await resp.json();
    _strategiesCache = data.strategies || [];
    _populateStrategySelect(_strategiesCache);
    log.timeEnd('GET /api/strategies');
    log.info('策略列表加载成功，共', _strategiesCache.length, '个');
    return true;
  } catch (e) {
    log.error('GET /api/strategies 异常', e);
    toast.error('策略列表加载失败', { detail: e.message });
    return false;
  }
}

async function _loadDataSources() {
  log.time('GET /api/data-sources');
  try {
    const resp = await fetch('/api/data-sources');
    if (!resp.ok) {
      log.error('GET /api/data-sources 返回', resp.status);
      toast.error('数据源列表加载失败', { detail: `HTTP ${resp.status}` });
      return false;
    }
    const data = await resp.json();
    _dataSourcesCache = data.data_sources || [];
    _populateDataSourceSelect(_dataSourcesCache);
    log.timeEnd('GET /api/data-sources');
    log.info('数据源加载成功，共', _dataSourcesCache.length, '个');
    return true;
  } catch (e) {
    log.error('GET /api/data-sources 异常', e);
    toast.error('数据源列表加载失败', { detail: e.message });
    return false;
  }
}

function _populateStrategySelect(strategies) {
  const sel = document.getElementById('bp-strategy');
  if (!sel) return;
  sel.innerHTML = '<option value="">-- 选择策略 --</option>' +
    strategies.map(s => {
      const label = s.type === 'llm' ? `${s.display_name} (LLM)` : s.display_name;
      return `<option value="${s.name}">${label}</option>`;
    }).join('');
}

function _populateDataSourceSelect(sources) {
  const sel = document.getElementById('bp-datasource');
  if (!sel) return;
  sel.innerHTML = '<option value="">-- 选择数据源 --</option>' +
    sources.map(s => {
      const range = s.date_range ? `(${s.date_range.start} ~ ${s.date_range.end})` : '';
      return `<option value="${s.symbol}|${s.freq}">${s.symbol} ${s.freq} ${range}</option>`;
    }).join('');
}

function _populatePresetSelect(presets) {
  const wrap = document.getElementById('bp-preset-wrap');
  const sel = document.getElementById('bp-preset');
  if (!sel) return;

  if (!presets || presets.length === 0) {
    // 无预设：隐藏整行
    if (wrap) wrap.style.display = 'none';
    sel.innerHTML = '';
    return;
  }

  if (wrap) wrap.style.display = '';
  sel.innerHTML = '<option value="">-- 默认参数 --</option>' +
    presets.map(p => `<option value="${p}">${p}</option>`).join('');
}

function _onStrategyChange(e) {
  const strategyName = e.target.value;
  const strategy = _strategiesCache.find(s => s.name === strategyName);

  // LLM 提示
  const note = strategy?.note || '';
  const noteEl = document.getElementById('bp-llm-note');
  if (noteEl) {
    noteEl.textContent = note;
    noteEl.style.display = note ? 'block' : 'none';
  }

  // 配置预设下拉
  _populatePresetSelect(strategy?.config_presets || []);

  log.info('策略切换 →', strategyName, '预设数量:', strategy?.config_presets?.length ?? 0);
}

/**
 * 数据源切换时自动填充日期范围 + 显示范围提示
 */
function _onDataSourceChange(e) {
  const dsVal = e.target.value;
  if (!dsVal) {
    _updateDsRangeHint(null);
    return;
  }

  const [symbol, freq] = dsVal.split('|');
  const source = _dataSourcesCache.find(s => s.symbol === symbol && s.freq === freq);

  _updateDsRangeHint(source?.date_range);

  if (source?.date_range) {
    const startEl = document.getElementById('bp-start');
    const endEl = document.getElementById('bp-end');
    // 始终填充：如果用户没手动改过就用数据源范围
    if (startEl) startEl.value = source.date_range.start;
    if (endEl) endEl.value = source.date_range.end;
    // 自动高亮"全部" chip
    _highlightChip('all');
    _saveFormState();
    log.info('数据源切换 → 自动填充日期', source.date_range);
  }
}

/**
 * 更新数据源范围提示文本
 */
function _updateDsRangeHint(dateRange) {
  const hintEl = document.getElementById('bp-ds-range');
  if (!hintEl) return;
  if (!dateRange) {
    hintEl.textContent = '';
    hintEl.style.display = 'none';
    return;
  }
  hintEl.textContent = `📅 ${dateRange.start} ~ ${dateRange.end}`;
  hintEl.style.display = 'block';
}

async function _onFormSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const strategyName = form.querySelector('#bp-strategy')?.value;
  const dsVal = form.querySelector('#bp-datasource')?.value || '';
  const [symbol, freq] = dsVal.split('|');
  const start = form.querySelector('#bp-start')?.value;
  const end = form.querySelector('#bp-end')?.value;
  const configName = form.querySelector('#bp-preset')?.value || null;

  // 前端必填校验
  _clearError();
  if (!strategyName) { _showError('请选择策略'); toast.warn('请选择策略'); return; }
  if (!symbol || !freq) { _showError('请选择数据源'); toast.warn('请选择数据源'); return; }
  if (!start) { _showError('请填写开始日期'); toast.warn('请填写开始日期'); return; }
  if (!end) { _showError('请填写结束日期'); toast.warn('请填写结束日期'); return; }
  if (start > end) { _showError('开始日期不能晚于结束日期'); toast.warn('开始日期不能晚于结束日期'); return; }

  const reqBody = buildRunRequest({ strategy_name: strategyName, symbol, freq, start, end, config_name: configName });
  log.info('提交回测请求', reqBody);

  _showProgress();
  toast.info('回测已提交，正在执行...', { detail: `${strategyName} ${symbol}/${freq}` });

  log.time('POST /api/runs');
  try {
    const resp = await fetch('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody),
    });
    log.timeEnd('POST /api/runs');
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      const msg = err.detail || `HTTP ${resp.status}`;
      log.error('POST /api/runs 失败', resp.status, err);
      _showError(msg);
      toast.error('回测提交失败', { detail: msg });
      return;
    }
    const { run_id } = await resp.json();
    log.info('run_id', run_id, '，开始 WebSocket 进度监听');
    _connectWebSocket(run_id, reqBody);
  } catch (err) {
    log.error('POST /api/runs 异常', err);
    _showError(String(err));
    toast.error('回测提交异常', { detail: err.message });
  }
}

function _connectWebSocket(runId, reqBody) {
  const wsParams = {
    strategy_name: reqBody.strategy_name,
    symbol: reqBody.symbol,
    freq: reqBody.freq,
    start: reqBody.start,
    end: reqBody.end,
  };
  if (reqBody.config_name) wsParams.config_name = reqBody.config_name;

  const url = buildWsUrl(runId, wsParams);
  log.info('WebSocket 连接', url);
  const ws = new WebSocket(url);

  // Connection timeout: abort if not connected within 10 s
  const CONNECT_TIMEOUT_MS = 10_000;
  const IDLE_TIMEOUT_MS = 60_000;
  let connectTimer = setTimeout(() => {
    if (ws.readyState === WebSocket.CONNECTING) {
      log.error('WebSocket 连接超时 (10s)');
      ws.close();
      _showError('WebSocket 连接超时，请检查后端服务');
      toast.error('WebSocket 连接超时', { detail: '请检查后端服务是否正常运行' });
    }
  }, CONNECT_TIMEOUT_MS);

  // Idle timeout: reset on every message
  let idleTimer = setTimeout(() => {
    log.error('WebSocket 无响应超时 (60s)');
    ws.close();
    _showError('回测无响应，请检查后端服务');
    toast.error('回测无响应', { detail: 'WebSocket 60秒无消息' });
  }, IDLE_TIMEOUT_MS);

  ws.onopen = () => {
    clearTimeout(connectTimer);
    log.info('WebSocket 已连接');
  };

  ws.onmessage = (event) => {
    // Reset idle timer on every message
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      log.error('WebSocket 无响应超时 (60s)');
      ws.close();
      _showError('回测无响应，请检查后端服务');
      toast.error('回测无响应', { detail: 'WebSocket 60秒无消息' });
    }, IDLE_TIMEOUT_MS);

    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch (e) {
      log.error('WS 消息解析失败', event.data, e);
      return;
    }
    log.debug('WS 消息', msg.status, msg);
    const result = handleWsMessage(msg);
    if (result.action === 'progress') {
      _updateProgress(result.payload);
    } else if (result.action === 'redirect') {
      clearTimeout(idleTimer);
      log.info('回测完成，跳转', result.payload);
      toast.success('回测完成！', { detail: `run_id: ${msg.run_id}` });
      setTimeout(() => { location.href = result.payload; }, 800);
    } else if (result.action === 'error') {
      clearTimeout(idleTimer);
      log.error('回测失败', result.payload);
      _showError(result.payload);
      toast.error('回测失败', { detail: result.payload });
    }
  };

  ws.onerror = (e) => {
    clearTimeout(connectTimer);
    clearTimeout(idleTimer);
    log.error('WebSocket 错误', e);
    _showError('WebSocket 连接失败');
    toast.error('WebSocket 连接失败');
  };

  ws.onclose = (e) => {
    clearTimeout(connectTimer);
    clearTimeout(idleTimer);
    log.info('WebSocket 关闭，code:', e.code, 'reason:', e.reason || '(none)');
  };
}

function _showProgress() {
  const progressEl = document.getElementById('bp-progress-area');
  const formEl = document.getElementById('bp-form');
  if (formEl) formEl.style.display = 'none';
  if (progressEl) progressEl.style.display = 'block';
}

function _updateProgress({ percent, current_date }) {
  const bar = document.getElementById('bp-progress-bar');
  const label = document.getElementById('bp-progress-label');
  if (bar) bar.style.width = `${percent}%`;
  if (label) label.textContent = `${percent}% — ${current_date}`;
}

function _clearError() {
  const errEl = document.getElementById('bp-error');
  if (errEl) {
    errEl.textContent = '';
    errEl.style.display = 'none';
  }
}

function _showError(msg) {
  const errEl = document.getElementById('bp-error');
  const progressEl = document.getElementById('bp-progress-area');
  const formEl = document.getElementById('bp-form');
  if (progressEl) progressEl.style.display = 'none';
  if (formEl) formEl.style.display = 'flex';
  if (errEl) {
    errEl.textContent = msg;
    errEl.style.display = 'block';
  }
}

/**
 * backtest-panel.js
 * 新建回测面板逻辑：纯函数 + DOM 操作
 *
 * 策略参数由服务端 configs/strategies/*.yaml 管理，前端只选配置预设名。
 */

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
// DOM 操作（页面加载时初始化）
// ---------------------------------------------------------------------------

/** 策略列表缓存（strategy_name → strategy 对象），供切换策略时查预设 */
let _strategiesCache = [];

/**
 * 初始化"新建回测"面板
 * 从 /api/strategies 和 /api/data-sources 加载选项
 */
export async function initBacktestPanel() {
  const panel = document.getElementById('backtest-panel');
  if (!panel) return;

  console.log('[BacktestPanel] 初始化开始');

  // 并行加载策略和数据源
  const [strategiesOk, sourcesOk] = await Promise.all([
    _loadStrategies(),
    _loadDataSources(),
  ]);

  if (!strategiesOk) console.warn('[BacktestPanel] 策略列表加载失败，表单不可用');
  if (!sourcesOk) console.warn('[BacktestPanel] 数据源列表加载失败，表单不可用');

  // 策略切换 → 更新配置预设下拉
  const strategySelect = document.getElementById('bp-strategy');
  if (strategySelect) {
    strategySelect.addEventListener('change', _onStrategyChange);
  }

  // 表单提交
  const form = document.getElementById('bp-form');
  if (form) {
    form.addEventListener('submit', _onFormSubmit);
  }

  console.log('[BacktestPanel] 初始化完成');
}

async function _loadStrategies() {
  try {
    const resp = await fetch('/api/strategies');
    if (!resp.ok) {
      console.error('[BacktestPanel] GET /api/strategies 返回', resp.status);
      return false;
    }
    const data = await resp.json();
    _strategiesCache = data.strategies || [];
    _populateStrategySelect(_strategiesCache);
    console.log('[BacktestPanel] 策略列表加载成功，共', _strategiesCache.length, '个');
    return true;
  } catch (e) {
    console.error('[BacktestPanel] GET /api/strategies 异常', e);
    return false;
  }
}

async function _loadDataSources() {
  try {
    const resp = await fetch('/api/data-sources');
    if (!resp.ok) {
      console.error('[BacktestPanel] GET /api/data-sources 返回', resp.status);
      return false;
    }
    const data = await resp.json();
    _populateDataSourceSelect(data.data_sources || []);
    console.log('[BacktestPanel] 数据源加载成功，共', (data.data_sources || []).length, '个');
    return true;
  } catch (e) {
    console.error('[BacktestPanel] GET /api/data-sources 异常', e);
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

  console.log('[BacktestPanel] 策略切换 →', strategyName,
    '预设数量:', strategy?.config_presets?.length ?? 0);
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
  if (!strategyName) { _showError('请选择策略'); return; }
  if (!symbol || !freq) { _showError('请选择数据源'); return; }
  if (!start) { _showError('请填写开始日期'); return; }
  if (!end) { _showError('请填写结束日期'); return; }
  if (start > end) { _showError('开始日期不能晚于结束日期'); return; }

  const reqBody = buildRunRequest({ strategy_name: strategyName, symbol, freq, start, end, config_name: configName });
  console.log('[BacktestPanel] 提交回测请求', reqBody);

  _showProgress();

  try {
    const resp = await fetch('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      const msg = err.detail || `HTTP ${resp.status}`;
      console.error('[BacktestPanel] POST /api/runs 失败', resp.status, err);
      _showError(msg);
      return;
    }
    const { run_id } = await resp.json();
    console.log('[BacktestPanel] run_id', run_id, '，开始 WebSocket 进度监听');
    _connectWebSocket(run_id, reqBody);
  } catch (err) {
    console.error('[BacktestPanel] POST /api/runs 异常', err);
    _showError(String(err));
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
  console.log('[BacktestPanel] WebSocket 连接', url);
  const ws = new WebSocket(url);

  // Connection timeout: abort if not connected within 10 s
  const CONNECT_TIMEOUT_MS = 10_000;
  const IDLE_TIMEOUT_MS = 60_000;
  let connectTimer = setTimeout(() => {
    if (ws.readyState === WebSocket.CONNECTING) {
      console.error('[BacktestPanel] WebSocket 连接超时');
      ws.close();
      _showError('WebSocket 连接超时，请检查后端服务');
    }
  }, CONNECT_TIMEOUT_MS);

  // Idle timeout: reset on every message
  let idleTimer = setTimeout(() => {
    console.error('[BacktestPanel] WebSocket 无响应超时');
    ws.close();
    _showError('回测无响应，请检查后端服务');
  }, IDLE_TIMEOUT_MS);

  ws.onopen = () => {
    clearTimeout(connectTimer);
    console.log('[BacktestPanel] WebSocket 已连接');
  };

  ws.onmessage = (event) => {
    // Reset idle timer on every message
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      console.error('[BacktestPanel] WebSocket 无响应超时');
      ws.close();
      _showError('回测无响应，请检查后端服务');
    }, IDLE_TIMEOUT_MS);

    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch (e) {
      console.error('[BacktestPanel] WS 消息解析失败', event.data, e);
      return;
    }
    console.log('[BacktestPanel] WS 消息', msg.status, msg);
    const result = handleWsMessage(msg);
    if (result.action === 'progress') {
      _updateProgress(result.payload);
    } else if (result.action === 'redirect') {
      clearTimeout(idleTimer);
      console.log('[BacktestPanel] 回测完成，跳转', result.payload);
      location.href = result.payload;
    } else if (result.action === 'error') {
      clearTimeout(idleTimer);
      console.error('[BacktestPanel] 回测失败', result.payload);
      _showError(result.payload);
    }
  };

  ws.onerror = (e) => {
    clearTimeout(connectTimer);
    clearTimeout(idleTimer);
    console.error('[BacktestPanel] WebSocket 错误', e);
    _showError('WebSocket 连接失败');
  };

  ws.onclose = (e) => {
    clearTimeout(connectTimer);
    clearTimeout(idleTimer);
    console.log('[BacktestPanel] WebSocket 关闭，code:', e.code);
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

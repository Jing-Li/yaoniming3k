/**
 * evolve-panel.js
 * Prompt 进化面板
 *
 * 功能：
 * - 进化配置（数据选择、代数、基础 Prompt）
 * - 提交进化任务 + WebSocket 进度
 * - 实时进化趋势图更新
 */

import { createLogger } from './logger.js';
import { toast } from './toast.js';
import { pageState } from './strategy-page.js';
import { addEvolveGeneration, showEvolveResults } from './optimize-charts.js';

const log = createLogger('EvolvePanel');

/** 当前 WebSocket 连接（防止重复提交导致泄漏） */
let _currentWs = null;

/**
 * 初始化进化面板
 */
export function initEvolvePanel(state) {
  // 数据源和日期已由 optimize-panel 初始化，这里只需绑定事件
  const form = document.getElementById('evo-form');
  if (form) {
    form.addEventListener('submit', handleEvolveSubmit);
  }
}

/**
 * 提交进化任务
 */
async function handleEvolveSubmit(e) {
  e.preventDefault();

  const symbol = document.getElementById('evo-symbol')?.value;
  const freq = document.getElementById('evo-freq')?.value;
  const start = document.getElementById('evo-start')?.value;
  const end = document.getElementById('evo-end')?.value;
  const maxGen = parseInt(document.getElementById('evo-generations')?.value || '5', 10);
  const basePrompt = document.getElementById('evo-base-prompt')?.value?.trim() || null;

  if (!symbol || !freq || !start || !end) {
    toast.warn('请填写完整的品种、频率和日期范围');
    return;
  }

  const body = {
    symbol, freq, start, end,
    max_generations: maxGen,
    base_prompt: basePrompt,
  };

  log.info('提交进化任务', body);

  const submitBtn = document.getElementById('evo-submit');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = '提交中...';
  }

  try {
    const res = await fetch('/api/prompt-evolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const { job_id } = await res.json();
    toast.success('进化任务已提交');
    connectEvolveWebSocket(job_id);

  } catch (err) {
    log.error('提交失败', { error: err.message });
    toast.error(`提交失败: ${err.message}`);
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = '开始进化';
    }
  }
}

/**
 * WebSocket 进度连接（进化）
 */
function connectEvolveWebSocket(jobId) {
  // 关闭旧连接
  if (_currentWs) {
    _currentWs.onmessage = null;
    _currentWs.close();
    _currentWs = null;
  }

  const progressEl = document.getElementById('evo-progress');
  const barEl = document.getElementById('evo-progress-bar');
  const pctEl = document.getElementById('evo-progress-pct');
  const infoEl = document.getElementById('evo-progress-info');

  if (progressEl) progressEl.style.display = '';

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${location.host}/ws/prompt-evolve/${jobId}/progress`;
  const ws = new WebSocket(wsUrl);
  _currentWs = ws;

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.status === 'running') {
      const pct = msg.total > 0 ? Math.round((msg.progress / msg.total) * 100) : 0;
      if (barEl) barEl.style.width = `${pct}%`;
      if (pctEl) pctEl.textContent = `${pct}%`;
      if (infoEl) infoEl.textContent = msg.message;
    }

    if (msg.status === 'done') {
      if (barEl) barEl.style.width = '100%';
      if (pctEl) pctEl.textContent = '100%';
      if (infoEl) infoEl.textContent = msg.message || '进化完成';
      toast.success('进化完成！');

      if (msg.results) {
        showEvolveResults(msg.results);
      }

      ws.close();
    }

    if (msg.status === 'error') {
      if (infoEl) infoEl.textContent = `错误: ${msg.message}`;
      toast.error(`进化失败: ${msg.message}`);
      ws.close();
    }
  };

  ws.onerror = () => {
    toast.error('WebSocket 连接失败');
    _currentWs = null;
  };
}

/**
 * Caisen — Toast 通知系统
 *
 * 用法:
 *   import { toast } from './toast.js';
 *   toast.success('回测完成！');
 *   toast.error('API 请求失败: 500');
 *   toast.info('正在加载数据...');
 *   toast.warn('数据可能不完整');
 *
 * 自动消失（默认 4 秒），error 类型持续 8 秒。
 * 可手动点击关闭。
 */

const ICONS = {
    success: '✅',
    error: '❌',
    warn: '⚠️',
    info: 'ℹ️',
};

const DURATIONS = {
    success: 4000,
    error: 8000,
    warn: 5000,
    info: 4000,
};

let _container = null;

/**
 * 获取或创建 Toast 容器
 */
function getContainer() {
    if (_container && document.body.contains(_container)) return _container;
    _container = document.createElement('div');
    _container.className = 'toast-container';
    _container.setAttribute('aria-live', 'polite');
    _container.setAttribute('aria-relevant', 'additions');
    document.body.appendChild(_container);
    return _container;
}

/**
 * 显示 Toast 通知
 * @param {string} message - 通知文本
 * @param {'success'|'error'|'warn'|'info'} type - 类型
 * @param {Object} [opts] - 选项
 * @param {number} [opts.duration] - 持续时间 ms
 * @param {string} [opts.detail] - 附加详情（小字显示）
 */
function show(message, type = 'info', opts = {}) {
    const container = getContainer();
    const duration = opts.duration ?? DURATIONS[type] ?? 4000;

    const el = document.createElement('div');
    el.className = `toast toast--${type}`;
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');

    const icon = ICONS[type] || ICONS.info;
    const detailHtml = opts.detail
        ? `<div class="toast__detail">${opts.detail}</div>`
        : '';

    el.innerHTML = `
        <span class="toast__icon" aria-hidden="true">${icon}</span>
        <div class="toast__body">
            <div class="toast__message"></div>
            ${detailHtml}
        </div>
        <button class="toast__close" aria-label="关闭通知" title="关闭">&times;</button>
    `;

    // 安全设置 message（防 XSS）
    el.querySelector('.toast__message').textContent = message;
    if (opts.detail) {
        el.querySelector('.toast__detail').textContent = opts.detail;
    }

    // 关闭按钮
    el.querySelector('.toast__close').addEventListener('click', () => dismiss(el));

    // 入场动画
    container.appendChild(el);
    requestAnimationFrame(() => el.classList.add('toast--visible'));

    // 自动消失
    const timer = setTimeout(() => dismiss(el), duration);

    // 悬停暂停
    el.addEventListener('mouseenter', () => clearTimeout(timer));
    el.addEventListener('mouseleave', () => setTimeout(() => dismiss(el), 1500));

    return el;
}

/**
 * 移除 Toast（带退场动画）
 */
function dismiss(el) {
    if (!el || !el.parentNode) return;
    el.classList.add('toast--dismiss');
    el.addEventListener('animationend', () => el.remove(), { once: true });
    // Fallback removal
    setTimeout(() => { if (el.parentNode) el.remove(); }, 500);
}

/**
 * 便捷 API
 */
export const toast = {
    success: (msg, opts) => show(msg, 'success', opts),
    error: (msg, opts) => show(msg, 'error', opts),
    warn: (msg, opts) => show(msg, 'warn', opts),
    info: (msg, opts) => show(msg, 'info', opts),
};

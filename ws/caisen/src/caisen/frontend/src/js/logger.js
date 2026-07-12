/**
 * Caisen — 结构化日志模块
 *
 * 用法:
 *   import { createLogger } from './logger.js';
 *   const log = createLogger('DataLoader');
 *   log.info('加载完成', { runId, bars: 250 });
 *   log.warn('缓存过期');
 *   log.error('API 失败', { status: 500, url: '/api/runs' });
 *
 * 日志格式:  [LEVEL] HH:MM:SS.mmm [Module] message {context}
 * 所有日志始终输出（不再受 DEV 开关限制），方便线上排查。
 * 可通过 URL 参数 ?log=warn 动态过滤级别。
 */

const LEVELS = { debug: 0, info: 1, warn: 2, error: 3 };

/**
 * 从 URL 参数获取当前日志级别（默认 info）
 */
function getLevelFromUrl() {
    try {
        const params = new URLSearchParams(window.location.search);
        const level = params.get('log');
        return level && LEVELS[level] !== undefined ? level : 'info';
    } catch {
        return 'info';
    }
}

/**
 * 格式化时间戳为 HH:MM:SS.mmm
 */
function fmtTime() {
    const d = new Date();
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}.${String(d.getMilliseconds()).padStart(3, '0')}`;
}

/**
 * 创建带模块标签的 logger 实例
 * @param {string} module - 模块名称（如 'DataLoader', 'BacktestPanel'）
 * @returns {{ debug: Function, info: Function, warn: Function, error: Function, time: Function, timeEnd: Function }}
 */
export function createLogger(module) {
    const tag = `[${module}]`;

    function shouldLog(level) {
        const threshold = getLevelFromUrl();
        return LEVELS[level] >= LEVELS[threshold];
    }

    function fmtArgs(args) {
        // Separate objects from primitives for cleaner output
        const parts = [];
        for (const a of args) {
            if (a instanceof Error) {
                parts.push(a.message);
                if (a.stack) parts.push('\n' + a.stack);
            } else if (typeof a === 'object' && a !== null) {
                try { parts.push(JSON.stringify(a)); } catch { parts.push(String(a)); }
            } else {
                parts.push(String(a));
            }
        }
        return parts.join(' ');
    }

    const timers = new Map();

    return {
        debug(...args) {
            if (shouldLog('debug')) {
                console.debug(`[DBG] ${fmtTime()} ${tag}`, ...args);
            }
        },

        info(...args) {
            if (shouldLog('info')) {
                console.log(`[INF] ${fmtTime()} ${tag}`, ...args);
            }
        },

        warn(...args) {
            if (shouldLog('warn')) {
                console.warn(`[WRN] ${fmtTime()} ${tag}`, ...args);
            }
        },

        error(...args) {
            if (shouldLog('error')) {
                console.error(`[ERR] ${fmtTime()} ${tag}`, ...args);
            }
        },

        /**
         * 计时器 — 用于测量 API 调用等操作耗时
         * @param {string} label
         */
        time(label) {
            timers.set(label, performance.now());
        },

        /**
         * 结束计时并输出日志
         * @param {string} label
         * @returns {number} 耗时毫秒数
         */
        timeEnd(label) {
            const start = timers.get(label);
            if (start === undefined) return 0;
            timers.delete(label);
            const ms = Math.round(performance.now() - start);
            this.info(`${label} — ${ms}ms`);
            return ms;
        },
    };
}

/**
 * 全局未捕获错误处理器 — 确保生产环境也能看到错误
 */
export function setupGlobalErrorHandlers() {
    window.addEventListener('error', (e) => {
        console.error(`[ERR] ${fmtTime()} [Global] Uncaught:`, e.message, 'at', e.filename, `${e.lineno}:${e.colno}`);
        if (e.error?.stack) console.error(e.error.stack);
    });

    window.addEventListener('unhandledrejection', (e) => {
        console.error(`[ERR] ${fmtTime()} [Global] Unhandled rejection:`, e.reason);
    });
}

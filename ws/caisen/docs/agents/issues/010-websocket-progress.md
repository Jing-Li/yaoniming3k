# WebSocket 进度端点 `/ws/runs/{run_id}/progress`

- **ID**: 010
- **标签**: enhancement, closed
- **优先级**: HIGH
- **状态**: closed (2026-05-26)

## Parent

[#004 PRD: 前端触发回测 + 项目全局配置](004-frontend-backtest-trigger.md)

## What to build

在 Web 服务中新增 WebSocket 端点 `WS /ws/runs/{run_id}/progress`，将 `BacktestRunner` 的进度回调桥接为 WebSocket 消息推送。

客户端连接后，后端在独立线程中运行回测，每 100 根 K 线通过 WebSocket 推送进度消息，完成或出错后推送终态消息并关闭连接。

消息协议（JSON）：

```json
// 进度消息
{"status": "running", "processed": 300, "total": 1200, "current_date": "2024-03-15"}

// 完成消息
{"status": "done", "run_id": "CaiSenStrategy_20240526_001"}

// 错误消息
{"status": "error", "message": "数据不足，无法运行回测"}
```

`run_id` 在 WebSocket 连接建立时由客户端指定（由 `POST /api/runs` 预先创建）。

## Acceptance criteria

- [x] `WS /ws/runs/{run_id}/progress` 端点存在
- [x] 客户端连接后收到至少一条 `running` 消息（总 K 线数 > 100 时）
- [x] 回测完成后收到 `done` 消息并携带有效 `run_id`
- [x] 回测出错后收到 `error` 消息并携带错误描述
- [x] 连接在终态消息发送后自动关闭
- [x] `websockets` 依赖已添加到 `pyproject.toml`

## Blocked by

- [#009 BacktestRunner：带进度回调的回测执行模块](009-backtest-runner.md)

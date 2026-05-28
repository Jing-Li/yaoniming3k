# POST /api/runs：同步触发回测端点

- **ID**: 011
- **标签**: enhancement, closed
- **优先级**: HIGH
- **状态**: closed (2026-05-26)

## Parent

[#004 PRD: 前端触发回测 + 项目全局配置](004-frontend-backtest-trigger.md)

## What to build

在 Web 服务中新增 `POST /api/runs` 端点，接收回测参数，预分配 `run_id`，然后异步在后台执行回测（与 WebSocket 进度端点配合使用）。

请求体（JSON）：
```json
{
  "strategy_name": "CaiSenStrategy",
  "symbol": "000001.SZ",
  "freq": "1d",
  "start": "2023-01-01",
  "end": "2024-12-31",
  "params": {
    "stop_loss_factor": 0.95
  }
}
```

成功响应（202 Accepted）：
```json
{
  "run_id": "CaiSenStrategy_20240526_001"
}
```

端点立即返回 `run_id`，实际回测在后台线程执行。前端用 `run_id` 连接 WebSocket 监听进度。参数校验失败返回 422。

## Acceptance criteria

- [x] `POST /api/runs` 端点存在，接受上述请求体
- [x] 参数合法时立即返回 202 + `{run_id}`
- [x] `strategy_name` 不在已注册策略列表中时返回 422
- [ ] `symbol`/`freq` 不存在对应本地数据时返回 422（由后台线程静默处理，WS 下发错误）
- [x] 日期格式错误时返回 422
- [x] 返回的 `run_id` 可用于连接 `WS /ws/runs/{run_id}/progress`
- [x] 集成测试使用 FastAPI TestClient 验证 202 响应和 422 场景

## Blocked by

- [#009 BacktestRunner：带进度回调的回测执行模块](009-backtest-runner.md)

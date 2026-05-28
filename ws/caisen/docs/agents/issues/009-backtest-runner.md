# BacktestRunner：带进度回调的回测执行模块

- **ID**: 009
- **标签**: enhancement, closed
- **优先级**: HIGH
- **状态**: closed (2026-05-26)

## Parent

[#004 PRD: 前端触发回测 + 项目全局配置](004-frontend-backtest-trigger.md)

## What to build

新建 `BacktestRunner` 模块，封装"加载行情数据 → 实例化策略 → 运行 BacktestEngine → 持久化结果"的完整流程，并通过进度回调（每 100 根 K 线触发一次）向外暴露执行进度。

`BacktestRunner` 与 WebSocket/HTTP 层完全解耦：调用方传入一个 `on_progress` 回调函数，`BacktestRunner` 只负责调用回调，不关心传输协议。

接口约定：

```python
# 进度回调签名
on_progress(processed: int, total: int, current_date: str) -> None

# 运行接口
run_backtest(
    strategy_name: str,
    symbol: str,
    freq: str,
    start: str,
    end: str,
    params: dict,
    on_progress: Callable | None = None,
) -> str  # 返回 run_id
```

数据不足（K 线数为 0）时抛出明确异常，不静默失败。

## Acceptance criteria

- [x] `BacktestRunner` 模块存在，`run_backtest()` 接口符合约定签名
- [x] 使用 mock bars 数据可完成端到端回测并返回有效 `run_id`
- [x] `on_progress` 回调每 100 根 K 线被调用一次（最后不足 100 根时也调用一次）；BacktestEngine.run() 加了可选 `on_bar` 钩子
- [x] 数据不足（K 线数为 0）时抛出 `BacktestError("数据为空")`
- [x] 策略名不存在时抛出 `BacktestError("策略不存在")`
- [x] 使用 `ProjectConfig` 读取 `data_dir` 和 `output_dir`（不硬编码）
- [x] 4 个单元测试，全部通过

## Blocked by

- [#005 ProjectConfig：全局配置加载模块](005-project-config.md)
- [#007 DataSourceScanner](007-data-source-scanner.md)
- [#008 StrategyRegistry](008-strategy-registry.md)

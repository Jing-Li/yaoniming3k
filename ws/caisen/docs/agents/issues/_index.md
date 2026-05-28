# Issue Index

## Open

*（暂无 open issues）*

## Closed

| ID | Title | Tags | Resolution |
|----|-------|------|------------|
| 001 | Frontend CSS 结构与 CONTEXT.md 不一致 | doc-sync, enhancement, wontfix | ADR-0010 已覆盖，domain-only 原则下无需文档同步 |
| 002 | 早期 ADR 格式不完整 | doc-sync, enhancement, wontfix | 内容清晰可读，补格式收益低，修订时顺便处理 |
| 003 | 前端测试 stubs 引用不存在的 exports | doc-sync, bug, closed | 重写测试文件匹配当前模块导出，28 tests 全部通过 |
| 004 | PRD：前端触发回测 + 项目全局配置 | enhancement, closed | 所有子 issue (#005–#012) 全部交付，PRD 完成 |
| 005 | ProjectConfig：全局配置加载模块 | enhancement, closed | TDD 完成：3 tests GREEN，集成到 web/main.py、cli/main.py、llm_backtest.py，创建 configs/project.yaml |
| 006 | configs 目录重组：策略 YAML 迁移 | enhancement, closed | 7 个策略 YAML 移至 configs/strategies/，CONTEXT.md 已更新，265 tests passed |
| 007 | DataSourceScanner：数据目录扫描 + `/api/data-sources` | enhancement, closed | TDD 完成：4 tests GREEN，文件名格式 YYYYMMDD_YYYYMMDD，端点集成 ProjectConfig |
| 008 | StrategyRegistry：策略注册表 + `/api/strategies` | enhancement, closed | TDD 完成：4 tests GREEN，顺带修复 ma_cross.py 导入 bug，端点已上线 |
| 009 | BacktestRunner：带进度回调的回测执行模块 | enhancement, closed | TDD 完成：4 tests GREEN，BacktestEngine.run() 加 on_bar 钩子，BacktestError 明确异常，277 tests passed |
| 010 | WebSocket 进度端点 `/ws/runs/{run_id}/progress` | enhancement, closed | TDD 完成：4 tests GREEN，queue 桥接 on_progress 回调，done/error 终态关闭连接，285 tests passed |
| 011 | POST /api/runs：同步触发回测端点 | enhancement, closed | TDD 完成：4 tests GREEN，Pydantic 校验日期格式，策略注册表同步校验，threading.Thread 后台执行，281 tests passed |
| 012 | 前端"新建回测"面板 + WebSocket 客户端 | enhancement, closed | TDD 完成：9 JS tests GREEN，backtest-panel.js 纯函数，index.html 面板并列布局，Vite build 通过，46 JS + 285 Python tests passed |

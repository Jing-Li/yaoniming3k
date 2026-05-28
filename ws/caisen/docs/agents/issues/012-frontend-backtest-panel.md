# 前端"新建回测"面板 + WebSocket 客户端

- **ID**: 012
- **标签**: enhancement, closed
- **优先级**: HIGH
- **状态**: closed (2026-05-26)

## Parent

[#004 PRD: 前端触发回测 + 项目全局配置](004-frontend-backtest-trigger.md)

## What to build

在 `index.html` 入口页新增"新建回测"面板，与现有 runs 列表并列。面板包含完整的回测发起表单和 WebSocket 进度展示区。

**表单交互流程：**

1. 页面加载时调用 `GET /api/strategies` 和 `GET /api/data-sources` 初始化下拉选项
2. 用户选择策略后，根据 `params_schema` 动态渲染参数表单（数字输入框、开关、下拉等）
3. 用户填写 symbol、freq、start、end、params 后点击"开始回测"
4. 前端调用 `POST /api/runs` 获取 `run_id`
5. 前端建立 WebSocket 连接 `WS /ws/runs/{run_id}/progress`，展示实时进度条和当前处理日期
6. 收到 `done` 消息后自动跳转 `report.html?run_id=xxx`
7. 收到 `error` 消息后在面板内展示错误信息（红色提示框）

**LLM 策略特殊处理：** 选中后在参数区显示提示"此策略需要服务器端预先配置 API Key"。

面板使用现有 CSS 设计系统（`variables.css`、`components.css`），风格与现有 runs 列表一致。

## Acceptance criteria

- [x] `index.html` 中存在"新建回测"面板，与 runs 列表并列显示
- [x] 策略下拉从 `/api/strategies` 加载，区分 code/llm 类型
- [x] 数据源下拉从 `/api/data-sources` 加载，显示 symbol + freq 组合
- [x] 选择策略后动态渲染对应参数表单（支持 float/int/bool/select 四种输入类型）
- [x] 点击"开始回测"后进度条可见，显示百分比和当前处理日期
- [x] 回测完成后自动跳转 `report.html?run_id=xxx`
- [x] 回测出错时面板内显示明确错误信息，不跳转
- [x] LLM 策略选中时展示 API Key 配置提示
- [x] 面板样式与现有 UI 设计系统一致（使用 CSS 变量）
- [x] 前端 Vite 构建通过（`npm run build`）

## Blocked by

- [#007 DataSourceScanner](007-data-source-scanner.md)
- [#008 StrategyRegistry](008-strategy-registry.md)
- [#010 WebSocket 进度端点](010-websocket-progress.md)
- [#011 POST /api/runs 端点](011-post-runs-endpoint.md)

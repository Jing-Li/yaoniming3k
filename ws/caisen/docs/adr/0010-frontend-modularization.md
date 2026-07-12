# ADR-0010: 前端模块化重构

## Status
Implemented

## Context

原 `src/caisen/visualization/index.html` 单文件实现（1245 行）已完成模块化重构，迁移至 `src/caisen/frontend/`。

### 已解决的问题

1. **单文件过长** → 拆分为 26 个 JS 模块
2. **模块边界不清** → 按职责分离到独立文件
3. **测试缺失** → Vitest 单元测试 + Playwright E2E
4. **构建工具** → Vite 开发服务器 + 生产构建

### 约束（保持）

- 保持纯 HTML + JS（无框架），Vite 构建
- JSON 数据文件作为数据传递格式
- ECharts 作为图表库

## Decision

### 1. 目录结构

```
src/caisen/frontend/
├── index.html              # 入口（runs 列表）
├── report.html             # K线图详情页
├── strategy.html           # 策略中心页
├── package.json            # npm 依赖
├── vite.config.js          # Vite 配置
├── src/
│   ├── js/                 # 26 个 JS 模块
│   │   ├── app.js          # 主应用入口
│   │   ├── data-loader.js  # 数据加载
│   │   ├── kline-chart.js  # K线图
│   │   ├── equity-chart.js # 权益曲线
│   │   ├── drawdown-chart.js # 回撤图
│   │   ├── heatmap.js      # 月度收益热力图
│   │   ├── annotation-renderer.js # 标注渲染
│   │   ├── annotation-filter.js   # 标注过滤
│   │   ├── backtest-panel.js      # 回测面板
│   │   ├── optimize-panel.js      # 优化面板
│   │   ├── evolve-panel.js        # 进化面板
│   │   ├── toast.js               # Toast 通知
│   │   ├── logger.js              # 日志系统
│   │   └── ...                    # 其他模块
│   └── css/                # CSS 样式
│       ├── variables.css   # CSS 变量
│       ├── reset.css       # 样式重置
│       ├── layout.css      # 布局
│       ├── components.css  # 组件
│       ├── pages.css       # 页面
│       └── main.css        # 统一入口
├── tests/                  # Vitest 单元测试
└── e2e/                    # Playwright E2E 测试
```

### 2. 页面结构

| 页面 | 文件 | 功能 |
|------|------|------|
| 首页 | index.html | 回测报告列表、策略选择 |
| 报告页 | report.html | K线图 + 权益曲线 + 交易表 |
| 策略中心 | strategy.html | 优化/进化/对比面板 |

### 3. 打包策略

采用 **Vite** 构建：
- 开发时：`vite dev` 启动开发服务器（端口 5173）
- 生产时：`vite build` 生成静态资源到 `dist/`

### 4. 类型化（可选）

添加 JSDoc 类型注释，渐进式增强类型安全：
- Annotation 类型定义
- Data 结构类型

## Consequences

### Positive
- 模块边界清晰，26 个独立 JS 模块按职责分离
- 渲染逻辑与图表逻辑分离
- Vitest 单元测试 + Playwright E2E 测试覆盖
- Vite 热更新提升开发效率
- 团队协作更容易（多人可同时修改不同模块）

### Negative
- 引入构建工具（Vite），增加复杂度
- 需要处理模块化后的代码分割

### Risks
- 拆分过程中可能引入 bug
- Vite 配置需要额外学习

## References
- ADR-0007: 可视化报告架构
- index.html 当前实现（1245 行）
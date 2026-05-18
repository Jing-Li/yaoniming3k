# ADR-0010: 前端模块化重构

## Status
Proposed

## Context

当前 `src/caisen/visualization/index.html` 是单文件实现（1245 行），包含 CSS、HTML 模板和 JavaScript 逻辑混在一起。随着 Annotation 类型增加（已达 12 种），维护成本上升。

### 问题

1. **单文件过长**：1245 行导致定位和修改困难
2. **模块边界不清**：renderMap、图表初始化、数据加载混在一起
3. **测试缺失**：纯 JS 无测试覆盖
4. **类型安全不足**：无 TypeScript

### 约束

- 保持纯 HTML + JS（无框架），便于直接浏览器打开
- JSON 数据文件作为数据传递格式（ADR-0007 已定义）
- ECharts 作为图表库

## Decision

### 1. 目录结构

```
src/caisen/visualization/
├── index.html          # 入口文件，组装各模块
├── styles/
│   └── main.css        # 样式（从 index.html 提取）
├── modules/
│   ├── chart.js        # 图表初始化、配置
│   ├── annotation.js   # renderMap、标注渲染逻辑
│   ├── data.js         # 数据加载、解析
│   └── utils.js        # 工具函数（findBarByTimestamp 等）
└── sample/
    └── data.json       # 示例数据
```

### 2. 模块职责

| 模块 | 职责 | 导出 |
|------|------|------|
| `chart.js` | ECharts 实例管理、配置、K线图/净值图初始化 | `initKLineChart()`, `initEquityChart()` |
| `annotation.js` | renderMap、标注类型渲染器 | `renderAnnotations()`, `renderMap` |
| `data.js` | loadData、getDataUrl、applyDateFilter | `loadData()`, `DataLoader` |
| `utils.js` | findBarByTimestamp、格式化函数 | `findBarByTimestamp()` |

### 3. 打包策略

采用 **Vite** 构建：
- 开发时：`vite dev` 启动开发服务器
- 生产时：`vite build` 生成单文件 HTML（或多个小文件）
- 保持 `dist/` 输出与现在 `index.html` 功能等价

### 4. 类型化（可选）

添加 JSDoc 类型注释，渐进式增强类型安全：
- Annotation 类型定义
- Data 结构类型

## Consequences

### Positive
- 模块边界清晰，便于维护
- 渲染逻辑与图表逻辑分离
- 便于添加测试
- 团队协作更容易（多人可同时修改不同模块）

### Negative
- 引入构建工具（Vite），增加复杂度
- 需要处理模块化后的代码分割
- 过渡期需要同时维护单文件和模块化版本

### Risks
- 拆分过程中可能引入 bug
- Vite 配置需要额外学习

## References
- ADR-0007: 可视化报告架构
- index.html 当前实现（1245 行）
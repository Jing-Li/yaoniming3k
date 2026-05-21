# ADR-0007: 可视化报告架构

## Status
Accepted

## Context

回测系统需要生成可视化报告，展示策略执行结果。报告包含：
- K 线图
- 净值曲线
- 交易标注
- 策略绘制的形态标记

### 技术选型背景

1. **Plotly vs 纯 HTML+JS**
   - Plotly 包大（1-5MB），依赖重
   - 纯 HTML+JS 轻量，可完全定制
   - 选择：纯 HTML+JS

2. **数据传递方式**
   - 内嵌 HTML：数据量大时不灵活
   - API 服务：增加复杂度
   - 选择：JSON 文件

3. **Python/前端职责**
   - Python 只负责生成数据
   - 前端完全控制渲染
   - 便于前后端独立迭代

4. **前端架构**
   - SPA vs MPA：选择 MPA，两个独立 HTML 文件
   - JS 模块化：保持现有 10 个模块划分
   - CSS 组织：拆分为独立文件
   - 构建工具：使用 Vite
   - ECharts：通过 npm 安装，Vite 打包

## Decision

### 1. 目录结构

#### 前端子目录（frontend/）

```
frontend/
├── index.html                    # 主页（runs 列表）
├── report.html                   # 详情页（K线图）
├── package.json                  # npm 依赖
├── vite.config.js                # Vite 配置
├── src/
│   ├── js/                       # JS 模块
│   │   ├── constants.js          # 主题颜色、间距常量
│   │   ├── app-state.js          # 全局状态
│   │   ├── utils.js              # 纯工具函数
│   │   ├── data-loader.js        # API 数据加载
│   │   ├── chart-builder.js      # ECharts 配置构建
│   │   ├── annotation-renderer.js # 标注渲染
│   │   ├── chart-renderer.js     # 图表渲染
│   │   ├── components.js         # UI 组件
│   │   ├── runs-list.js          # runs 列表逻辑
│   │   └── main.js               # 入口点
│   └── css/                      # CSS 文件
│       ├── variables.css         # CSS 变量
│       ├── reset.css             # 样式重置
│       ├── layout.css            # 布局
│       ├── components.css        # 组件样式
│       └── pages.css            # 页面特定样式
├── e2e/                          # Playwright E2E 测试
└── tests/js/                     # Vitest 单元测试
```

#### 回测结果目录

```
./runs/{run_id}/
├── meta.json          # 元数据（策略名、时间等）
├── equity.parquet     # 净值曲线（Parquet 格式，高效存储）
├── trades.parquet     # 交易记录（Parquet 格式）
├── annotations.json   # 可视化标注
└── metrics.json       # 绩效指标
```

前端可视化需要 `data.json`（包含 bars + equity_curve + trades + annotations + metrics），由后端命令生成。

### 2. 可视化报告生成

使用 `caisen web <run_id>` 命令启动可视化服务：

```
./runs/{run_id}/
├── data.json          # 可视化专用综合数据文件
└── [其他回测数据文件]
```

#### data.json 结构

```json
{
  "meta": {
    "strategy_name": "MACrossStrategy",
    "symbol": "ag",
    "start": "2026-01-01",
    "end": "2026-05-15",
    "freq": "1h"
  },
  "metrics": {
    "total_return": 0.0844,
    "max_drawdown": 0.3002,
    "sharpe_ratio": 0.23,
    "win_rate": 0.333,
    "profit_factor": 1.21
  },
  "bars": [
    {"timestamp": "...", "open": 20000, "high": 20100, "low": 19900, "close": 20050, "volume": 1000}
  ],
  "equity_curve": [
    {"timestamp": "...", "equity": 100000, "cash": 90000}
  ],
  "trades": [
    {"timestamp": "...", "side": "BUY", "price": 20000, "quantity": 5, "commission": 30}
  ],
  "annotations": [
    {"type": "buy_signal", "timestamp": "...", "data": {"price": 20000, "label": "MA金叉", "color": "green"}}
  ]
}
```

#### CLI 命令

```bash
# 启动可视化 Web 服务（浏览器访问）
caisen web --port 8000

# 绑定所有网卡（局域网访问）
caisen web --host 0.0.0.0 --port 8000

# 直接打开指定回测结果
caisen web --run-id MACrossStrategy_20260518_1 --port 8000
```

### 3. 源码目录结构

```
src/caisen/
├── frontend/                    # 前端（HTML, CSS, JS, Vite）
│   ├── index.html
│   ├── report.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── js/
│       └── css/
├── web/                         # FastAPI 服务
│   └── main.py
└── ...                          # 其他后端模块
```

### 4. Web 服务架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│   FastAPI   │────▶│  ./runs/    │
│   (HTML)    │◀────│   Server   │◀────│  data.json  │
└─────────────┘     └─────────────┘     └─────────────┘
```

#### API 端点

| 端点 | 说明 |
|------|------|
| `GET /` | 前端入口页面（index.html） |
| `GET /report.html` | 回测详情页面 |
| `GET /api/runs` | 列出所有回测结果（含摘要 metrics） |
| `GET /api/runs/{run_id}` | 获取回测详情 |
| `GET /api/runs/{run_id}/visualization` | 获取可视化数据 |
| `GET /api/runs/{run_id}/data.json` | 直接获取 data.json |
| `GET /health` | 健康检查 |

#### /api/runs 返回结构

```json
{
  "runs": [
    {
      "run_id": "MACrossStrategy_20260518_1",
      "strategy_name": "MACrossStrategy",
      "symbol": "ag",
      "start_date": "2026-01-01",
      "end_date": "2026-05-15",
      "freq": "60m",
      "created_at": "2026-05-18T10:30:00",
      "metrics": {
        "total_return": 0.0844,
        "max_drawdown": 0.3002
      }
    }
  ],
  "total": 26
}
```

#### 前端访问模式

1. **API 模式**：`http://host:port/report.html?run_id={run_id}` → 前端从 `/api/runs/{run_id}/visualization` 获取数据
2. **文件模式**：直接打开 `report.html`（离线使用），从相对路径 `./data.json` 加载数据

### 5. Annotation 接口约定

#### 通用字段
- `type`: AnnotationType 枚举值
- `timestamp`: 主时间点
- `data`: 类型相关数据

#### 类型约定

| type | data 字段 | 说明 |
|------|----------|------|
| `buy_signal` | `price`, `label`, `color` | 买入信号，绿色向上三角 |
| `sell_signal` | `price`, `label`, `color` | 卖出信号，红色向下三角 |
| `neutral_signal` | `price`, `label`, `color` | 中性信号，灰色菱形 |
| `pattern_mark` | `pattern`, `points`, `neckline`, `label`, `color` | 形态标注（头肩底、W底等） |
| `horizontal_line` | `price`, `label`, `color` | 水平线 |
| `trend_line` | `start`, `end`, `label`, `color` | 趋势线（起点+终点） |
| `support_zone` | `price`, `label`, `color` | 支撑区，绿色虚线 |
| `resistance_zone` | `price`, `label`, `color` | 阻力区，红色虚线 |
| `volume_spike` | `timestamp`, `data` | 成交量突增标记（由成交量系列处理） |
| `text_label` | `text`, `price`, `color` | 文本标注 |
| `rectangle` | `start`, `end`, `color` | 矩形区间（起点+终点） |
| `polygon` | `points`, `label`, `color` | 多边形（多点连线） |

#### pattern_mark 完整结构

```json
{
  "type": "pattern_mark",
  "timestamp": "2024-01-15T10:00:00",
  "data": {
    "pattern": "head_and_shoulders_bottom",
    "points": [
      {"timestamp": "2024-01-10", "price": 100, "label": "左肩"},
      {"timestamp": "2024-01-12", "price": 95, "label": "头"},
      {"timestamp": "2024-01-14", "price": 100, "label": "右肩"}
    ],
    "neckline": {
      "start": "2024-01-10",
      "end": "2024-01-14",
      "price": 100
    },
    "label": "头肩底形态",
    "color": "purple"
  }
}
```

### 6. 技术栈

- **图表库**: ECharts 5.x（通过 npm 安装，Vite 打包）
- **构建工具**: Vite
- **前端**: HTML + CSS + JS（纯 JavaScript，无 TypeScript）
- **测试**: Vitest（单元测试）+ Playwright（E2E 测试）
- **Python**: FastAPI 服务，生成 JSON 数据

### 7. 渲染规则

前端按 `annotation.type` 查找 renderMap，决定渲染方式：

```javascript
const renderMap = {
  'buy_signal': (ctx, annotation) => { /* 绿色三角 */ },
  'sell_signal': (ctx, annotation) => { /* 红色三角 */ },
  'pattern_mark': (ctx, annotation) => { /* 形态连线 */ },
  'horizontal_line': (ctx, annotation) => { /* 水平线 */ },
  // ...
};
```

### 8. 测试策略

- **单元测试**（Vitest）：覆盖纯函数逻辑（utils.js, annotation-renderer.js, chart-config.js）
- **E2E 测试**（Playwright）：测试页面加载、API 调用、图表渲染
- **本地验证**：手动验证，无 GitHub Actions CI

## Consequences

### Positive
- 前后端解耦，可独立迭代
- JSON 格式便于调试和扩展
- 轻量 HTML 文件，易于分享
- Vite 提供快速开发和优化构建
- E2E 测试保证页面功能正常
- 离线模式支持直接打开 HTML 文件

### Negative
- 前端需要单独管理 npm 依赖
- 需要维护渲染规则映射表
- 两个 HTML 文件需要同步更新基础样式

## References
- Annotation 类型定义: `src/caisen/strategy/base.py`
- BacktestResult 数据结构: `src/caisen/core/engine.py`
- 前端代码: `src/caisen/frontend/`
- Web 服务: `src/caisen/web/`
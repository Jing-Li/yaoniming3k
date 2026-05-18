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

## Decision

### 1. 数据格式：JSON 文件

每个回测结果生成一个 JSON 文件，前端独立渲染。

```
reports/
  {run_id}/
    data.json      # 回测数据
    index.html     # 前端渲染器（由前端 agent 生成）
```

### 2. JSON 数据结构

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
    {"type": "buy_signal", "timestamp": "...", "data": {"price": 20000, "label": "MA金叉", "color": "green"}},
    {"type": "pattern_mark", "timestamp": "...", "data": {
      "pattern": "head_and_shoulders_bottom",
      "points": [
        {"timestamp": "...", "price": 100, "label": "左肩"},
        {"timestamp": "...", "price": 95, "label": "头"},
        {"timestamp": "...", "price": 100, "label": "右肩"}
      ],
      "neckline": {"price": 100},
      "label": "头肩底",
      "color": "purple"
    }}
  ]
}
```

### 3. Annotation 接口约定

#### 通用字段
- `type`: AnnotationType 枚举值
- `timestamp`: 主时间点
- `data`: 类型相关数据

#### 类型约定

| type | data 字段 | 说明 |
|------|----------|------|
| `buy_signal` | `price`, `label`, `color` | 买入信号 |
| `sell_signal` | `price`, `label`, `color` | 卖出信号 |
| `pattern_mark` | `pattern`, `points`, `neckline`, `label`, `color` | 形态标注 |
| `horizontal_line` | `price`, `label`, `color` | 水平线 |
| `trend_line` | `start`, `end`, `label`, `color` | 趋势线 |
| `text_label` | `text`, `price`, `color` | 文本标注 |

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

### 4. 技术栈

- **图表库**: ECharts（轻量、功能丰富）
- **前端**: 纯 HTML + CSS + JS，无框架
- **Python**: 生成 JSON 数据

### 5. 渲染规则

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

## Consequences

### Positive
- 前后端解耦，可独立迭代
- JSON 格式便于调试和扩展
- 轻量 HTML 文件，易于分享

### Negative
- 前端需要单独开发
- 需要维护渲染规则映射表

## References
- Annotation 类型定义: `src/caisen/strategy/base.py`
- BacktestResult 数据结构: `src/caisen/core/engine.py`
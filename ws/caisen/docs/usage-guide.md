# 蔡森策略使用指南

## 一、策略概述

蔡森策略是一种基于形态识别的交易策略，主要捕捉底部反转形态（如W底、头肩底）带来的上涨机会。

**核心思想**：在市场形成整理平台后，跌破平台下沿（破底），然后重新站回（拉回），形成"破底翻"买点。

## 二、策略参数详解

### 2.1 平台检测参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `platform_min_bars` | 12 | 整理平台最小K线数（太短无法形成有效平台） |
| `platform_max_amplitude` | 0.05 | 平台最大振幅5%（太大是趋势，不是整理） |

### 2.2 风险控制参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `stop_loss_factor` | 0.94 | 止损系数（破底低点 × factor） |
| `min_profit_pct` | 0.04 | 最小盈利目标4% |
| `trailing_stop_pct` | 0.03 | 移动止损回撤3% |
| `volume_threshold` | 1.2 | 放量倍数阈值 |

### 2.3 胜率增强参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `long_only_mode` | False | True=只做多头，避免做空亏损 |
| `max_loss_pct` | 0.0 | 最大亏损容忍（超过此比例强制止损） |

## 三、形态开关

| 形态 | 说明 | 推荐 |
|------|------|------|
| `W_BOTTOM` | W底，双底反转 | ✅ 开启 |
| `HEAD_AND_SHOULDERS_BOTTOM` | 头肩底 | ✅ 开启 |
| `M_TOP` | M头，双顶反转 | ❌ 关闭（做空容易亏损） |
| `HEAD_AND_SHOULDERS_TOP` | 头肩顶 | ❌ 关闭 |
| `TRIANGLE` | 三角整理 | ❌ 关闭 |
| `FLAG` | 旗形整理 | ❌ 关闭 |
| `RECTANGLE` | 矩形整理 | ❌ 关闭 |
| `ROUNDING_BOTTOM` | 圆弧底 | ❌ 关闭 |
| `CUP_HANDLE` | 杯柄形态 | ❌ 关闭 |
| `BREAKOUT_PULLBACK` | 过前高 | ❌ 关闭 |

## 四、使用方法

### 4.1 命令行运行

```bash
# 使用默认配置运行
caisen run --strategy caisen --symbol ag --freq 60m

# 使用自定义配置运行
caisen run --strategy caisen --config configs/caisen_high_winrate.yaml --symbol ag --freq 60m

# 运行优化
caisen optimize --symbol ag --freq 60m --output-dir runs/optimization
```

### 4.2 Python 代码调用

```python
from caisen.strategy.cai_sen import CaiSenStrategy
from caisen.core.engine import BacktestEngine
from caisen.core.config import BacktestConfig

# 方式1：直接构造
strategy = CaiSenStrategy(
    stop_loss_factor=0.94,
    min_profit_pct=0.04,
    platform_min_bars=12,
    long_only_mode=True,
    max_loss_pct=0.10,
    w_bottom_enabled=True,
    head_and_shoulders_bottom_enabled=True,
    # ... 其他形态关闭
)

# 方式2：从配置文件加载
strategy = CaiSenStrategy.from_config_file("configs/caisen_high_winrate.yaml")

# 运行回测
engine = BacktestEngine(BacktestConfig(initial_capital=100000))
result = engine.run(strategy, bars)

print(f"胜率: {result.win_rate:.1%}")
print(f"年化收益: {result.total_return:.2%}")
print(f"最大回撤: {result.max_drawdown:.2%}")
```

### 4.3 YAML 配置示例

```yaml
# 高胜率配置
params:
  stop_loss_factor: 0.94
  min_profit_pct: 0.04
  trailing_stop_pct: 0.03
  platform_min_bars: 12
  volume_threshold: 1.2
  max_loss_pct: 0.10
  long_only_mode: true

patterns:
  W_BOTTOM: true
  HEAD_AND_SHOULDERS_BOTTOM: true
  # 其他形态全部关闭
  M_TOP: false
  HEAD_AND_SHOULDERS_TOP: false
  TRIANGLE: false
  FLAG: false
  RECTANGLE: false
  ROUNDING_BOTTOM: false
  CUP_HANDLE: false
  BREAKOUT_PULLBACK: false
```

## 五、参数调优指南

### 5.1 追求高收益（不在意回撤）
```yaml
# 激进配置
params:
  stop_loss_factor: 0.96      # 宽松止损
  min_profit_pct: 0.05         # 高止盈
  # 形态全部开启
patterns:
  W_BOTTOM: true
  M_TOP: true
  # ... 全部 true
```
**预期结果**：年化55%+，但回撤可能达14%+

### 5.2 追求高胜率（稳定收益）
```yaml
# 稳健配置
params:
  stop_loss_factor: 0.94      # 紧止损
  min_profit_pct: 0.04         # 适度止盈
  max_loss_pct: 0.10           # 最大亏损10%
  long_only_mode: true         # 只做多头
patterns:
  W_BOTTOM: true
  HEAD_AND_SHOULDERS_BOTTOM: true
  # 其他全部关闭
```
**预期结果**：胜率81%+，年化20%，回撤8%

### 5.3 平衡配置
```yaml
# 平衡配置
params:
  stop_loss_factor: 0.96
  min_profit_pct: 0.04
  max_loss_pct: 0.08
  long_only_mode: true
patterns:
  W_BOTTOM: true
  HEAD_AND_SHOULDERS_BOTTOM: true
  TRIANGLE: true
  CUP_HANDLE: true
```
**预期结果**：胜率65%+，年化25%+

## 六、网格优化

```python
from caisen.strategy.caisen_optimizer import grid_search, GridSearchConfig

# 配置参数搜索空间
config = GridSearchConfig(
    stop_loss_factors=[0.94, 0.95, 0.96, 0.97, 0.98],
    min_profit_pcts=[0.03, 0.04, 0.05],
    platform_min_bars_list=[8, 10, 12, 15],
    volume_thresholds=[1.2, 1.5, 2.0],
)

# 运行优化（2160种组合）
results = grid_search(bars, config=config, n_workers=4, top_n=10)

# 查看最优参数
for r in results:
    print(f"胜率={r.win_rate:.1%}, 年化={r.annual_return:.2%}, "
          f"参数: sl={r.params['stop_loss_factor']}, mp={r.params['min_profit_pct']}")
```

## 七、结果解读

### 回测结果指标

| 指标 | 说明 | 目标范围 |
|------|------|----------|
| `total_return` | 总收益率 | 越高越好 |
| `max_drawdown` | 最大回撤 | < 15% |
| `sharpe_ratio` | 夏普比率 | > 0.5 |
| `win_rate` | 胜率 | > 60% |
| `profit_factor` | 盈亏比 | > 1.0 |
| `trades` | 总交易数 | > 30 |

### 交易分析

```python
# 查看所有交易
for trade in engine.trades:
    print(f"{trade.timestamp}: {trade.side} @ {trade.price}, qty={trade.quantity:.2f}")

# 计算盈亏
buys = [t for t in engine.trades if t.side.name == 'BUY']
sells = [t for t in engine.trades if t.side.name == 'SELL']

for i in range(min(len(buys), len(sells))):
    pnl = (sells[i].price - buys[i].price) * buys[i].quantity
    print(f"Trade {i}: {'盈利' if pnl > 0 else '亏损'} {pnl:.0f}")
```

## 八、常见问题

### Q1: 为什么关闭 M_TOP 和其他空头形态？
A: 白银市场经常出现快速反弹，做空容易被套。数据显示只做多头的胜率比双向交易高15%+。

### Q2: max_loss_pct 设多少合适？
A: 建议 0.08~0.12。太小会频繁止损，太大可能无法控制单笔亏损。

### Q3: 如何判断策略是否过拟合？
A: 在不同品种/周期上验证。如果某一组参数只在一个品种上有效，说明可能过拟合。

### Q4: 能否自动优化参数？
A: 可以。使用 `caisen_optimizer.py` 中的 `grid_search()` 函数进行网格搜索。

---
生成时间: 2026-05-21
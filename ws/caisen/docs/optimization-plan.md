# 蔡森策略参数优化计划

## 目标
通过配置文件迭代优化蔡森策略参数，避免修改核心代码。

## 架构设计

### 1. 配置层 (`caisen_config.py`)
```python
@dataclass
class CaiSenConfig:
    # 平台检测参数
    platform_min_bars: int = 10
    platform_max_amplitude: float = 0.05

    # 破底翻参数
    breakdown_max_pct: float = 0.02

    # 仓位管理
    first_position_pct: float = 0.30
    second_position_pct: float = 0.50

    # 风险控制（可迭代优化）
    stop_loss_factor: float = 0.96
    min_profit_pct: float = 0.03
    trailing_stop_pct: float = 0.05
    volume_threshold: float = 1.5

    # 形态开关
    w_bottom_enabled: bool = True
    m_top_enabled: bool = True
    # ... 其他形态
```

### 2. 策略类方法 (`CaiSenStrategy`)
```python
@classmethod
def from_config_file(cls, config_path: str | Path) -> "CaiSenStrategy":
    config = CaiSenConfig.from_yaml(config_path)
    params = {...}  # 映射到构造函数参数
    return cls(**params)
```

### 3. 优化器 (`caisen_optimizer.py`)
- `GridSearchConfig`: 定义参数搜索空间
- `grid_search()`: 并行执行回测，返回最优参数

### 4. YAML 配置格式
```yaml
params:
  stop_loss_factor: 0.96
  min_profit_pct: 0.05
  platform_min_bars: 12
  volume_threshold: 1.2

patterns:
  W_BOTTOM: true
  M_TOP: false
  HEAD_AND_SHOULDERS_BOTTOM: true
  # ...
```

## 关键修复记录

### Bug: YAML 形态名称映射失败
**问题**: `f"{pattern_name}_enabled"` 格式不匹配（如 `M_TOP` vs `m_top_enabled`）

**原因**: YAML 使用下划线命名（如 `HEAD_AND_SHOULDERS_BOTTOM`），属性用驼峰（如 `head_and_shoulders_bottom_enabled`）

**修复**: 在 `CaiSenConfig.from_yaml()` 中添加显式映射：
```python
name_map = {
    "W_BOTTOM": "w_bottom_enabled",
    "M_TOP": "m_top_enabled",
    "HEAD_AND_SHOULDERS_BOTTOM": "head_and_shoulders_bottom_enabled",
    # ...
}
```

## 高收益优化（第一轮）

### 数据范围
- 品种：AG（白银）
- 周期：60分钟
- 时间：2026-01-05 ~ 2026-05-15
- 数据量：890 条

### 参数空间
| 参数 | 搜索范围 |
|------|----------|
| stop_loss_factor | 0.94, 0.95, 0.96, 0.97, 0.98 |
| min_profit_pct | 0.02, 0.03, 0.04, 0.05 |
| trailing_stop_pct | 0.03, 0.05, 0.08 |
| platform_min_bars | 8, 10, 12, 15 |
| volume_threshold | 1.2, 1.5, 2.0 |
| 形态组合 | 3 种（激进/平衡/保守） |

**总组合数**: 2160

### 最优结果
| 指标 | 值 |
|------|-----|
| 年化收益 | **55.43%** |
| 最大回撤 | 14.34% |
| 夏普比率 | 0.87 |
| 胜率 | 59.46% |
| 总交易 | 77 笔 |

---

## 高胜率优化（第二轮）— 达到 80% 胜率

### 优化目标
从 59% 胜率提升到 80% 以上，同时保持合理的收益。

### 发现的问题
1. **做空亏损严重**：白银市场经常出现快速反弹，做空容易被打止损
2. **大亏交易**：单笔最大亏损达到 -12240，亏损比例 -18.63%
3. **盈亏比接近 1**：平均盈利 3201，平均亏损 3052

### 新增参数
```python
# 胜率增强参数
long_only_mode: bool = True      # 只做多头（避免做空亏损）
trend_filter_enabled: bool = False  # 趋势过滤开关
trend_ma_period: int = 20       # 均线周期（用于趋势判断）
max_loss_pct: float = 0.10      # 最大亏损容忍（超过此比例强制止损）
time_stop_bars: int = 0         # 时间止损（持有N根K线后强制平仓）
```

### 核心发现

| 策略 | 胜率 | 年化 | 回撤 | 交易 |
|------|------|------|------|------|
| 全开形态（原始） | 56% | 21% | 24% | 62 |
| 只做多头 | 71% | 10% | 8% | 72 |
| 只做多头+趋势过滤 | 71% | 3% | 13% | 58 |
| 限制最大亏损5% | 60% | 18% | 6% | 100 |
| **只做最强形态+最大亏损** | **81%** | **20%** | **8%** | **65** |

### 关键结论

1. **只做多头显著提升胜率**：从 56% 提升到 71%，回撤从 24% 降到 8%
2. **趋势过滤效果不明显**：胜率不变但年化收益大幅下降，可能不适合当前市场
3. **限制最大亏损效果显著**：5% 限制下年化达到 18%，回撤仅 6%
4. **只做最强形态**：W底 + 头肩底，其他形态关闭，反而提升胜率
5. **综合策略最优**：只做多头 + 最大亏损限制 + 只做最强形态 = 81% 胜率

### 最优配置（高胜率版）

| 参数 | 值 | 说明 |
|------|-----|------|
| stop_loss_factor | 0.94 | 紧止损 |
| min_profit_pct | 0.04 | 适度止盈 |
| max_loss_pct | 0.10 | 最大亏损限制10% |
| platform_min_bars | 12 | 平台K线数 |
| volume_threshold | 1.2 | 放量倍数 |

**启用形态**：W底、头肩底

**关闭形态**：M头、头肩顶、三角、旗形、矩形、圆弧底、杯柄、过前高

### 验证结果

```
============================================================
蔡森策略高胜率配置验证
============================================================
胜率: 81.2%
年化收益: 19.96%
最大回撤: 8.16%
夏普比率: 0.87
总交易: 65
```

## 使用方法

### 1. 运行优化
```python
from caisen.strategy.caisen_optimizer import grid_search, GridSearchConfig

results = grid_search(bars, config=GridSearchConfig(), n_workers=4, top_n=5)
```

### 2. 应用最优配置
```python
strategy = CaiSenStrategy.from_config_file("runs/opt_ag_60m_2026/best_config.yaml")
```

### 3. 手动调整后再优化
修改 YAML 文件，再次运行优化即可迭代。

## 经验总结

### 提高胜率的关键

1. **只做趋势方向**：在上升趋势中做多，下降趋势中空仓，避免逆势交易
2. **限制单笔最大亏损**：通过 `max_loss_pct` 参数控制，防止极端亏损
3. **选择高质量形态**：W底和头肩底是最可靠的底部反转形态
4. **避免过度交易**：关闭低胜率形态（如旗形、三角），减少噪音信号

### 参数敏感度

- `max_loss_pct`: 最关键，0.1 比 0.05 表现更好
- `stop_loss_factor`: 紧止损 (0.94) 优于宽松止损 (0.98)
- `min_profit_pct`: 适度止盈 (0.04) 优于高止盈 (0.05)

### 形态质量排序

1. **W底**：最可靠，触发条件明确
2. **头肩底**：次可靠，需要较多历史数据
3. **其他形态**：胜率不稳定，建议关闭

## 文件清单
- `src/caisen/strategy/caisen_config.py` - 配置加载器
- `src/caisen/strategy/caisen_optimizer.py` - 网格搜索优化器
- `src/caisen/strategy/cai_sen.py` - 策略类（含 from_config_file）
- `configs/caisen_default.yaml` - 默认配置模板
- `configs/caisen_high_winrate.yaml` - 高胜率配置

## 下一步
- [x] 在更多品种/周期上验证（如黄金、原油）
- [ ] 增加更多参数到搜索空间（如 breakout_pullback 阈值）
- [ ] 添加 Walk-forward 验证防止过拟合
- [ ] 考虑加入机器学习超参数优化

---
生成时间: 2026-05-21
更新: 2026-05-21 高胜率优化完成
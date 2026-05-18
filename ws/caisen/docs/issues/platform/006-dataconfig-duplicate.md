# Architecture Issue: DataConfig 类重复定义

## Priority
**Warning** - 代码混乱

## Problem
存在两个不同的 `DataConfig` 类：
- `src/caisen/core/config.py` - 回测配置
- `src/caisen/data/config.py` - 数据加载配置

两者语义不同但命名相同，容易混淆。

## Impact
- 代码阅读困难
- 可能误用错误的配置类
- 类型注解可能混淆

## Reference
- **Architecture Review**: 2026-05-18
- **Related Code**:
  - `src/caisen/core/config.py`
  - `src/caisen/data/config.py`

## Recommended Fix
重命名其中一个或添加明确的前缀/后缀：
```python
# 方案 A: 重命名为 DataConfig
class DataConfig:
    ...

# 方案 B: 添加模块前缀
from caisen.data.config import DataConfig as DataLoaderConfig
```

## Acceptance Criteria
- [ ] 配置类命名清晰无歧义
- [ ] 类型注解正确
- [ ] 测试通过
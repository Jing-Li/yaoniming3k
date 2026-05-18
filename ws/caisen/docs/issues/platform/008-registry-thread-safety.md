# Architecture Issue: 数据源注册表线程不安全

## Priority
**Warning** - 并发问题

## Problem
`_datasources` 是模块级全局变量，多线程环境下不安全：

```python
_datasources: Dict[str, Type[DataLoader]] = {...}
_active_datasource: Optional[str] = None
```

## Impact
- 多线程调用可能冲突
- 并发场景下行为不确定
- 无法支持并行回测

## Reference
- **Architecture Review**: 2026-05-18
- **Related Code**: `src/caisen/data/registry.py`

## Recommended Fix
使用 `threading.Lock` 或 `contextvars`:

```python
import threading

_datasources_lock = threading.Lock()
_active_datasource: Optional[str] = None

def register_datasource(name: str, loader_class: Type[DataLoader]) -> None:
    with _datasources_lock:
        _datasources[name] = loader_class
```

## Acceptance Criteria
- [ ] 线程安全实现
- [ ] 并发测试通过
- [ ] 性能无显著下降
# Architecture Issue: 数据源注册表线程不安全

## Status: Resolved

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

## Resolution
在 `src/caisen/data/registry.py` 中添加 `threading.Lock` 保护所有注册表操作：

```python
_registry_lock = threading.Lock()

def register_datasource(name: str, loader_class: Type[DataLoader]) -> None:
    with _registry_lock:
        _datasources[name] = loader_class
```

所有涉及 `_datasources` 和 `_active_datasource` 读写的函数都使用 `with _registry_lock` 保护。

## Reference
- **Architecture Review**: 2026-05-18
- **Related Code**: `src/caisen/data/registry.py`

## Acceptance Criteria
- [x] 线程安全实现
- [ ] 并发测试通过
- [ ] 性能无显著下降
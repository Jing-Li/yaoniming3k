# ADR-0013: Annotation 提升到 core

## Status
Implemented

## Context
ADR-0008 Issue #3 指出 `Annotation` 和 `AnnotationType` 定义在 `strategy/base.py`，但被 `result/types.py` 等多个模块使用，需要提升到 `core` 作为共享契约。

## Decisions

### 1. 新文件 core/annotation.py

将 `Annotation` 和 `AnnotationType` 从 `strategy/base.py` 移动到 `core/annotation.py`。

### 2. 导出更新

- `core/__init__.py`: 导出 `Annotation`, `AnnotationType`
- `strategy/base.py`: 从 `core.annotation` 导入并重新导出（向后兼容）
- `result/types.py`: 从 `core.annotation` 导入
- `core/engine.py`: 从 `core.annotation` 导入

### 3. 文件结构

```
src/caisen/
├── core/
│   ├── annotation.py  # Annotation + AnnotationType (新)
│   ├── bar.py
│   ├── order.py
│   └── ...
└── strategy/
    └── base.py        # 只保留 Strategy 基类
```

## Consequences

### Positive
- `Annotation` 作为核心数据类型，可在任何模块使用
- 避免从 `strategy` 导入到 `result` 的跨层依赖
- 便于前端独立使用

### Negative
- 需要更新多个文件的导入路径

## References
- ADR-0008: 架构深化改进
- Issue #3: Annotation 提升到 core
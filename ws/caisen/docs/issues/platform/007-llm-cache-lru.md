# Architecture Issue: LLM 缓存缺少 LRU 淘汰

## Priority
**Warning** - 内存泄漏风险

## Problem
`response_cache` 没有 LRU 淘汰机制，只在超过 `max_cache_size` 后停止写入：

```python
if len(self.response_cache) >= self.max_cache_size:
    return  # 停止写入，但不淘汰旧数据
```

## Impact
- 内存占用持续增长
- 长期运行可能 OOM
- 缓存效率低

## Reference
- **Architecture Review**: 2026-05-18
- **Related Code**: `src/caisen/llm/`

## Recommended Fix
实现 LRU 缓存：

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_response(self, key: str) -> Optional[str]:
    ...
```

或使用 `cachetools` 库。

## Acceptance Criteria
- [ ] 实现 LRU 淘汰策略
- [ ] 缓存大小可控
- [ ] 测试通过
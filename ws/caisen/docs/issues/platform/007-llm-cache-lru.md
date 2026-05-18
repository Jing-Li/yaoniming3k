# Architecture Issue: LLM 缓存缺少 LRU 淘汰

## Priority
**Warning** - 内存泄漏风险

## Status
**Resolved** - 2026-05-18

## Problem
`response_cache` 没有 LRU 淘汰机制，只在超过 `max_cache_size` 后停止写入

## Solution
实现 `LRUCache` 类，使用 `OrderedDict` 实现 LRU 淘汰

## Changes
- `src/caisen/strategy/llm_strategy.py` - 新增 `LRUCache` 类

## Acceptance Criteria
- [x] 实现 LRU 淘汰策略
- [x] 缓存大小可控
- [x] 测试通过
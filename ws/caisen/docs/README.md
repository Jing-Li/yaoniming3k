# 文档目录

## 架构决策记录 (ADR)

| 编号 | 标题 | 状态 |
|------|------|------|
| [ADR-0001](./adr/0001-datasource-independent-project.md) | 数据源独立项目 | Accepted |
| [ADR-0002](./adr/0002-parquet-data-storage.md) | Parquet 数据存储 | Accepted |
| [ADR-0003](./adr/0003-strategy-abc-interface.md) | 策略 ABC 接口 | Accepted |
| [ADR-0004](./adr/0004-llm-strategy-architecture.md) | LLM 策略架构 | Accepted |
| [ADR-0005](./adr/0005-visualization-annotations.md) | 可视化标注定义 | Accepted |
| [ADR-0006](./adr/0006-compare-mode-code-llm.md) | 对比模式（代码 vs LLM） | Accepted |
| [ADR-0007](./adr/0007-visualization-report-architecture.md) | 可视化报告架构 | Accepted |
| [ADR-0010](./adr/0010-frontend-modularization.md) | 前端模块化 | Accepted |

## 平台问题

### 已解决

| 编号 | 标题 |
|------|------|
| [#001](./issues/platform/001-cli-mock-flag.md) | CLI --mock 标志 |
| [#002](./issues/platform/002-entry-points.md) | Entry Points 注册 |
| [#003](./issues/platform/003-data-integration-test.md) | 数据集成测试 |
| [#004](./issues/platform/004-local-loader-test.md) | LocalLoader 测试 |
| [#005](./issues/platform/005-freq-constant.md) | 频率常量定义 |
| [#006](./issues/platform/006-dataconfig-duplicate.md) | DataConfig 重复命名 |
| [#007](./issues/platform/007-llm-cache-lru.md) | LLM 缓存 LRU |
| [#008](./issues/platform/008-registry-thread-safety.md) | 注册表线程安全 |
| [#009](./issues/platform/009-adrs-pending.md) | ADR 待处理 |
| [#010](./issues/platform/010-cli-strategy-loading.md) | CLI 策略加载 |

## 策略问题

| 编号 | 标题 |
|------|------|
| [001](./issues/strategies/001-strategy-template-library.md) | 策略模板库 |
| [002](./issues/strategies/002-strategy-validation.md) | 策略验证 |
| [003](./issues/strategies/003-strategy-evolution.md) | 策略演进 |

## 相关文档

- [CONTEXT.md](../CONTEXT.md) - 领域术语表
- [README.md](../README.md) - 项目主文档
- [AGENTS.md](../AGENTS.md) - Agent 指南
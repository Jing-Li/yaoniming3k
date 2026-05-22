# ADR-0014: LLM Provider 简化

## Status
Accepted

## Context
ADR-0008 Issue #4 指出 `LLMClient` 承担了太多职责：
- Prompt 构建（`build_prompt`）
- API 调用（`call_llm`）
- 响应解析（`parse_response`）
- 结果校验

这种耦合导致难以独立测试和替换组件。

## Decision

### 1. LLMClient 简化为纯接口

`LLMClient` 简化为抽象接口，仅包含 `call(prompt: str) -> str` 方法：

```python
class LLMClient(ABC):
    @abstractmethod
    def call(self, prompt: str) -> str:
        pass
```

### 2. ResponseParser 独立为单独模块

`ResponseParser` 从 `LLMClient` 中提取，负责：
- JSON 解析
- 格式校验
- LLMResult 构造

```python
class ResponseParser:
    def parse(self, response: str) -> LLMResult
    def parse_raw(self, response: str) -> Dict[str, Any]
```

### 3. PromptBuilder 保持独立

已有的 `PromptBuilder` 模块保持不变，负责 Prompt 构建。

### 4. 删除 PromptBuilderClient 适配器

`LLMStrategy` 内部组合三个组件，不再需要 `PromptBuilderClient` 适配器：

```python
class LLMStrategy(Strategy):
    def __init__(
        self,
        llm_client=None,
        prompt_builder=None,
        response_parser=None
    ):
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.response_parser = response_parser or ResponseParser()

    def analyze(self, bars) -> LLMResult:
        prompt = self.prompt_builder.build(bars)
        response = self.llm_client.call(prompt)
        return self.response_parser.parse(response)
```

### 5. OpenAIProvider 实现简化接口

`OpenAIProvider` 实现 `call(prompt: str) -> str`，移除原有的 `build_prompt` 和 `parse_response`。

## Consequences

### Positive
- **职责单一**：每个组件职责清晰
- **可测试性**：可独立测试 PromptBuilder、ResponseParser、LLMClient
- **可组合性**：支持不同组合（如测试时用 MockLLMClient + ResponseParser）
- **扩展性**：新增 Provider 只需实现 `call` 方法

### Negative
- **接口变更**：现有代码需要更新调用方式
- **向后兼容**：需要迁移现有使用 `analyze(bars)` 的代码

## Files Changed
- `src/caisen/strategy/llm/client.py` - 简化为纯接口
- `src/caisen/strategy/llm/provider.py` - 实现 `call` 方法
- `src/caisen/strategy/llm/response.py` - 新增 ResponseParser
- `src/caisen/strategy/llm/strategy.py` - 移除 PromptBuilderClient，组合三个组件
- `src/caisen/strategy/llm/evolver.py` - 使用新的接口
- `src/caisen/strategy/llm/__init__.py` - 更新导出

## References
- ADR-0008: 架构深化改进
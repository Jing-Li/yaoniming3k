# Token 使用统计

<cite>
**本文引用的文件**   
- [src/openai_provider/providers/taiji.py](file://src/openai_provider/providers/taiji.py)
- [src/openai_provider/models/openai.py](file://src/openai_provider/models/openai.py)
- [src/openai_provider/config.py](file://src/openai_provider/config.py)
- [tests/test_regression.py](file://tests/test_regression.py)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构总览](#架构总览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能考量](#性能考量)
8. [故障排查指南](#故障排查指南)
9. [结论](#结论)
10. [附录](#附录)

## 简介
本技术文档聚焦于“Token 使用统计”功能，系统性阐述以下要点：
- Token 计数的实现原理与关键方法
- tiktoken 编码器的使用与回退策略
- 消息级 Token 计算与总 Token 统计
- tool_calls 参数 Token 的处理方式
- 中英文混合文本的计数行为
- 集成不同编码器、自定义计数策略的方法
- 性能优化建议与准确性/误差范围说明

## 项目结构
本项目为 OpenAI 兼容网关，将请求转发至 Taiji LLM 后端。Token 统计逻辑集中在 Provider 层，负责：
- 构建请求前对 prompt 进行消息级 Token 估算
- 解析 SSE 响应中的 token 信息（如可用）
- 在缺失服务端 token 时，基于本地编码器或字符估算回退完成 completion_tokens 与 total_tokens 的计算

```mermaid
graph TB
A["FastAPI 路由<br/>main.py"] --> B["TaijiProvider<br/>providers/taiji.py"]
B --> C["tiktoken 编码器<br/>_get_tokenizer/_count_tokens"]
B --> D["消息 Token 统计<br/>_count_messages_tokens"]
B --> E["SSE 解析与 token 信息提取<br/>_parse_sse_body"]
B --> F["Usage 模型<br/>models/openai.py"]
B --> G["配置项<br/>config.py"]
```

图表来源
- [src/openai_provider/providers/taiji.py:65-120](file://src/openai_provider/providers/taiji.py#L65-L120)
- [src/openai_provider/models/openai.py:125-131](file://src/openai_provider/models/openai.py#L125-L131)
- [src/openai_provider/config.py:24-33](file://src/openai_provider/config.py#L24-L33)

章节来源
- [src/openai_provider/providers/taiji.py:65-120](file://src/openai_provider/providers/taiji.py#L65-L120)
- [src/openai_provider/models/openai.py:125-131](file://src/openai_provider/models/openai.py#L125-L131)
- [src/openai_provider/config.py:24-33](file://src/openai_provider/config.py#L24-L33)

## 核心组件
- 编码器获取与缓存
  - _get_tokenizer：惰性加载 tiktoken 编码器（cl100k_base），失败则记录警告并将内部编码器置空以启用回退。
- 文本 Token 计数
  - _count_tokens：优先使用 tiktoken.encode；不可用时采用字符估算回退（中文按约每 2 字符≈1 token，英文等按约每 4 字符≈1 token）。
- 消息级 Token 统计
  - _count_messages_tokens：遍历 messages，累加 role、content、name、tool_call_id 以及每个 tool_calls 的 id、function.name、function.arguments 的 Token 数。
- SSE 响应 token 信息提取
  - _parse_sse_body：从 type=object 的数据块中抽取 promptTokens、completionTokens、useTokens、contextTokens 等字段。
- 非流式/流式响应中的 Usage 组装
  - chat_completions 与 stream_chat_completions：优先使用服务端返回的 completion_tokens；否则基于 content/reasoning_content/tool_calls 拼接后调用 _count_tokens 估算；total_tokens = prompt_tokens + completion_tokens。

章节来源
- [src/openai_provider/providers/taiji.py:65-94](file://src/openai_provider/providers/taiji.py#L65-L94)
- [src/openai_provider/providers/taiji.py:96-120](file://src/openai_provider/providers/taiji.py#L96-L120)
- [src/openai_provider/providers/taiji.py:633-668](file://src/openai_provider/providers/taiji.py#L633-L668)
- [src/openai_provider/providers/taiji.py:737-758](file://src/openai_provider/providers/taiji.py#L737-L758)
- [src/openai_provider/providers/taiji.py:930-954](file://src/openai_provider/providers/taiji.py#L930-L954)

## 架构总览
下图展示了 Token 统计在非流式与流式路径中的关键流程与数据流向。

```mermaid
sequenceDiagram
participant Client as "客户端"
participant API as "FastAPI 路由"
participant Prov as "TaijiProvider"
participant Tik as "tiktoken 编码器"
participant Srv as "Taiji 后端(SSE)"
Client->>API : "POST /v1/chat/completions"
API->>Prov : "chat_completions/stream_chat_completions"
Prov->>Prov : "_prepare_request(_count_messages_tokens)"
Prov->>Tik : "_get_tokenizer/_count_tokens(可选)"
Prov->>Srv : "POST 请求(含 text)"
Srv-->>Prov : "SSE 数据流(data : ...)"
Prov->>Prov : "_parse_sse_body 提取 token_info"
alt "有 completion_tokens"
Prov->>Prov : "直接使用 completion_tokens"
else "无 completion_tokens"
Prov->>Tik : "_count_tokens(content+reasoning+tool_calls)"
end
Prov->>Prov : "total_tokens = prompt_tokens + completion_tokens"
Prov-->>API : "Usage(prompt, completion, total)"
API-->>Client : "JSON/Stream 响应"
```

图表来源
- [src/openai_provider/providers/taiji.py:520-600](file://src/openai_provider/providers/taiji.py#L520-L600)
- [src/openai_provider/providers/taiji.py:633-668](file://src/openai_provider/providers/taiji.py#L633-L668)
- [src/openai_provider/providers/taiji.py:737-758](file://src/openai_provider/providers/taiji.py#L737-L758)
- [src/openai_provider/providers/taiji.py:930-954](file://src/openai_provider/providers/taiji.py#L930-L954)

## 详细组件分析

### 编码器与回退策略
- 编码器选择
  - 默认使用 cl100k_base（gpt-3.5/gpt-4 系列常用编码），通过 tiktoken.get_encoding 获取并缓存到实例变量。
- 回退策略
  - 当 tiktoken 未安装或导入失败时，记录警告日志，并在后续计数中使用字符估算：
    - 中文区间判断：\u4e00-\u9fff
    - 估算公式：max(1, 中文数 // 2 + 其他字符数 // 4)
- 适用场景
  - 生产环境建议安装 tiktoken 以获得更精确的计数；若受限环境无法安装，回退策略仍可工作但存在误差。

章节来源
- [src/openai_provider/providers/taiji.py:65-94](file://src/openai_provider/providers/taiji.py#L65-L94)

#### 类与方法关系图
```mermaid
classDiagram
class TaijiProvider {
- Any _tokenizer
+ _get_tokenizer() Any
+ _count_tokens(text) int
+ _count_messages_tokens(messages) int
+ _parse_sse_body(body) tuple
+ chat_completions(req, request_id) ChatCompletionResponse
+ stream_chat_completions(req, request_id) AsyncGenerator
}
class Tiktoken {
+ get_encoding(name) Encoder
+ encode(text) list
}
class Usage {
+ int prompt_tokens
+ int completion_tokens
+ int total_tokens
}
TaijiProvider --> Tiktoken : "使用"
TaijiProvider --> Usage : "构造"
```

图表来源
- [src/openai_provider/providers/taiji.py:65-120](file://src/openai_provider/providers/taiji.py#L65-L120)
- [src/openai_provider/models/openai.py:125-131](file://src/openai_provider/models/openai.py#L125-L131)

### 消息级 Token 计算与 tool_calls 处理
- 遍历每条消息，累加：
  - role、content、name、tool_call_id
  - 对于 tool_calls：id、function.name、function.arguments 均参与计数
- 注意：arguments 是字符串形式，直接计入其 Token 数，避免重复序列化带来的额外开销。

章节来源
- [src/openai_provider/providers/taiji.py:96-120](file://src/openai_provider/providers/taiji.py#L96-L120)

#### 流程图：消息 Token 累计
```mermaid
flowchart TD
Start(["进入 _count_messages_tokens"]) --> Init["total = 0"]
Init --> ForMsg{"遍历 messages"}
ForMsg --> |是| AddRole["total += _count_tokens(role)"]
AddRole --> HasContent{"content 是否存在?"}
HasContent --> |是| AddContent["total += _count_tokens(content)"]
HasContent --> |否| CheckName
AddContent --> CheckName{"name 是否存在?"}
CheckName --> |是| AddName["total += _count_tokens(name)"]
CheckName --> |否| CheckToolCallId
AddName --> CheckToolCallId{"tool_call_id 是否存在?"}
CheckToolCallId --> |是| AddToolCallId["total += _count_tokens(tool_call_id)"]
CheckToolCallId --> |否| CheckToolCalls
AddToolCallId --> CheckToolCalls{"tool_calls 是否存在?"}
CheckToolCalls --> |是| LoopTC["遍历 tool_calls"]
CheckToolCalls --> |否| NextMsg
LoopTC --> AddTC["total += _count_tokens(id/name/arguments)"]
AddTC --> NextMsg["下一条消息"]
NextMsg --> ForMsg
ForMsg --> |否| End(["返回 total"])
```

图表来源
- [src/openai_provider/providers/taiji.py:96-120](file://src/openai_provider/providers/taiji.py#L96-L120)

### 非流式响应中的 Token 统计
- prompt_tokens：使用原始消息统计值（截断前的真实请求大小），确保上层系统能正确触发上下文压缩等策略。
- completion_tokens：
  - 优先使用 SSE object 数据中的 completion_tokens
  - 否则根据 content、reasoning_content、tool_calls 拼接后的文本调用 _count_tokens 估算
- total_tokens：严格等于 prompt_tokens + completion_tokens，符合 OpenAI 规范

章节来源
- [src/openai_provider/providers/taiji.py:737-758](file://src/openai_provider/providers/taiji.py#L737-L758)

#### 序列图：非流式 Token 统计
```mermaid
sequenceDiagram
participant P as "TaijiProvider.chat_completions"
participant M as "_count_messages_tokens"
participant S as "_parse_sse_body"
participant T as "_count_tokens"
P->>M : "计算 original_prompt_tokens"
P->>S : "解析 SSE 得到 token_info"
alt "token_info 包含 completion_tokens"
P->>P : "completion_tokens = token_info.completion_tokens"
else "缺少 completion_tokens"
P->>T : "_count_tokens(content+reasoning+tool_calls)"
T-->>P : "completion_tokens"
end
P->>P : "total_tokens = prompt_tokens + completion_tokens"
```

图表来源
- [src/openai_provider/providers/taiji.py:520-600](file://src/openai_provider/providers/taiji.py#L520-L600)
- [src/openai_provider/providers/taiji.py:633-668](file://src/openai_provider/providers/taiji.py#L633-L668)
- [src/openai_provider/providers/taiji.py:737-758](file://src/openai_provider/providers/taiji.py#L737-L758)

### 流式响应中的 Token 统计
- 与流式内容聚合同步：
  - 维护 total_content、total_reasoning，并在结束时统一计算 completion_tokens
  - 同样优先使用 SSE object 中的 completion_tokens，否则基于已聚合文本估算
- 最终在结束 chunk 中附带 usage，包含 prompt_tokens、completion_tokens、total_tokens

章节来源
- [src/openai_provider/providers/taiji.py:930-954](file://src/openai_provider/providers/taiji.py#L930-L954)

#### 序列图：流式 Token 统计
```mermaid
sequenceDiagram
participant P as "stream_chat_completions"
participant S as "_parse_sse_body(增量)"
participant T as "_count_tokens"
loop 逐行读取 SSE
P->>S : "解析 data : object/string"
S-->>P : "更新 token_info 或累积内容"
end
alt "token_info 包含 completion_tokens"
P->>P : "completion_tokens = token_info.completion_tokens"
else "缺少 completion_tokens"
P->>T : "_count_tokens(total_content+total_reasoning)"
T-->>P : "completion_tokens"
end
P->>P : "total_tokens = prompt_tokens + completion_tokens"
P-->>P : "yield finish chunk with usage"
```

图表来源
- [src/openai_provider/providers/taiji.py:800-996](file://src/openai_provider/providers/taiji.py#L800-L996)

### 中英文混合文本的计数行为
- 使用 tiktoken 时：遵循 cl100k_base 的分词规则，对中英文混合文本给出较准确的 token 数。
- 回退策略下：
  - 中文按约每 2 字符≈1 token
  - 英文及其他字符按约每 4 字符≈1 token
  - 该策略对纯中文或纯英文场景相对稳健，但对复杂混合文本存在一定误差

章节来源
- [src/openai_provider/providers/taiji.py:77-94](file://src/openai_provider/providers/taiji.py#L77-L94)

### 集成不同的 Token 编码器与自定义计数策略
- 替换编码器
  - 可在 _get_tokenizer 中切换 tiktoken 的 encoding name（例如 gpt-4o 相关编码），或在外部注入自定义编码器实例。
- 自定义计数策略
  - 可重写 _count_tokens 以实现特定语言或领域分词器（如 jieba、sentencepiece 等）的接入。
  - 也可在 _count_messages_tokens 中扩展字段或调整权重（例如对 JSON arguments 做特殊处理）。
- 注意事项
  - 保持与现有 Usage 语义一致：prompt_tokens 应为截断前的真实请求大小；completion_tokens 需与 total_tokens 保持一致性约束。

章节来源
- [src/openai_provider/providers/taiji.py:65-94](file://src/openai_provider/providers/taiji.py#L65-94)
- [src/openai_provider/providers/taiji.py:96-120](file://src/openai_provider/providers/taiji.py#L96-L120)

### 性能优化建议
- 预装 tiktoken 以避免回退分支与额外正则/循环开销
- 复用实例级 _tokenizer 缓存（当前已实现惰性加载与缓存）
- 减少不必要的字符串拼接与序列化：
  - 在估算 completion_tokens 时仅拼接必要部分（content、reasoning_content、tool_calls 的 model_dump）
- 在高并发场景下，考虑进程内共享只读编码器实例（当前单进程内已缓存）

章节来源
- [src/openai_provider/providers/taiji.py:65-94](file://src/openai_provider/providers/taiji.py#L65-94)
- [src/openai_provider/providers/taiji.py:737-758](file://src/openai_provider/providers/taiji.py#L737-L758)
- [src/openai_provider/providers/taiji.py:930-954](file://src/openai_provider/providers/taiji.py#L930-L954)

## 依赖关系分析
- 模块耦合
  - Provider 依赖 models.openai.Usage 输出标准 Usage 结构
  - Provider 依赖 config.Settings 获取最大文本长度等配置
  - Provider 依赖 tiktoken（可选）用于精确计数
- 外部接口
  - SSE 对象类型数据中包含 promptTokens、completionTokens、useTokens、contextTokens 等字段，用于优先取用服务端统计

```mermaid
graph LR
P["TaijiProvider"] --> U["Usage(models/openai.py)"]
P --> C["Settings(config.py)"]
P --> TK["tiktoken(可选)"]
P --> SSE["SSE object 数据(pTokens/cTokens/useTokens/contextTokens)"]
```

图表来源
- [src/openai_provider/providers/taiji.py:633-668](file://src/openai_provider/providers/taiji.py#L633-L668)
- [src/openai_provider/models/openai.py:125-131](file://src/openai_provider/models/openai.py#L125-L131)
- [src/openai_provider/config.py:24-33](file://src/openai_provider/config.py#L24-L33)

章节来源
- [src/openai_provider/providers/taiji.py:633-668](file://src/openai_provider/providers/taiji.py#L633-L668)
- [src/openai_provider/models/openai.py:125-131](file://src/openai_provider/models/openai.py#L125-L131)
- [src/openai_provider/config.py:24-33](file://src/openai_provider/config.py#L24-L33)

## 性能考量
- 时间复杂度
  - _count_tokens：O(n)，n 为文本长度（tiktoken 或回退估算）
  - _count_messages_tokens：O(m·n)，m 为消息数量，n 为平均消息长度
- 空间复杂度
  - 主要消耗在字符串拼接与临时列表，整体线性增长
- 优化点
  - 避免重复编码：尽量复用 _tokenizer 实例
  - 仅在必要时估算 completion_tokens（优先使用 SSE 提供的数值）
  - 控制工具调用参数的序列化体积（arguments 过大时可考虑采样或摘要）

[本节为通用性能讨论，不直接分析具体文件]

## 故障排查指南
- 常见告警
  - “tiktoken not available, falling back to character-based estimation”：表示未安装 tiktoken，系统将使用字符估算。可通过安装依赖解决。
- 验证用例
  - 测试覆盖非流式与流式两种路径下的 completion_tokens 取值，确认 SSE object 数据被正确解析并写入 usage。
- 定位步骤
  - 检查 SSE object 数据是否包含 completionTokens/promptTokens/useTokens
  - 核对 _count_messages_tokens 是否正确遍历了所有消息字段与 tool_calls
  - 确认 total_tokens 是否等于 prompt_tokens + completion_tokens

章节来源
- [logs/taiji-provider.log](file://logs/taiji-provider.log)
- [tests/test_regression.py:147-175](file://tests/test_regression.py#L147-L175)

## 结论
- 本实现以 tiktoken 为主、字符估算回退为辅，兼顾精度与可用性
- 消息级统计覆盖 role/content/name/tool_call_id 及 tool_calls 的关键字段，保证 prompt_tokens 的完整性
- 非流式与流式路径均优先使用 SSE 提供的 completion_tokens，缺失时再估算，且 total_tokens 严格满足 OpenAI 规范
- 针对中英文混合文本，tiktoken 提供较高精度；回退策略具备基本稳健性但存在误差
- 通过合理集成与优化，可在保证准确性的同时提升统计性能

[本节为总结性内容，不直接分析具体文件]

## 附录

### 代码片段路径参考
- 编码器获取与回退
  - [src/openai_provider/providers/taiji.py:65-94](file://src/openai_provider/providers/taiji.py#L65-L94)
- 消息级 Token 统计
  - [src/openai_provider/providers/taiji.py:96-120](file://src/openai_provider/providers/taiji.py#L96-L120)
- SSE token 信息提取
  - [src/openai_provider/providers/taiji.py:633-668](file://src/openai_provider/providers/taiji.py#L633-L668)
- 非流式 Usage 组装
  - [src/openai_provider/providers/taiji.py:737-758](file://src/openai_provider/providers/taiji.py#L737-L758)
- 流式 Usage 组装
  - [src/openai_provider/providers/taiji.py:930-954](file://src/openai_provider/providers/taiji.py#L930-L954)
- Usage 模型定义
  - [src/openai_provider/models/openai.py:125-131](file://src/openai_provider/models/openai.py#L125-L131)
- 配置项（最大文本长度、会话信息等）
  - [src/openai_provider/config.py:24-33](file://src/openai_provider/config.py#L24-L33)
- 回归测试（SSE token 字段校验）
  - [tests/test_regression.py:147-175](file://tests/test_regression.py#L147-L175)
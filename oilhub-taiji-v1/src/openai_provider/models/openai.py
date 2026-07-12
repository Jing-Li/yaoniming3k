from __future__ import annotations

from typing import Literal, Any

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Custom base model that excludes None fields by default
# ---------------------------------------------------------------------------

class OpenAIModel(BaseModel):
    """Base model for OpenAI-compatible responses.

    Excludes None fields in serialization to match OpenAI API behavior.
    """

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump_json(**kwargs)


# ---------------------------------------------------------------------------
# Tool / Function Calling models
# ---------------------------------------------------------------------------

class FunctionDefinition(OpenAIModel):
    """OpenAI function definition for tool registration."""

    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None


class ToolDefinition(OpenAIModel):
    """OpenAI tool definition wrapping a function."""

    type: Literal["function"] = "function"
    function: FunctionDefinition


class ToolCallFunction(OpenAIModel):
    """Function name and arguments within a tool call."""

    name: str
    arguments: str


class ToolCall(OpenAIModel):
    """A single tool call in a completion response."""

    index: int | None = None
    id: str | None = None
    type: Literal["function"] = "function"
    function: ToolCallFunction


class ToolChoice(OpenAIModel):
    """Specific tool choice targeting a named function."""

    type: Literal["function"] = "function"
    function: dict[str, Any]


# ---------------------------------------------------------------------------
# Messages & Request
# ---------------------------------------------------------------------------

class ContentPart(OpenAIModel):
    """A single content part for multimodal messages (text or image_url)."""

    type: Literal["text", "image_url"]
    text: str | None = None
    image_url: dict[str, Any] | None = None


class ChatMessage(OpenAIModel):
    """A single message in a chat conversation.

    Supports multimodal content (OpenAI vision format):
    - str: plain text
    - list[ContentPart]: multimodal parts (text + image_url)
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[ContentPart] | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None


class ChatCompletionRequest(OpenAIModel):
    """OpenAI-compatible chat completion request body."""

    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[ChatMessage]
    temperature: float | None = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=1.0, ge=0, le=1)
    n: int | None = Field(default=1, ge=1, le=10)
    stream: bool | None = False
    stop: str | list[str] | None = None
    presence_penalty: float | None = Field(default=0, ge=-2, le=2)
    frequency_penalty: float | None = Field(default=0, ge=-2, le=2)
    user: str | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: str | ToolChoice | None = None
    # Taiji 扩展能力（非标准 OpenAI 字段）
    thinking: bool | None = None   # None = 使用服务端默认值
    web_search: bool | None = None  # None = 使用服务端默认值


# ---------------------------------------------------------------------------
# Non-streaming response models
# ---------------------------------------------------------------------------

class ChatCompletionMessage(OpenAIModel):
    """Assistant message in a non-streaming completion response."""

    role: Literal["assistant"] = "assistant"
    content: str | None = None
    reasoning_content: str | None = None
    tool_calls: list[ToolCall] | None = None


class ChatCompletionChoice(OpenAIModel):
    """A single choice in a non-streaming completion response."""

    index: int = 0
    message: ChatCompletionMessage
    logprobs: dict[str, Any] | None = None
    finish_reason: str | None = "stop"


class Usage(OpenAIModel):
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(OpenAIModel):
    """OpenAI-compatible non-streaming chat completion response."""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: Usage
    system_fingerprint: str | None = None


# ---------------------------------------------------------------------------
# Streaming models
# ---------------------------------------------------------------------------

class ChatCompletionDelta(OpenAIModel):
    """Incremental content delta in a streaming response."""

    role: Literal["assistant"] | None = None
    content: str | None = None
    reasoning_content: str | None = None
    tool_calls: list[ToolCall] | None = None


class ChatCompletionStreamChoice(OpenAIModel):
    """A single choice in a streaming completion chunk."""

    index: int = 0
    delta: ChatCompletionDelta
    logprobs: dict[str, Any] | None = None
    finish_reason: str | None = None


class ChatCompletionStreamResponse(OpenAIModel):
    """OpenAI-compatible streaming chat completion chunk."""

    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChatCompletionStreamChoice]
    usage: Usage | None = None
    system_fingerprint: str | None = None

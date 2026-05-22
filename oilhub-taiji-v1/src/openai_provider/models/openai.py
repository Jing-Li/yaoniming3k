from typing import List, Optional, Union, Literal, Any
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Custom base model that excludes None fields by default
# ---------------------------------------------------------------------------

class OpenAIModel(BaseModel):
    """Base model for OpenAI-compatible responses. Excludes None fields in serialization."""

    def model_dump(self, **kwargs: Any) -> dict:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump_json(**kwargs)


# ---------------------------------------------------------------------------
# Tool / Function Calling models
# ---------------------------------------------------------------------------

class FunctionDefinition(OpenAIModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[dict] = None


class ToolDefinition(OpenAIModel):
    type: Literal["function"] = "function"
    function: FunctionDefinition


class ToolCallFunction(OpenAIModel):
    name: str
    arguments: str


class ToolCall(OpenAIModel):
    index: Optional[int] = None
    id: Optional[str] = None
    type: Literal["function"] = "function"
    function: ToolCallFunction


class ToolChoice(OpenAIModel):
    type: Literal["function"] = "function"
    function: dict


# ---------------------------------------------------------------------------
# Messages & Request
# ---------------------------------------------------------------------------

class ChatMessage(OpenAIModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class ChatCompletionRequest(OpenAIModel):
    model_config = ConfigDict(extra="ignore")

    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    n: Optional[int] = Field(default=1, ge=1, le=10)
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    user: Optional[str] = None
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[Union[str, ToolChoice]] = None


# ---------------------------------------------------------------------------
# Non-streaming response models
# ---------------------------------------------------------------------------

class ChatCompletionMessage(OpenAIModel):
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class ChatCompletionChoice(OpenAIModel):
    index: int = 0
    message: ChatCompletionMessage
    logprobs: Optional[dict] = None
    finish_reason: Optional[str] = "stop"


class Usage(OpenAIModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(OpenAIModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage
    system_fingerprint: Optional[str] = None


# ---------------------------------------------------------------------------
# Streaming models
# ---------------------------------------------------------------------------

class ChatCompletionDelta(OpenAIModel):
    role: Optional[Literal["assistant"]] = None
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class ChatCompletionStreamChoice(OpenAIModel):
    index: int = 0
    delta: ChatCompletionDelta
    logprobs: Optional[dict] = None
    finish_reason: Optional[str] = None


class ChatCompletionStreamResponse(OpenAIModel):
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionStreamChoice]
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None

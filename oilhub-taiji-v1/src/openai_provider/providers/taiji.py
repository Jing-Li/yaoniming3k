"""Taiji LLM Provider 实现。

将 OpenAI Chat Completions 请求转发至 Taiji 后端，
处理 SSE 响应解析、tool_calls 提取、think 标签分离和 token 计数。
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import httpx

from ..config import settings
from ..exceptions import (
    ProviderError,
    TaijiBusinessError,
    TaijiHTTPError,
    TaijiRequestError,
    TaijiTimeoutError,
)
from ..models.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatCompletionStreamResponse,
    ChatCompletionStreamChoice,
    ChatCompletionDelta,
    ToolCall,
    ToolCallFunction,
    ToolDefinition,
    Usage,
)
from ..models.taiji import TaijiRequest
from .base import BaseProvider

logger_req = logging.getLogger("provider_request")
logger_resp = logging.getLogger("provider_response")


class TaijiProvider(BaseProvider):
    """Taiji LLM Provider。

    将 OpenAI Chat Completions 请求转换为 Taiji API 调用，
    支持非流式和流式两种模式。
    """

    def __init__(self) -> None:
        self._tokenizer: Any = None
        self.base_url: str = settings.TAIJI_BASE_URL.rstrip("/")
        self.api_key: str = settings.TAIJI_API_KEY
        self.max_text_length: int = settings.TAIJI_MAX_TEXT_LENGTH
        self.content_fields: list[str] = settings.content_fields_list
        self.session_id: int = settings.TAIJI_SESSION_ID
        self.session_cookie: str = settings.TAIJI_SESSION_COOKIE

    async def close(self) -> None:
        """释放资源（当前无持久连接，预留接口）。"""

    def _get_tokenizer(self) -> Any:
        """Lazy load tiktoken encoder."""
        if self._tokenizer is None:
            try:
                import tiktoken
                # Use cl100k_base encoding (used by gpt-3.5-turbo, gpt-4)
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                logger_req.warning("tiktoken not available, falling back to character-based estimation")
                self._tokenizer = None
        return self._tokenizer

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken, fallback to char-based estimation.

        Args:
            text: 要计数的文本。

        Returns:
            估算的 token 数量。
        """
        tokenizer = self._get_tokenizer()
        if tokenizer:
            return len(tokenizer.encode(text))
        else:
            # Fallback: rough estimation (1 token ≈ 4 chars for English, ≈ 1.5 chars for Chinese)
            # Count Chinese characters
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            other_chars = len(text) - chinese_chars
            return max(1, chinese_chars // 2 + other_chars // 4)

    def _count_messages_tokens(self, messages: list[Any]) -> int:
        """Count total tokens in a list of ChatMessage objects.

        Args:
            messages: ChatMessage 对象列表。

        Returns:
            所有消息的总 token 数。
        """
        total = 0
        for msg in messages:
            # Count role and content
            total += self._count_tokens(msg.role or "")
            if msg.content:
                total += self._count_tokens(msg.content)
            if msg.name:
                total += self._count_tokens(msg.name)
            if msg.tool_call_id:
                total += self._count_tokens(msg.tool_call_id)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total += self._count_tokens(tc.id or "")
                    total += self._count_tokens(tc.function.name or "")
                    total += self._count_tokens(tc.function.arguments or "")
        return total

    def _build_tools_prompt(self, tools: list[ToolDefinition], tool_choice: str = "auto") -> str:
        """将 OpenAI tools 定义转换为 taiji 可理解的 XML/DSML 格式指令。"""
        lines = []

        # === Section 1: Tool catalog ===
        lines.append("You have access to the following tools:")
        lines.append("")
        for i, tool in enumerate(tools, 1):
            func = tool.function
            params = json.dumps(func.parameters, ensure_ascii=False) if func.parameters else "{}"
            lines.append(f"{i}. **{func.name}**")
            if func.description:
                lines.append(f"   Description: {func.description}")
            lines.append(f"   Parameters schema: {params}")
            lines.append("")

        # === Section 2: Tool selection rules ===
        lines.append("--- TOOL SELECTION RULES ---")
        lines.append("1. Analyze the user request carefully and determine which tool(s) can help.")
        lines.append("2. If multiple tools are relevant, choose the most appropriate one(s). You may call multiple tools in a single response.")
        lines.append("3. Ensure all required parameters are provided. If a required parameter is missing, ask the user for it instead of guessing.")
        lines.append("4. Do NOT make up parameter values. Only use values explicitly provided by the user or derived from context.")
        lines.append("")

        # === Section 3: Response format (XML/DSML) ===
        lines.append("--- RESPONSE FORMAT ---")
        lines.append("When you decide to use a tool, respond using XML-style tool call syntax. Do NOT use JSON format.")
        lines.append("CRITICAL: NEVER use JSON format like {\"tool_calls\": [...]}. ALWAYS use XML format shown below.")
        lines.append("")
        lines.append("Format for a single tool call:")
        lines.append("<tool_calls>")
        lines.append('  <invoke name="tool_name">')
        lines.append('    <parameter name="param1">value1</parameter>')
        lines.append('    <parameter name="param2">value2</parameter>')
        lines.append('  </invoke>')
        lines.append("</tool_calls>")
        lines.append("")
        lines.append("Example with actual tool (write_file):")
        lines.append("<tool_calls>")
        lines.append('  <invoke name="write_file">')
        lines.append('    <parameter name="path">/tmp/test.py</parameter>')
        lines.append('    <parameter name="content">print("hello world")</parameter>')
        lines.append('  </invoke>')
        lines.append("</tool_calls>")
        lines.append("")
        lines.append("For multiple tool calls:")
        lines.append("<tool_calls>")
        lines.append('  <invoke name="tool1">...</invoke>')
        lines.append('  <invoke name="tool2">...</invoke>')
        lines.append("</tool_calls>")
        lines.append("")
        lines.append("Important rules:")
        lines.append("- Parameter values go between <parameter name=\"param_name\">...</parameter> tags.")
        lines.append("- Each parameter requires a SEPARATE <parameter> tag with its name attribute.")
        lines.append("- Do NOT put parameters as attributes on the <invoke> tag.")
        lines.append("- Do NOT include any explanatory text outside the <tool_calls> block when calling tools.")
        lines.append("- If parameter values contain special XML characters (<, >, &, quotes), use their entity references or place raw values between tags (the parser will handle them).")
        lines.append("")

        # === Section 4: Behavioral constraints ===
        lines.append("--- BEHAVIORAL CONSTRAINTS ---")
        lines.append("- NEVER end your turn with a promise to take action later. Execute the tool NOW if you have enough information.")
        lines.append("- If you cannot proceed because of missing information, ask the user directly instead of calling a tool with guessed values.")
        lines.append("- After receiving tool results, incorporate them into your response naturally. Do NOT repeat the raw tool output verbatim unless explicitly asked.")
        lines.append("- If a tool returns an error, explain the issue to the user and suggest alternatives. Do NOT retry the same call indefinitely.")
        lines.append("")

        # === Section 5: tool_choice enforcement ===
        if tool_choice == "required":
            lines.append("--- MANDATORY TOOL USE ---")
            lines.append("You MUST call at least one tool in your response. Do NOT respond with plain text.")
            lines.append("")
        elif tool_choice == "none":
            lines.append("--- TOOL USE PROHIBITED ---")
            lines.append("You MUST NOT call any tools. Respond only with natural language.")
            lines.append("")
        elif tool_choice == "auto":
            lines.append("--- WHEN TO USE TOOLS ---")
            lines.append("Use tools when they can provide accurate, real-time, or computed information that you cannot produce on your own.")
            lines.append("Respond with natural language when no tool is needed or when the user query is conversational.")
            lines.append("")

        return "\n".join(lines)

    def _build_text(
        self,
        messages: list[Any],
        tools: list[ToolDefinition] | None = None,
        tool_choice: str = "auto",
        context_tokens: int = 0,
    ) -> tuple[str, int]:
        """
        将 OpenAI messages 数组转换为 taiji 的纯文本。
        
        智能截断策略（确保不超过 TAIJI_MAX_TEXT_LENGTH）：
        1. 始终包含所有 system 消息和 tools prompt（最高优先级）
        2. 从后往前添加最近的对话，直到接近限制
        3. 如果连最后一条消息都放不下，则截断该消息
        4. 添加截断提示，让模型知道上下文被截断
        
        Returns:
            tuple: (构建的文本, 实际字符长度)
        
        context_tokens: taiji API 返回的当前会话上下文 token 数（暂未使用，因为 taiji 通过 sessionId 管理上下文）
        """
        # Maximum text length for taiji API request body
        max_length = self.max_text_length
        
        parts = []
        
        # === Step 1: Collect system messages (highest priority, always include) ===
        system_parts = []
        for msg in messages:
            if msg.role == "system":
                system_parts.append(f"[System]: {msg.content or ''}")
        
        # Inject tools prompt if present
        if tools:
            system_parts.append(f"[System]: {self._build_tools_prompt(tools, tool_choice)}")
        
        # Calculate system parts length
        system_text = "\n".join(system_parts)
        system_length = len(system_text)
        
        # If system alone exceeds limit, truncate it (should never happen with 800K limit)
        if system_length >= max_length:
            truncated = system_text[:max_length - 100] + "\n...(truncated)"
            return truncated, len(truncated)
        
        # === Step 2: Collect conversation messages ===
        conversation_parts = []
        for msg in reversed(messages):
            if msg.role in ("user", "assistant", "tool"):
                content = msg.content or ""
                if msg.role == "user":
                    conversation_parts.insert(0, f"[User]: {content}")
                elif msg.role == "assistant":
                    # Include tool_calls info if present
                    assistant_text = f"[Assistant]: {content}"
                    if msg.tool_calls:
                        tool_calls_info = []
                        for tc in msg.tool_calls:
                            tool_calls_info.append(
                                f"Called tool '{tc.function.name}' with args: {tc.function.arguments}"
                            )
                        assistant_text += f"\n[Tool Calls Executed]: {'; '.join(tool_calls_info)}"
                    conversation_parts.insert(0, assistant_text)
                elif msg.role == "tool":
                    conversation_parts.insert(0, f"[Tool Result for {msg.tool_call_id or 'unknown'}]: {content}")
        
        # === Step 3: Add messages from most recent until we hit the limit ===
        result_parts = system_parts.copy()
        current_length = system_length
        truncated_count = 0
        
        for part in reversed(conversation_parts):
            # Calculate length with this part (including newline separator)
            new_length = current_length + 1 + len(part)  # +1 for newline
            
            if new_length <= max_length:
                # Can fit this message
                result_parts.insert(len(system_parts), part)
                current_length = new_length
            else:
                # Cannot fit full message
                truncated_count += 1
                remaining_space = max_length - current_length - 1  # -1 for newline
                
                if remaining_space > 200:  # Only truncate if we have reasonable space
                    truncation_notice = "\n...(earlier context truncated to fit size limit)\n"
                    notice_length = len(truncation_notice)
                    
                    if remaining_space > notice_length + 100:
                        # Add truncation notice and truncated content
                        max_content_len = remaining_space - notice_length
                        truncated_content = part[-max_content_len:]  # Take from end (most recent part of old message)
                        result_parts.insert(len(system_parts), truncation_notice + truncated_content)
                        current_length = max_length
                break
        
        # Add summary of truncated messages if any
        if truncated_count > 0:
            truncation_summary = f"\n...(Note: {truncated_count} earlier message(s) were truncated or omitted due to size limits)\n"
            summary_length = len(truncation_summary)
            
            # Check if we can fit the summary
            if current_length + summary_length <= max_length:
                result_parts.insert(len(system_parts), truncation_summary)
            elif current_length < max_length:
                # Replace the first inserted truncation notice with our summary
                for i, part in enumerate(result_parts):
                    if "...(earlier context truncated" in part:
                        result_parts[i] = truncation_summary
                        break
        
        final_text = "\n".join(result_parts)
        return final_text, len(final_text)

    def _extract_json_block(self, text: str, key: str) -> str | None:
        """从文本中提取包含指定 key 的完整 JSON 对象（支持嵌套）。"""
        idx = text.find(key)
        if idx == -1:
            return None
        start = text.rfind('{', 0, idx)
        if start == -1:
            return None
        brace_count = 0
        in_string = False
        escape = False
        end = start
        while end < len(text):
            char = text[end]
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                in_string = not in_string
            elif not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return text[start:end+1]
            end += 1
        return None

    def _parse_tool_calls(self, text: str) -> list[ToolCall]:
        """
        解析模型输出中的 tool_calls。
        返回 ToolCall 对象列表；如果未检测到则返回空列表。
        
        支持三种格式：
        1. DSML XML: <｜｜DSML｜｜tool_calls><｜｜DSML｜｜invoke name="func">
        2. 标准 XML: <tool_calls><invoke name="func">
        3. JSON: {"tool_calls": [{"id": "...", "function": {...}}]}
        """
        if not text:
            return []
        
        # 优先尝试 XML 解析
        xml_result = self._parse_xml_tool_calls_format(text)
        if xml_result:
            return xml_result
        
        # JSON 回退：{"tool_calls": [...]}
        return self._parse_json_tool_calls(text)

    def _parse_json_tool_calls(self, text: str) -> list[ToolCall]:
        """解析 JSON 格式的 tool_calls: {"tool_calls": [...]}"""
        block = self._extract_json_block(text, "tool_calls")
        if not block:
            return []
        try:
            obj = json.loads(block)
            raw_tcs = obj.get("tool_calls") if isinstance(obj, dict) else None
            if not isinstance(raw_tcs, list):
                return []
            result = []
            for raw_tc in raw_tcs:
                if not isinstance(raw_tc, dict):
                    continue
                func = raw_tc.get("function") or {}
                tc_id = raw_tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                result.append(ToolCall(
                    id=tc_id,
                    type=raw_tc.get("type", "function"),
                    function=ToolCallFunction(
                        name=func.get("name", ""),
                        arguments=func.get("arguments", "{}"),
                    ),
                ))
            return result
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def _parse_xml_tool_calls_format(self, text: str) -> list[ToolCall]:
        """
        解析 XML 格式的 tool_calls。
        支持两种变体：
        1. DSML: <｜｜DSML｜｜tool_calls><｜｜DSML｜｜invoke name="func">
        2. 标准 XML: <tool_calls><invoke name="func">
        """
        if not text:
            return []
        
        # 定义要匹配的 XML 模式
        patterns = [
            # DSML 格式
            r'<｜｜DSML｜｜tool_calls>(.*?)<｜｜DSML｜｜/tool_calls>',
            # 标准 tool_calls
            r'<tool_calls>(.*?)</tool_calls>',
        ]
        
        # 如果没有闭合标签，尝试匹配开放标签到文本末尾
        open_patterns = [
            r'<｜｜DSML｜｜tool_calls>(.*)',
            r'<tool_calls>(.*)',
        ]
        
        all_matches = []
        
        # 先尝试匹配有闭合标签的
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                all_matches.extend(matches)
        
        # 如果没有找到闭合标签，尝试开放标签
        if not all_matches:
            for pattern in open_patterns:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    all_matches.append(match.group(1))
                    break
        
        if not all_matches:
            return []
        
        # 从匹配内容中提取 invoke 调用
        validated = []
        for content in all_matches:
            # 匹配 invoke 标签（支持紧凑格式，标签名和属性间可能无空格）
            invoke_pattern = r'<｜｜DSML｜｜invoke\s+name="([^"]+)"[^>]*>(.*?)(?:<｜｜DSML｜｜/invoke>|$)'
            standard_invoke = r'<invoke\s*name="([^"]+)"[^>]*>(.*?)(?:</invoke>|$)'
            
            invokes = re.findall(invoke_pattern, content, re.DOTALL)
            if not invokes:
                invokes = re.findall(standard_invoke, content, re.DOTALL)
            
            for func_name, params_str in invokes:
                # 提取参数
                arguments = {}
                
                # 匹配 DSML 参数格式: <｜｜DSML｜｜parameter name="xxx" string="true">value</｜｜DSML｜｜parameter>
                dsm_param = r'<｜｜DSML｜｜parameter\s+name="([^"]+)"[^>]*>(.*?)</｜｜DSML｜｜parameter>'
                for param_name, param_value in re.findall(dsm_param, params_str, re.DOTALL):
                    arguments[param_name] = param_value.strip()
                
                # 匹配标准参数格式: <parameter name="xxx">value</parameter>
                standard_param = r'<parameter\s*name="([^"]+)"[^>]*>(.*?)</parameter>'
                for param_name, param_value in re.findall(standard_param, params_str, re.DOTALL):
                    arguments[param_name] = param_value.strip()
                
                # 匹配简单参数格式: <key>value</key>
                simple_param = r'<([^/\s>]+)>([^<]+)</\1>'
                for param_name, param_value in re.findall(simple_param, params_str, re.DOTALL):
                    if param_name not in ('invoke', 'parameter', 'tool_calls', 'function_calls'):
                        arguments[param_name] = param_value.strip()
                
                validated.append(ToolCall(
                    id=f'toolu_{uuid.uuid4().hex[:8]}',
                    type='function',
                    function=ToolCallFunction(
                        name=func_name,
                        arguments=json.dumps(arguments, ensure_ascii=False),
                    ),
                ))
        
        return validated

    def _strip_tool_calls_from_content(self, content: str) -> str:
        """从文本中移除 XML/JSON 格式的 tool_calls 块，返回清理后的文本。"""
        xml_patterns = [
            r'<｜｜DSML｜｜tool_calls>.*?(?:<｜｜DSML｜｜/tool_calls>|$)',
            r'<tool_calls>.*?(?:</tool_calls>|$)',
        ]
        for pattern in xml_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL)
        content = content.strip()

        if content.startswith('{'):
            json_block = self._extract_json_block(content, 'tool_calls')
            if json_block:
                content = content.replace(json_block, '').strip()

        return content

    def _extract_content(self, data_obj: dict[str, Any]) -> str:
        """按优先级从 taiji 响应 JSON 中提取文本内容。"""
        for field in self.content_fields:
            if field in data_obj:
                val = data_obj[field]
                if isinstance(val, str):
                    return val
        # 兜底：返回整个 JSON 字符串
        return json.dumps(data_obj, ensure_ascii=False)

    def _strip_think_tags(self, text: str) -> tuple[str, str | None]:
        """去除模型思考过程 <think>...</think>，返回 (cleaned_text, reasoning_content)。
        当 reasoning_content 为空时返回 None。"""
        pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
        matches = pattern.findall(text)
        reasoning = "\n".join(m.strip() for m in matches if m.strip())
        cleaned = pattern.sub("", text).strip()
        return cleaned, reasoning if reasoning else None

    def _prepare_request(self, req: ChatCompletionRequest, request_id: str) -> dict[str, Any]:
        """构建 taiji API 请求的公共参数（非流式/流式共用）。"""
        original_prompt_tokens = self._count_messages_tokens(req.messages)

        # Resolve tool_choice: str or ToolChoice object -> str
        tool_choice = "auto"
        if req.tool_choice is not None:
            tool_choice = req.tool_choice if isinstance(req.tool_choice, str) else "auto"

        text, text_length = self._build_text(req.messages, req.tools, tool_choice=tool_choice)

        if text_length > self.max_text_length:
            logger_req.warning(
                f"Text length {text_length} exceeds max_text_length {self.max_text_length}, forcing hard truncation",
                extra={"request_id": request_id}
            )
            text = text[:self.max_text_length - 100] + "\n...(hard truncated)"
            text_length = len(text)

        logger_req.debug(
            f"Built text length: {text_length:,} chars (limit: {self.max_text_length:,})",
            extra={"request_id": request_id}
        )

        extra_params = {}
        if req.temperature is not None:
            extra_params["temperature"] = req.temperature
        if req.max_tokens is not None:
            extra_params["max_tokens"] = req.max_tokens
        if req.top_p is not None:
            extra_params["top_p"] = req.top_p
        if req.presence_penalty is not None:
            extra_params["presence_penalty"] = req.presence_penalty
        if req.frequency_penalty is not None:
            extra_params["frequency_penalty"] = req.frequency_penalty

        taiji_req = TaijiRequest(text=text, sessionId=self.session_id, files=[], **extra_params)

        headers = {
            "accept": "text/event-stream",
            "content-type": "application/json",
            "authorization": self.api_key,
            "x-app-version": "3.2.0",
            "origin": self.base_url,
            "referer": f"{self.base_url}/chat",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }

        cookies = {}
        if self.session_cookie:
            cookies["server_name_session"] = self.session_cookie

        url = f"{self.base_url}/api/chat/completions"

        log_headers = {k: v for k, v in headers.items() if k.lower() != "authorization"}
        logger_req.debug(
            "Calling taiji API",
            extra={
                "request_id": request_id,
                "extra": {
                    "url": url,
                    "method": "POST",
                    "headers": log_headers,
                    "cookies": cookies,
                    "body": taiji_req.model_dump(),
                },
            },
        )

        client = httpx.AsyncClient(timeout=60.0, cookies=cookies)
        return {
            "client": client,
            "url": url,
            "headers": headers,
            "taiji_req": taiji_req,
            "original_prompt_tokens": original_prompt_tokens,
        }

    def _build_stream_delta(
        self, completion_id: str, created: int, model: str, role_sent: list[bool],
        content: str | None = None, reasoning_content: str | None = None,
        tool_calls: list[ToolCall] | None = None,
    ) -> str:
        """构建流式 delta 响应 JSON 字符串。role_sent 用 list 包装以便修改。"""
        delta = ChatCompletionDelta()
        if not role_sent[0]:
            delta.role = "assistant"
            role_sent[0] = True
        if content:
            delta.content = content
        if reasoning_content:
            delta.reasoning_content = reasoning_content
        if tool_calls:
            delta.tool_calls = tool_calls
        return ChatCompletionStreamResponse(
            id=completion_id, created=created, model=model,
            choices=[ChatCompletionStreamChoice(delta=delta, finish_reason=None)],
        ).model_dump_json(ensure_ascii=False)

    def _build_finish_chunk(
        self, completion_id: str, created: int, model: str, finish_reason: str, usage: Usage,
    ) -> str:
        """构建流式结束 chunk JSON 字符串。"""
        return ChatCompletionStreamResponse(
            id=completion_id, created=created, model=model,
            choices=[ChatCompletionStreamChoice(delta=ChatCompletionDelta(), finish_reason=finish_reason)],
            usage=usage,
        ).model_dump_json(ensure_ascii=False)

    def _parse_sse_body(self, body: str) -> tuple[str, str | None, dict[str, Any]]:
        """解析 taiji 返回的 SSE 文本，提取并拼接所有 data 行内容。
        返回 (content, reasoning_content, token_info) 元组。
        token_info 包含 promptTokens, completionTokens, useTokens 等信息。"""
        contents = []
        token_info = {}
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    obj_type = obj.get("type")
                    if obj_type == "string":
                        text = self._extract_content(obj)
                        if text:
                            contents.append(text)
                    elif obj_type == "object":
                        # Extract token usage information from object type
                        obj_data = obj.get("data", {})
                        if isinstance(obj_data, dict):
                            if "promptTokens" in obj_data:
                                token_info["prompt_tokens"] = obj_data["promptTokens"]
                            if "completionTokens" in obj_data:
                                token_info["completion_tokens"] = obj_data["completionTokens"]
                            if "useTokens" in obj_data:
                                token_info["total_tokens"] = obj_data["useTokens"]
                            if "contextTokens" in obj_data:
                                token_info["context_tokens"] = obj_data["contextTokens"]
                except json.JSONDecodeError:
                    contents.append(data)
        raw = "".join(contents) if contents else body
        cleaned, reasoning = self._strip_think_tags(raw)
        return cleaned, reasoning, token_info

    async def chat_completions(self, req: ChatCompletionRequest, request_id: str) -> ChatCompletionResponse:
        prep = self._prepare_request(req, request_id)
        client = prep["client"]
        original_prompt_tokens = prep["original_prompt_tokens"]

        start = time.perf_counter()
        try:
            response = await client.post(
                prep["url"],
                headers=prep["headers"],
                json=prep["taiji_req"].model_dump(),
            )
        except httpx.TimeoutException as exc:
            raise TaijiTimeoutError(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise TaijiRequestError(str(exc)) from exc
        finally:
            await client.aclose()

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        body_text = response.text

        # 日志：调用 taiji 的 response
        logger_resp.debug(
            "Taiji API response",
            extra={
                "request_id": request_id,
                "extra": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": body_text[:5000],
                    "latency_ms": latency_ms,
                },
            },
        )

        if response.status_code != 200:
            raise TaijiHTTPError(response.status_code, body_text)

        content, reasoning_content, token_info = self._parse_sse_body(body_text)

        # taiji 有时用 HTTP 200 包装业务错误（如认证过期、无效参数）
        # 检测特征：解析后内容是 JSON 且包含 err/msg/code 字段
        if content.startswith("{"):
            try:
                err_obj = json.loads(content)
                if err_obj.get("err") or err_obj.get("msg") or err_obj.get("code", 0) != 0:
                    err_msg = err_obj.get("msg") or err_obj.get("err") or json.dumps(err_obj)
                    raise TaijiBusinessError(err_msg)
            except json.JSONDecodeError:
                pass

        # 检测是否包含 tool_calls
        raw_tool_calls = self._parse_tool_calls(content)
        if raw_tool_calls:
            content = self._strip_tool_calls_from_content(content)
            
            # If content is empty or only whitespace after removal, set to None
            if not content or not content.strip():
                content = None
            
            finish_reason = "tool_calls"
            tool_calls = raw_tool_calls
        else:
            finish_reason = "stop"
            tool_calls = None

        # Use the ORIGINAL prompt_tokens (calculated before truncation)
        # This ensures hermes-agent sees the true request size and triggers compact when needed
        prompt_tokens = original_prompt_tokens
        
        # Use completion tokens from taiji API if available, otherwise estimate
        if token_info.get("completion_tokens"):
            completion_tokens = token_info["completion_tokens"]
        else:
            # Fallback: estimate completion tokens from response content
            completion_parts = []
            if content:
                completion_parts.append(content)
            if reasoning_content:
                completion_parts.append(reasoning_content)
            if tool_calls:
                completion_parts.append(json.dumps([tc.model_dump() for tc in tool_calls], ensure_ascii=False))
            completion_text = "".join(completion_parts)
            completion_tokens = self._count_tokens(completion_text) if completion_text else 0
        
        # Always calculate total_tokens as sum of prompt and completion tokens
        # to ensure consistency (OpenAI spec requires total = prompt + completion)
        total_tokens = prompt_tokens + completion_tokens

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
            created=int(datetime.now(timezone.utc).timestamp()),
            model=req.model,
            choices=[
                ChatCompletionChoice(
                    message=ChatCompletionMessage(
                        role="assistant",
                        content=content,
                        reasoning_content=reasoning_content,
                        tool_calls=tool_calls,
                    ),
                    finish_reason=finish_reason,
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

    async def stream_chat_completions(
        self, req: ChatCompletionRequest, request_id: str
    ) -> AsyncGenerator[str, None]:
        prep = self._prepare_request(req, request_id)
        client = prep["client"]
        original_prompt_tokens = prep["original_prompt_tokens"]

        completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created = int(datetime.now(timezone.utc).timestamp())
        role_sent = [False]  # list so _build_stream_delta can mutate
        total_content = ""
        total_reasoning = ""
        token_info = {}
        think_buffer = ""
        think_closed = False
        has_tools = bool(req.tools)
        content_buffer: list[str] = []

        start = time.perf_counter()
        try:
            async with client.stream(
                "POST",
                prep["url"],
                headers=prep["headers"],
                json=prep["taiji_req"].model_dump(),
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise TaijiHTTPError(response.status_code, body.decode())

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue

                    data = line[5:].strip()
                    if data == "[DONE]":
                        break

                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    # Handle different response types
                    obj_type = obj.get("type")
                    if obj_type == "object":
                        # Extract token usage information
                        obj_data = obj.get("data", {})
                        if isinstance(obj_data, dict):
                            if "promptTokens" in obj_data:
                                token_info["prompt_tokens"] = obj_data["promptTokens"]
                            if "completionTokens" in obj_data:
                                token_info["completion_tokens"] = obj_data["completionTokens"]
                            if "useTokens" in obj_data:
                                token_info["total_tokens"] = obj_data["useTokens"]
                            if "contextTokens" in obj_data:
                                token_info["context_tokens"] = obj_data["contextTokens"]
                        continue
                    elif obj_type != "string":
                        # Check for business errors
                        if obj.get("err") or obj.get("msg") or obj.get("code", 0) != 0:
                            err_msg = obj.get("msg") or obj.get("err") or json.dumps(obj)
                            raise TaijiBusinessError(err_msg)
                        continue

                    chunk_text = self._extract_content(obj)
                    if not chunk_text:
                        continue

                    # 流式 think 标签处理：实时发送 reasoning_content 增量
                    if not think_closed:
                        # 检查当前 chunk 是否包含 think 标签
                        if "<think>" in chunk_text:
                            # 检测到 think 开始
                            think_buffer = chunk_text
                            
                            if "</think>" not in chunk_text:
                                # think 未结束，发送当前 chunk 作为 reasoning_content
                                start_pos = chunk_text.find("<think>") + len("<think>")
                                reasoning_part = chunk_text[start_pos:]
                                total_reasoning += reasoning_part
                                yield self._build_stream_delta(completion_id, created, req.model, role_sent, reasoning_content=reasoning_part)
                                continue
                            else:
                                # think 在同一 chunk 内开始并结束
                                _, full_reasoning = self._strip_think_tags(chunk_text)
                                pos = chunk_text.rfind("</think>") + len("</think>")
                                total_reasoning = full_reasoning
                                think_closed = True
                                chunk_text = chunk_text[pos:]
                        elif think_buffer:
                            # 之前的 chunk 开启了 think，当前是 continuation
                            think_buffer += chunk_text
                            
                            if "</think>" in chunk_text:
                                # think 在此 chunk 结束
                                _, full_reasoning = self._strip_think_tags(think_buffer)
                                
                                # 发送剩余的 reasoning
                                already_sent_len = len(total_reasoning)
                                remaining = full_reasoning[already_sent_len:] if already_sent_len < len(full_reasoning) else ""
                                
                                if remaining:
                                    total_reasoning = full_reasoning
                                    yield self._build_stream_delta(completion_id, created, req.model, role_sent, reasoning_content=remaining)
                                else:
                                    total_reasoning = full_reasoning
                                
                                think_closed = True
                                pos = think_buffer.rfind("</think>") + len("</think>")
                                chunk_text = think_buffer[pos:]
                                think_buffer = ""
                            else:
                                # 仍在 think 中，发送当前 chunk 作为 reasoning
                                total_reasoning += chunk_text
                                yield self._build_stream_delta(completion_id, created, req.model, role_sent, reasoning_content=chunk_text)
                                continue
                        # else: 没有 think_buffer 且当前 chunk 不含 <think>，当作普通内容处理

                    # think 已关闭或没有 think 标签，正常处理 content
                    cleaned_chunk, extra_reasoning = self._strip_think_tags(chunk_text)
                    if extra_reasoning:
                        total_reasoning += extra_reasoning
                        if not has_tools:
                            yield self._build_stream_delta(completion_id, created, req.model, role_sent, reasoning_content=extra_reasoning)
                    
                    chunk_text = cleaned_chunk
                    if not chunk_text:
                        continue

                    total_content += chunk_text

                    if has_tools:
                        # 当存在 tools 时，先缓冲内容，待流结束后统一判断是否为 tool_call
                        content_buffer.append(chunk_text)
                    else:
                        yield self._build_stream_delta(completion_id, created, req.model, role_sent, content=chunk_text, reasoning_content=extra_reasoning)

        except httpx.TimeoutException as exc:
            raise TaijiTimeoutError(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise TaijiRequestError(str(exc)) from exc
        finally:
            await client.aclose()

        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        # Use the ORIGINAL prompt_tokens (calculated before truncation)
        # This ensures hermes-agent sees the true request size and triggers compact when needed
        prompt_tokens = original_prompt_tokens

        # Use completion tokens from taiji API if available, otherwise estimate
        if token_info.get("completion_tokens"):
            completion_tokens = token_info["completion_tokens"]
        else:
            completion_parts = []
            if total_content:
                completion_parts.append(total_content)
            if total_reasoning:
                completion_parts.append(total_reasoning)
            completion_text = "".join(completion_parts)
            completion_tokens = self._count_tokens(completion_text) if completion_text else 0

        # Always calculate total_tokens as sum of prompt and completion tokens
        # to ensure consistency (OpenAI spec requires total = prompt + completion)
        total_tokens = prompt_tokens + completion_tokens

        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        # 流结束后处理 tool_calls 判定
        raw_tool_calls = []
        if has_tools:
            raw_tool_calls = self._parse_tool_calls(total_content)
            if raw_tool_calls:
                # Remove tool_calls from total_content for clean output
                remaining_text = self._strip_tool_calls_from_content(total_content)
                
                # If there's remaining text content after removing tool_calls, send it first
                if remaining_text:
                    yield self._build_stream_delta(completion_id, created, req.model, role_sent, content=remaining_text)
                
                # Then output tool_calls delta
                yield self._build_stream_delta(completion_id, created, req.model, role_sent, tool_calls=raw_tool_calls)
                yield self._build_finish_chunk(completion_id, created, req.model, "tool_calls", usage)
            else:
                # 非 tool_call，将缓冲的内容一次性输出
                for chunk_text in content_buffer:
                    yield self._build_stream_delta(completion_id, created, req.model, role_sent, content=chunk_text)
                yield self._build_finish_chunk(completion_id, created, req.model, "stop", usage)
        else:
            yield self._build_finish_chunk(completion_id, created, req.model, "stop", usage)

        # Log streaming response summary
        logger_resp.debug(
            "Taiji API response (streaming)",
            extra={
                "request_id": request_id,
                "extra": {
                    "latency_ms": latency_ms,
                    "total_content_length": len(total_content),
                    "total_reasoning_length": len(total_reasoning),
                    "has_tools": has_tools,
                    "parsed_tool_calls_count": len(raw_tool_calls),
                    "total_content_preview": total_content[:500] if total_content else None,
                    "total_reasoning_preview": total_reasoning[:500] if total_reasoning else None,
                    "tool_call_detected": bool(raw_tool_calls),
                },
            },
        )

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
        self.text_to_image: bool = settings.TAIJI_TEXT_TO_IMAGE
        self.text_image_max: int = settings.TAIJI_TEXT_IMAGE_MAX
        self.web_search: bool = settings.TAIJI_WEB_SEARCH
        self.thinking: bool = settings.TAIJI_THINKING

    async def close(self) -> None:
        """释放资源（当前无持久连接，预留接口）。"""

    def _get_tokenizer(self) -> Any:
        """Lazy load tiktoken encoder (attempt only once)."""
        if not hasattr(self, '_tokenizer_tried'):
            self._tokenizer_tried = True
            try:
                import tiktoken
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except ImportError:
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
                total += self._count_tokens(self._extract_text_from_content(msg.content))
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

        # === Section 2: Response format (XML/DSML) ===
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

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Multimodal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text_from_content(content: Any) -> str:
        """从 content 中提取纯文本，兼容 str 和多模态 list 格式。

        支持:
        - str: 直接返回
        - list[ContentPart]: 拼接所有 type=text 的文本
        - None: 返回空字符串
        """
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        # list of ContentPart (multimodal)
        parts = []
        for item in content:
            if hasattr(item, "type"):
                # Pydantic model (ContentPart)
                if item.type == "text" and item.text:
                    parts.append(item.text)
            elif isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    parts.append(item["text"])
        return " ".join(parts)

    @staticmethod
    def _extract_files(messages: list[Any]) -> list[dict[str, Any]]:
        """从 messages 中提取 image_url 转为 Taiji files 格式。

        遍历所有 user 消息的 content，找到 type=image_url 的部分，
        转换为 Taiji 的 {name, data} 格式（data 为 base64 data URI）。

        Taiji 限制：最多 5 个文件，每个 ≤ 5MB。
        """
        files = []
        MAX_FILES = 5
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in chars (base64 is ~4/3 of binary)

        for msg in messages:
            if msg.role != "user":
                continue
            content = msg.content
            if not isinstance(content, list):
                continue
            for item in content:
                if len(files) >= MAX_FILES:
                    break

                # Get type and image_url
                if hasattr(item, "type"):
                    item_type = item.type
                    image_url = item.image_url
                elif isinstance(item, dict):
                    item_type = item.get("type")
                    image_url = item.get("image_url")
                else:
                    continue

                if item_type != "image_url" or not image_url:
                    continue

                url = image_url.get("url", "") if isinstance(image_url, dict) else ""
                if not url.startswith("data:"):
                    continue

                # Check size
                if len(url) > MAX_FILE_SIZE:
                    continue

                # Determine file extension from data URI
                ext = ".jpg"
                if "image/png" in url:
                    ext = ".png"
                elif "image/gif" in url:
                    ext = ".gif"
                elif "image/webp" in url:
                    ext = ".webp"

                files.append({
                    "name": f"image_{len(files) + 1}{ext}",
                    "data": url,
                })

        return files

    # ------------------------------------------------------------------
    # Text-to-image rendering (context overflow expansion)
    # ------------------------------------------------------------------

    @staticmethod
    def _render_text_to_images(
        text: str,
        max_images: int = 5,
        img_width: int = 4800,
        img_height: int = 8000,
        font_size: int = 10,
        line_height: int = 11,
        margin: int = 16,
    ) -> list[dict[str, Any]]:
        """将文本渲染为图片列表，充分利用 5MB/张 的附件限额。

        当 text 字段超过长度限制时，将全部文本渲染为图片，
        通过 Taiji files 字段发送，利用 OCR 能力还原上下文。

        容量: ~720 行/张 × ~780 字符/行 ≈ 单张 ~100K+ 字符
               5 张总容量: ~250K-500K 字符

        Args:
            text: 需要渲染的文本内容
            max_images: 最大图片数 (Taiji 限制 ≤5)
            img_width: 图片宽度 (px)
            img_height: 图片高度 (px)
            font_size: 字体大小
            line_height: 行高 (px)
            margin: 页边距 (px)

        Returns:
            list of {name, data} dicts (Taiji files 格式)
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger_req.warning("Pillow not installed, text-to-image disabled")
            return []

        if not text:
            return []

        # Load font (prefer Chinese-compatible system fonts)
        font = None
        for font_path in (
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except (OSError, IOError):
                continue
        if font is None:
            font = ImageFont.load_default()

        # Calculate layout
        max_lines_per_image = (img_height - 2 * margin) // line_height
        # Estimate chars per line based on image width and font
        chars_per_line = max(80, (img_width - 2 * margin) // (font_size // 2 + 1))

        # Split text into lines
        text_lines = []
        for raw_line in text.split("\n"):
            while len(raw_line) > chars_per_line:
                text_lines.append(raw_line[:chars_per_line])
                raw_line = raw_line[chars_per_line:]
            text_lines.append(raw_line)

        # Split into pages
        pages = []
        for i in range(0, len(text_lines), max_lines_per_image):
            pages.append(text_lines[i : i + max_lines_per_image])
            if len(pages) >= max_images:
                break

        # Render each page to image (JPEG preferred for smaller size)
        import io
        import base64

        total_pages = min(len(pages), max_images)

        files = []
        for page_idx, page_lines in enumerate(pages):
            if page_idx >= total_pages:
                break

            img = Image.new("RGB", (img_width, img_height), "white")
            draw = ImageDraw.Draw(img)

            # Add header with page order info
            header = f"--- Page {page_idx + 1} of {total_pages} ---"
            draw.text((margin, margin), header, fill="gray", font=font)
            y = margin + line_height + 4

            for line_text in page_lines:
                draw.text((margin, y), line_text, fill="black", font=font)
                y += line_height

            # Add page indicator at bottom
            draw.text(
                (img_width - 200, img_height - 30),
                f"Page {page_idx + 1}/{total_pages}",
                fill="gray",
                font=font,
            )

            # Encode as base64 data URI (try JPEG first for smaller size, fallback PNG)
            buf = io.BytesIO()
            try:
                img.save(buf, format="JPEG", quality=75, optimize=True)
                mime = "image/jpeg"
                ext = "jpg"
            except Exception:
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                mime = "image/png"
                ext = "png"
            b64_data = base64.b64encode(buf.getvalue()).decode()
            data_uri = f"data:{mime};base64,{b64_data}"
            img_size_kb = len(buf.getvalue()) / 1024

            # Skip if exceeds 5MB base64 limit
            if len(data_uri) > 5 * 1024 * 1024:
                logger_req.warning(
                    f"Rendered image {page_idx + 1} exceeds 5MB "
                    f"({len(data_uri) / 1024 / 1024:.1f}MB base64), skipping",
                )
                continue

            files.append({
                "name": f"context_page_{page_idx + 1}.{ext}",
                "data": data_uri,
            })
            logger_req.debug(
                f"Image {page_idx + 1}/{total_pages}: {len(page_lines)} lines, "
                f"{img_size_kb:.0f}KB ({len(data_uri) / 1024 / 1024:.1f}MB base64)",
            )

        return files

    def _build_text(
        self,
        messages: list[Any],
        tools: list[ToolDefinition] | None = None,
        tool_choice: str = "auto",
    ) -> tuple[str, int]:
        """
        将 OpenAI messages 数组转换为 taiji 的纯文本。
        
        本方法只做渲染，不做截断。文本溢出由 _prepare_request 的
        text_to_image 机制处理（旧对话转图片）。
        """
        # === Step 1: Collect system messages ===
        system_parts = []
        for msg in messages:
            if msg.role == "system":
                system_parts.append(f"[System]: {self._extract_text_from_content(msg.content)}")
        
        # Inject tools prompt if present
        if tools:
            system_parts.append(f"[System]: {self._build_tools_prompt(tools, tool_choice)}")
        
        # === Step 2: Collect conversation messages ===
        conversation_parts = []
        for msg in reversed(messages):
            if msg.role in ("user", "assistant", "tool"):
                content = self._extract_text_from_content(msg.content)
                if msg.role == "user":
                    conversation_parts.insert(0, f"[User]: {content}")
                elif msg.role == "assistant":
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
        
        # === Step 3: Combine (no truncation — overflow handled by image conversion) ===
        all_parts = system_parts + conversation_parts
        final_text = "\n".join(all_parts)
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
        当 reasoning_content 为空时返回 None。
        注意：不做 strip()，保留原始空白（包括换行符），避免流式 chunk 中的
        纯空白/换行 chunk 被误删导致输出丢失换行。"""
        pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
        matches = pattern.findall(text)
        reasoning = "\n".join(m.strip() for m in matches if m.strip())
        cleaned = pattern.sub("", text)
        return cleaned, reasoning if reasoning else None

    def _prepare_request(self, req: ChatCompletionRequest, request_id: str) -> dict[str, Any]:
        """构建 taiji API 请求的公共参数（非流式/流式共用）。"""
        # Resolve tool_choice first (used for both token counting and request building)
        tool_choice = "auto"
        if req.tool_choice is not None:
            tool_choice = req.tool_choice if isinstance(req.tool_choice, str) else "auto"

        # Count prompt tokens: messages + tools schema
        original_prompt_tokens = self._count_messages_tokens(req.messages)
        if req.tools:
            tools_text = self._build_tools_prompt(req.tools, tool_choice)
            original_prompt_tokens += self._count_tokens(tools_text)

        # Build text — tools always stay in text (needed for tool_calls), overflow only conversation
        tools_prompt = ""
        if req.tools:
            tools_prompt = self._build_tools_prompt(req.tools, tool_choice)

        if self.text_to_image:
            # Build conversation text (without tools) — full, no truncation
            conv_text, conv_length = self._build_text(
                req.messages, tools=None, tool_choice=tool_choice,
            )
            # Default text: tools + conversation combined
            if tools_prompt:
                text = f"[System]: {tools_prompt}\n{conv_text}"
            else:
                text = conv_text
            text_length = len(text)
        else:
            text, text_length = self._build_text(
                req.messages, req.tools, tool_choice=tool_choice,
            )
            conv_text = text
            conv_length = text_length

        # Extract user-provided image attachments from multimodal content
        user_files = self._extract_files(req.messages)
        overflow_images: list[dict[str, Any]] = []

        # Check if tools + conversation exceeds limit
        combined_length = len(tools_prompt) + 1 + conv_length if tools_prompt else conv_length

        if combined_length > self.max_text_length:
            if self.text_to_image:
                # Tools stay in text; overflow old conversation to images
                tools_budget = len(tools_prompt) + 200 if tools_prompt else 0
                tail_budget = min(
                    self.max_text_length - tools_budget - 200,  # -200 for notice
                    10000,  # cap at 10K for recent conversation
                )
                tail_budget = max(tail_budget, 1000)  # at least 1K
                split_at = max(0, conv_length - tail_budget)

                # Align to message boundary
                if split_at > 0:
                    boundary = conv_text.find("\n[", split_at)
                    if boundary != -1 and boundary < conv_length - 200:
                        split_at = boundary + 1

                if split_at > 0 and split_at < conv_length:
                    image_text = conv_text[:split_at]
                    kept_conv = conv_text[split_at:]
                else:
                    image_text = conv_text
                    kept_conv = ""

                overflow_images = self._render_text_to_images(
                    image_text, max_images=self.text_image_max
                ) if image_text else []

                # Measure system vs conversation split in overflow
                sys_boundary = conv_length
                for tag in ("\n[User]: ", "\n[Assistant]: ", "\n[Tool Result"):
                    idx = conv_text.find(tag)
                    if idx != -1 and idx < sys_boundary:
                        sys_boundary = idx

                logger_req.info(
                    f"Text overflow: {len(image_text):,} chars → {len(overflow_images)} image(s), "
                    f"system={sys_boundary:,} tools={len(tools_prompt):,} "
                    f"old_conv={len(image_text)-sys_boundary:,} "
                    f"recent_conv={len(kept_conv):,}",
                    extra={"request_id": request_id},
                )

                # Assemble: tools + notice + recent conversation
                parts = []
                if tools_prompt:
                    parts.append(f"[System]: {tools_prompt}")
                if overflow_images:
                    parts.append(
                        f"[System]: 早期对话已转为 {len(overflow_images)} 张图片附件，请按顺序读取。"
                    )
                if kept_conv:
                    parts.append(kept_conv)
                text = "\n".join(parts)
                text_length = len(text)
            else:
                logger_req.warning(
                    f"Text length {text_length} exceeds max_text_length {self.max_text_length}, "
                    "text_to_image is disabled — Taiji may reject this request",
                    extra={"request_id": request_id},
                )

        # Per-request override: client value takes priority, fallback to server config
        web_search = req.web_search if req.web_search is not None else self.web_search
        thinking = req.thinking if req.thinking is not None else self.thinking

        logger_req.info(
            f"Prepared: text={text_length:,} chars (limit: {self.max_text_length:,}), "
            f"overflow_images={len(overflow_images)}, user_files={len(user_files)}, "
            f"tools={bool(req.tools)}, text_to_image={self.text_to_image}, "
            f"webSearch={web_search}, thinking={thinking}",
            extra={"request_id": request_id},
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

        # Merge user files + overflow images (respect 5-file limit)
        MAX_TOTAL_FILES = 5
        files = list(user_files)
        remaining_slots = MAX_TOTAL_FILES - len(files)
        if overflow_images and remaining_slots > 0:
            files.extend(overflow_images[:remaining_slots])
        if user_files:
            logger_req.debug(
                f"Extracted {len(user_files)} user file attachment(s) from messages",
                extra={"request_id": request_id},
            )

        taiji_req = TaijiRequest(
            text=text,
            sessionId=self.session_id,
            files=files,
            webSearch=web_search,
            thinking=thinking,
            **extra_params,
        )

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

        # Build log-safe body (mask base64 data in files)
        log_body = taiji_req.model_dump()
        if log_body.get("files"):
            log_body["files"] = [
                {"name": f["name"], "data": f"{f['data'][:50]}...(truncated, {len(f['data'])} chars)"}
                for f in log_body["files"]
            ]

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
                    "body": log_body,
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

                    # Check for business errors on ALL types (including "string")
                    if obj.get("err") or obj.get("msg") or obj.get("code", 0) != 0:
                        err_msg = obj.get("msg") or obj.get("data") or obj.get("err") or json.dumps(obj)
                        raise TaijiBusinessError(err_msg)

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

                    # Check for business errors on ALL types (including "string")
                    # Taiji may return errors as {"type":"string","data":"...","code":1}
                    if obj.get("err") or obj.get("msg") or obj.get("code", 0) != 0:
                        err_msg = obj.get("msg") or obj.get("data") or obj.get("err") or json.dumps(obj)
                        raise TaijiBusinessError(err_msg)

                    if obj_type != "string":
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
                        # Always stream reasoning_content to client (hermes needs it even with tools)
                        yield self._build_stream_delta(completion_id, created, req.model, role_sent, reasoning_content=extra_reasoning)
                    
                    chunk_text = cleaned_chunk
                    if not chunk_text:
                        continue

                    total_content += chunk_text

                    if has_tools:
                        # 当存在 tools 时，先缓冲内容，待流结束后统一判断是否为 tool_call
                        content_buffer.append(chunk_text)
                    else:
                        yield self._build_stream_delta(completion_id, created, req.model, role_sent, content=chunk_text)

        except httpx.TimeoutException as exc:
            raise TaijiTimeoutError(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise TaijiRequestError(str(exc)) from exc
        except (TaijiBusinessError, TaijiHTTPError) as exc:
            logger_resp.error(
                f"Taiji streaming business error: {exc}",
                extra={
                    "request_id": request_id,
                    "extra": {
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                        "content_collected": total_content[:200] if total_content else None,
                    },
                },
            )
            raise
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

        # --- Enhanced streaming response summary ---
        finish_reason = "tool_calls" if raw_tool_calls else "stop"
        tool_call_names = [tc.function.name for tc in raw_tool_calls] if raw_tool_calls else []
        tool_call_details = []
        for tc in raw_tool_calls:
            args_preview = str(tc.function.arguments)[:100]
            tool_call_details.append(f"{tc.function.name}({args_preview})")

        summary_extra = {
            "latency_ms": latency_ms,
            "total_content_length": len(total_content),
            "total_reasoning_length": len(total_reasoning),
            "has_tools": has_tools,
            "parsed_tool_calls_count": len(raw_tool_calls),
            "tool_call_names": tool_call_names,
            "tool_call_details": tool_call_details,
            "finish_reason": finish_reason,
            "total_content_preview": total_content[:800] if total_content else None,
            "total_reasoning_preview": total_reasoning[:300] if total_reasoning else None,
        }

        # Detect potential missed tool calls: tools were requested, content has
        # tool-like patterns, but parser returned 0 results
        if has_tools and not raw_tool_calls and total_content:
            import re as _re
            tool_like = bool(_re.search(r'<invoke|<tool_call|"function"|"tool_calls"', total_content, _re.IGNORECASE))
            summary_extra["potential_missed_tool_call"] = tool_like
            summary_extra["content_snippet_for_review"] = total_content[:1500]
            if tool_like:
                logger_resp.warning(
                    f"Potential missed tool call: content has tool-like patterns but parser returned 0 results",
                    extra={
                        "request_id": request_id,
                        "extra": {
                            "content_length": len(total_content),
                            "content_preview": total_content[:1000],
                        },
                    },
                )

        logger_resp.info(
            f"Streaming response: {len(total_content)} chars, "
            f"tools={len(raw_tool_calls)} ({','.join(tool_call_names) if tool_call_names else 'none'}), "
            f"finish={finish_reason}, latency={latency_ms:.0f}ms",
            extra={"request_id": request_id, "extra": summary_extra},
        )

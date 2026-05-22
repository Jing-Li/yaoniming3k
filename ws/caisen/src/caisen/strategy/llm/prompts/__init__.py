"""Prompt 模板模块"""

from .default import (
    SYSTEM_PROMPT,
    RULES_FRAMEWORK,
    OUTPUT_FORMAT,
    EXAMPLES_TEMPLATE,
    get_prompt_template,
    PromptTemplate,
)

__all__ = [
    "SYSTEM_PROMPT",
    "RULES_FRAMEWORK",
    "OUTPUT_FORMAT",
    "EXAMPLES_TEMPLATE",
    "get_prompt_template",
    "PromptTemplate",
]
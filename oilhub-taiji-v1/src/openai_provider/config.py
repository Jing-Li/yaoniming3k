"""应用配置模块。

所有配置项通过环境变量读取，支持 .env 文件和默认值兜底。
使用 pydantic BaseSettings 实现自动类型验证。
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置。

    读取顺序：环境变量 > .env 文件 > 默认值。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Taiji 后端 ---
    TAIJI_BASE_URL: str = "https://ai.avuuq.cn"
    TAIJI_API_KEY: str = ""
    # 实测 taiji 单条 text 最大字符数约 830000；保守设置 800000
    TAIJI_MAX_TEXT_LENGTH: int = Field(default=800000, ge=1000)
    # 从 taiji SSE 响应中提取文本内容的字段名（逗号分隔，按优先级尝试）
    TAIJI_CONTENT_FIELDS: str = "data,content,text,message,answer,result"
    # taiji 会话标识
    TAIJI_SESSION_ID: int = 0
    TAIJI_SESSION_COOKIE: str = ""

    # --- 文本转图片扩容 ---
    # 当 text 超过 max_text_length 时，将截断部分渲染为图片附件发送给 Taiji
    TAIJI_TEXT_TO_IMAGE: bool = False
    TAIJI_TEXT_IMAGE_MAX: int = Field(default=5, ge=1, le=5)  # 最大图片数

    # --- Taiji 高级能力 ---
    TAIJI_WEB_SEARCH: bool = False   # 开启联网搜索
    TAIJI_THINKING: bool = False     # 开启深度思考

    # --- Provider 认证（可选）---
    API_KEY: str = ""

    # --- 服务监听 ---
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = Field(default=8080, ge=1, le=65535)

    # --- 模型能力（通过 /v1/models 暴露）---
    MODEL_CONTEXT_LENGTH: int = Field(default=200000, ge=1)
    MODEL_MAX_COMPLETION_TOKENS: int = Field(default=4096, ge=1)

    # --- CORS ---
    CORS_ORIGINS: str = "*"

    @property
    def content_fields_list(self) -> list[str]:
        """解析 TAIJI_CONTENT_FIELDS 为列表。"""
        return [f.strip() for f in self.TAIJI_CONTENT_FIELDS.split(",") if f.strip()]


settings = Settings()

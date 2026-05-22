import os


class Settings:
    TAIJI_BASE_URL: str = os.getenv("TAIJI_BASE_URL", "https://ai.aurod.cn")
    TAIJI_API_KEY: str = os.getenv("TAIJI_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjE4MTEwLCJzaWduIjoiODUyMmY5NjhhY2RhMmViZWY3YzlkMTc5NTdhZDA5ZjYiLCJyb2xlIjoidXNlciIsImV4cCI6MTc3OTg0Nzg3NSwibmJmIjoxNzc4NTUxODc1LCJpYXQiOjE3Nzg1NTE4NzV9.b6SbcdFNc3NHotxGDKYlmOmgq2oPIuNC0eGTcg1t4Vs")
    # 实测 taiji 单条 text 最大字符数约 830000
    # 保守设置 800000，确保稳定返回
    TAIJI_MAX_TEXT_LENGTH: int = int(os.getenv("TAIJI_MAX_TEXT_LENGTH", "800000"))
    # 从 taiji SSE 响应中提取文本内容的字段名（逗号分隔，按优先级尝试）
    # 实测 taiji 用 "data" 字段承载内容
    TAIJI_CONTENT_FIELDS: str = os.getenv("TAIJI_CONTENT_FIELDS", "data,content,text,message,answer,result")
    # 实测 taiji 需要有效的 sessionId 和 server_name_session cookie
    TAIJI_SESSION_ID: int = int(os.getenv("TAIJI_SESSION_ID", "658084"))
    TAIJI_SESSION_COOKIE: str = os.getenv("TAIJI_SESSION_COOKIE", "e8573afc12a94d36c85627cd71788200")

    # Provider 自身认证（可选）：若设置，客户端请求需携带 Authorization: Bearer <token>
    API_KEY: str = os.getenv("API_KEY", "")

    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8080"))


settings = Settings()

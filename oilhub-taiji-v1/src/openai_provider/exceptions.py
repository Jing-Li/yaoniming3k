"""自定义异常体系。

将 TaijiProvider 中散落的裸 Exception 替换为结构化异常，
使调用方能够精确区分超时、HTTP 错误和业务错误。
"""


class ProviderError(Exception):
    """所有 Provider 错误的基类。"""


class TaijiTimeoutError(ProviderError):
    """Taiji API 请求超时。"""

    def __init__(self, message: str = "") -> None:
        msg = f"Taiji API timeout: {message}" if message else "Taiji API timeout"
        super().__init__(msg)


class TaijiHTTPError(ProviderError):
    """Taiji API 返回非 200 HTTP 状态码。"""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Taiji API error: HTTP {status_code} - {message[:500]}")


class TaijiBusinessError(ProviderError):
    """Taiji API 用 HTTP 200 包装的业务错误（err/msg/code 字段）。"""

    def __init__(self, message: str) -> None:
        super().__init__(f"Taiji business error: {message}")


class TaijiRequestError(ProviderError):
    """Taiji API 网络层错误（DNS、连接拒绝等）。"""

    def __init__(self, message: str) -> None:
        super().__init__(f"Taiji API request failed: {message}")

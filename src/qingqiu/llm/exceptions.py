"""LLM 抽象层异常体系"""

from __future__ import annotations


class LLMError(Exception):
    """LLM 相关错误基类"""


class ProviderNotFoundError(LLMError):
    """找不到指定的 provider"""


class ProviderInitError(LLMError):
    """Provider 初始化失败（如 API key 缺失 / URL 不对）"""


class ProviderAPIError(LLMError):
    """Provider API 返回错误"""


class RateLimitError(ProviderAPIError):
    """触发 provider rate limit"""


class StreamCancelledError(LLMError):
    """流式响应被取消"""
"""LLM 抽象层 · 4 个 provider + 路由器 + 工厂"""

from qingqiu.llm.base import LLMProvider, LLMResponse, Message
from qingqiu.llm.openai_provider import OpenAIProvider
from qingqiu.llm.anthropic_provider import AnthropicProvider
from qingqiu.llm.ollama_provider import OllamaProvider
from qingqiu.llm.custom_provider import CustomProvider
from qingqiu.llm.router import LLMRouter
from qingqiu.llm.exceptions import (
    LLMError,
    ProviderNotFoundError,
    ProviderInitError,
    ProviderAPIError,
    RateLimitError,
    StreamCancelledError,
)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "Message",
    "LLMRouter",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "CustomProvider",
    "LLMError",
    "ProviderNotFoundError",
    "ProviderInitError",
    "ProviderAPIError",
    "RateLimitError",
    "StreamCancelledError",
    "get_provider",
    "PROVIDERS",
]


# Provider 工厂表（用于 get_provider 和 CLI）
PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "custom": CustomProvider,
}


def get_provider(name: str, **kwargs: object) -> LLMProvider:
    """按名字获取 provider 实例

    Args:
        name: provider 名（"openai" / "anthropic" / "ollama" / "custom"）
        kwargs: 传给 provider 构造函数的参数（如 api_key / base_url）

    Returns:
        LLMProvider 实例
    """
    if name not in PROVIDERS:
        raise ProviderNotFoundError(
            f"Unknown provider '{name}'. Available: {sorted(PROVIDERS.keys())}"
        )
    return PROVIDERS[name](**kwargs)
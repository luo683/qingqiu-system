"""__init__.py 导出 + 工厂函数测试"""

import pytest

from qingqiu.llm import (
    PROVIDERS,
    get_provider,
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider,
    CustomProvider,
    ProviderNotFoundError,
)


def test_providers_registry_has_all_four():
    assert set(PROVIDERS.keys()) == {"openai", "anthropic", "ollama", "custom"}


def test_providers_registry_classes():
    assert PROVIDERS["openai"] is OpenAIProvider
    assert PROVIDERS["anthropic"] is AnthropicProvider
    assert PROVIDERS["ollama"] is OllamaProvider
    assert PROVIDERS["custom"] is CustomProvider


def test_get_provider_unknown_raises():
    with pytest.raises(ProviderNotFoundError, match="nonexistent"):
        get_provider("nonexistent")


def test_get_provider_openai_without_key_raises():
    """openai 缺 API key 应该 raise ValueError（不是 ProviderNotFoundError）"""
    import os
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    with pytest.raises(ValueError):
        get_provider("openai")


def test_get_provider_ollama_no_env_ok():
    """ollama 不需要 API key，只用默认 host"""
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("OLLAMA_HOST", raising=False)
        provider = get_provider("ollama")
        assert isinstance(provider, OllamaProvider)


def test_get_provider_custom_without_url_raises():
    import os
    env_backup = os.environ.pop("CUSTOM_LLM_URL", None)
    try:
        with pytest.raises(ValueError, match="CUSTOM_LLM_URL"):
            get_provider("custom")
    finally:
        if env_backup is not None:
            os.environ["CUSTOM_LLM_URL"] = env_backup


def test_get_provider_with_kwargs():
    """get_provider 接受 kwargs 传给构造函数"""
    from unittest.mock import patch
    with patch("qingqiu.llm.openai_provider.AsyncOpenAI"):
        provider = get_provider("openai", api_key="sk-test", default_model="gpt-4o")
        assert provider.default_model == "gpt-4o"
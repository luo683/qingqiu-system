"""Anthropic provider 测试 · 用 mock"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qingqiu.llm.base import Message
from qingqiu.llm.anthropic_provider import AnthropicProvider


def test_init_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider()


def test_init_with_api_key():
    with patch("qingqiu.llm.anthropic_provider.AsyncAnthropic"):
        provider = AnthropicProvider(api_key="sk-ant-test")
        assert provider.name == "anthropic"
        assert provider.default_model == "claude-sonnet-4-5"


def test_init_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
    with patch("qingqiu.llm.anthropic_provider.AsyncAnthropic"):
        provider = AnthropicProvider()
        assert provider.api_key == "sk-ant-env"


def test_split_system():
    system, rest = AnthropicProvider._split_system([
        Message("system", "you are helpful"),
        Message("user", "hi"),
        Message("assistant", "hello"),
    ])
    assert system == "you are helpful"
    assert rest == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_split_system_no_system():
    system, rest = AnthropicProvider._split_system([
        Message("user", "hi"),
    ])
    assert system is None
    assert rest == [{"role": "user", "content": "hi"}]


async def test_complete_returns_llm_response():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Hello from Anthropic")]
    mock_response.model = "claude-sonnet-4-5"
    mock_response.usage.input_tokens = 8
    mock_response.usage.output_tokens = 4

    with patch("qingqiu.llm.anthropic_provider.AsyncAnthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        provider = AnthropicProvider(api_key="sk-ant-test")
        response = await provider.complete([Message("user", "hi")])

        assert response.content == "Hello from Anthropic"
        assert response.model == "claude-sonnet-4-5"
        assert response.provider == "anthropic"
        assert response.usage == {"input_tokens": 8, "output_tokens": 4}


async def test_complete_passes_system_separately():
    with patch("qingqiu.llm.anthropic_provider.AsyncAnthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_create = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="ok")]
        mock_response.model = "claude-sonnet-4-5"
        mock_response.usage.input_tokens = 5
        mock_response.usage.output_tokens = 2
        mock_create.return_value = mock_response
        mock_client.messages.create = mock_create

        provider = AnthropicProvider(api_key="sk-ant-test")
        await provider.complete([
            Message("system", "be brief"),
            Message("user", "hi"),
        ])

        kwargs = mock_create.call_args.kwargs
        assert kwargs.get("system") == "be brief"
        # system message 不应在 messages 里
        for m in kwargs["messages"]:
            assert m["role"] != "system"
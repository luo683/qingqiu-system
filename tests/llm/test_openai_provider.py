"""OpenAI provider 测试 · 用 mock 不实际调用 API"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qingqiu.llm.base import Message
from qingqiu.llm.openai_provider import OpenAIProvider


def test_init_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIProvider()


def test_init_with_api_key():
    with patch("qingqiu.llm.openai_provider.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test")
        assert provider.name == "openai"
        assert provider.default_model == "gpt-4o-mini"


def test_init_with_custom_model():
    with patch("qingqiu.llm.openai_provider.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test", default_model="gpt-4o")
        assert provider.default_model == "gpt-4o"


def test_init_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-test")
    with patch("qingqiu.llm.openai_provider.AsyncOpenAI"):
        provider = OpenAIProvider()
        assert provider.api_key == "sk-env-test"


async def test_complete_returns_llm_response():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Hello from OpenAI"))]
    mock_response.model = "gpt-4o-mini"
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 3

    with patch("qingqiu.llm.openai_provider.AsyncOpenAI") as MockClient:
        mock_client = MockClient.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = OpenAIProvider(api_key="sk-test")
        response = await provider.complete([Message("user", "hi")])

        assert response.content == "Hello from OpenAI"
        assert response.model == "gpt-4o-mini"
        assert response.provider == "openai"
        assert response.usage == {"input_tokens": 5, "output_tokens": 3}


async def test_complete_with_json_mode():
    with patch("qingqiu.llm.openai_provider.AsyncOpenAI") as MockClient:
        mock_client = MockClient.return_value
        mock_create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"key": "val"}'))]
        mock_response.model = "gpt-4o-mini"
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 3
        mock_create.return_value = mock_response
        mock_client.chat.completions.create = mock_create

        provider = OpenAIProvider(api_key="sk-test")
        await provider.complete(
            [Message("user", "give json")], json_mode=True
        )

        # 验证 json_mode 传给 SDK
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}
"""Custom provider 测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qingqiu.llm.base import Message
from qingqiu.llm.custom_provider import CustomProvider


def test_init_requires_url(monkeypatch):
    monkeypatch.delenv("CUSTOM_LLM_URL", raising=False)
    monkeypatch.delenv("CUSTOM_LLM_API_KEY", raising=False)
    monkeypatch.delenv("CUSTOM_LLM_MODEL", raising=False)
    with pytest.raises(ValueError, match="CUSTOM_LLM_URL"):
        CustomProvider()


def test_init_with_url_only(monkeypatch):
    monkeypatch.delenv("CUSTOM_LLM_URL", raising=False)
    monkeypatch.delenv("CUSTOM_LLM_API_KEY", raising=False)
    monkeypatch.delenv("CUSTOM_LLM_MODEL", raising=False)
    with patch("qingqiu.llm.custom_provider.httpx.AsyncClient"):
        provider = CustomProvider(base_url="https://api.example.com/v1")
        assert provider.base_url == "https://api.example.com/v1"
        assert provider.default_model == "custom-model"  # fallback


def test_init_from_env(monkeypatch):
    monkeypatch.setenv("CUSTOM_LLM_URL", "https://api.example.com/v1")
    monkeypatch.setenv("CUSTOM_LLM_API_KEY", "sk-custom")
    monkeypatch.setenv("CUSTOM_LLM_MODEL", "glm-4")
    with patch("qingqiu.llm.custom_provider.httpx.AsyncClient"):
        provider = CustomProvider()
        assert provider.base_url == "https://api.example.com/v1"
        assert provider.api_key == "sk-custom"
        assert provider.default_model == "glm-4"


async def test_complete_returns_llm_response():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello from custom"}}],
        "model": "glm-4",
        "usage": {"prompt_tokens": 7, "completion_tokens": 5},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("qingqiu.llm.custom_provider.httpx.AsyncClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.post = AsyncMock(return_value=mock_response)

        provider = CustomProvider(base_url="https://api.example.com/v1")
        response = await provider.complete([Message("user", "hi")])

        assert response.content == "Hello from custom"
        assert response.model == "glm-4"
        assert response.provider == "custom"
        assert response.usage == {"input_tokens": 7, "output_tokens": 5}


async def test_complete_passes_auth_header():
    with patch("qingqiu.llm.custom_provider.httpx.AsyncClient") as MockClient:
        mock_client = MockClient.return_value
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "model": "x",
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        provider = CustomProvider(base_url="https://api.example.com/v1", api_key="sk-test")
        await provider.complete([Message("user", "hi")])

        # 验证 client 初始化时带了 Authorization header
        MockClient.assert_called_once()
        call_kwargs = MockClient.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer sk-test"
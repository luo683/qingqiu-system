"""Ollama provider 测试 · httpx mock"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qingqiu.llm.base import Message
from qingqiu.llm.ollama_provider import OllamaProvider


def test_init_default_host():
    with patch("qingqiu.llm.ollama_provider.httpx.AsyncClient"):
        provider = OllamaProvider()
        assert provider.host == "http://127.0.0.1:11434"
        assert provider.default_model == "llama3.1"
        assert provider.embed_model == "nomic-embed-text"


def test_init_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://192.168.1.10:11434")
    with patch("qingqiu.llm.ollama_provider.httpx.AsyncClient"):
        provider = OllamaProvider()
        assert provider.host == "http://192.168.1.10:11434"


def test_init_custom_params():
    with patch("qingqiu.llm.ollama_provider.httpx.AsyncClient"):
        provider = OllamaProvider(
            host="http://gpu:11434",
            default_model="qwen2.5",
            embed_model="bge-m3",
        )
        assert provider.host == "http://gpu:11434"
        assert provider.default_model == "qwen2.5"
        assert provider.embed_model == "bge-m3"


async def test_complete_returns_llm_response():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": "Hello from Ollama"},
        "model": "llama3.1",
        "prompt_eval_count": 6,
        "eval_count": 4,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("qingqiu.llm.ollama_provider.httpx.AsyncClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.post = AsyncMock(return_value=mock_response)

        provider = OllamaProvider()
        response = await provider.complete([Message("user", "hi")])

        assert response.content == "Hello from Ollama"
        assert response.model == "llama3.1"
        assert response.provider == "ollama"
        assert response.usage == {"input_tokens": 6, "output_tokens": 4}


async def test_complete_with_json_mode():
    with patch("qingqiu.llm.ollama_provider.httpx.AsyncClient") as MockClient:
        mock_client = MockClient.return_value
        mock_post = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": '{"x":1}'},
            "model": "llama3.1",
            "prompt_eval_count": 5,
            "eval_count": 3,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        mock_client.post = mock_post

        provider = OllamaProvider()
        await provider.complete([Message("user", "give json")], json_mode=True)

        payload = mock_post.call_args.kwargs["json"]
        assert payload["format"] == "json"


async def test_embed_returns_vector():
    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
    mock_response.raise_for_status = MagicMock()

    with patch("qingqiu.llm.ollama_provider.httpx.AsyncClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.post = AsyncMock(return_value=mock_response)

        provider = OllamaProvider()
        vec = await provider.embed("hello")

        assert vec == [0.1, 0.2, 0.3]
        # 验证用了 embed_model
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["model"] == "nomic-embed-text"
        assert payload["prompt"] == "hello"
"""Ollama provider · 本地 LLM + 嵌入"""

from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx

from qingqiu.llm.base import LLMProvider, LLMResponse, Message


class OllamaProvider(LLMProvider):
    """Ollama 本地 LLM · 完全离线推理

    默认模型 llama3.1 / qwen2.5 ；嵌入模型 nomic-embed-text
    详见 https://ollama.com/library
    """

    name = "ollama"

    def __init__(
        self,
        host: str | None = None,
        default_model: str = "llama3.1",
        embed_model: str = "nomic-embed-text",
    ) -> None:
        self.host = host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434"
        self.default_model = default_model
        self.embed_model = embed_model
        self.client = httpx.AsyncClient(base_url=self.host, timeout=60.0)

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        payload: dict = {
            "model": model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"

        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["message"]["content"],
            model=data.get("model", model or self.default_model),
            usage={
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
            },
            provider=self.name,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        payload: dict = {
            "model": model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with self.client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "message" in data and data["message"].get("content"):
                    yield data["message"]["content"]

    async def embed(self, text: str) -> list[float]:
        """Ollama 嵌入向量（v1.0 vault 检索用）"""
        response = await self.client.post(
            "/api/embeddings",
            json={"model": self.embed_model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]
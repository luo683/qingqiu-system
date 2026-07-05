"""自定义 OpenAI 兼容 API provider · 支持 GLM / DeepSeek / 自部署"""

from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx

from qingqiu.llm.base import LLMProvider, LLMResponse, Message


class CustomProvider(LLMProvider):
    """任何 OpenAI 兼容 API 都可以用

    配置：
        CUSTOM_LLM_URL=https://your-endpoint
        CUSTOM_LLM_API_KEY=your-key
        CUSTOM_LLM_MODEL=your-model
    """

    name = "custom"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        default_model: str | None = None,
    ) -> None:
        self.base_url = base_url or os.environ.get("CUSTOM_LLM_URL")
        self.api_key = api_key or os.environ.get("CUSTOM_LLM_API_KEY", "")
        self.default_model = default_model or os.environ.get("CUSTOM_LLM_MODEL", "custom-model")
        if not self.base_url:
            raise ValueError(
                "Custom LLM URL 未设置（设置 CUSTOM_LLM_URL 环境变量或传 base_url 参数）"
            )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            timeout=60.0,
        )

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
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", model or self.default_model),
            usage={
                "input_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": data.get("usage", {}).get("completion_tokens", 0),
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
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload_str = line[6:]
                if payload_str == "[DONE]":
                    break
                data = json.loads(payload_str)
                if data["choices"] and data["choices"][0]["delta"].get("content"):
                    yield data["choices"][0]["delta"]["content"]
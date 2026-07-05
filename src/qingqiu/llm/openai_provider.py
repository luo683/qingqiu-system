"""OpenAI provider"""

from __future__ import annotations

import os
from typing import AsyncIterator

from openai import AsyncOpenAI

from qingqiu.llm.base import LLMProvider, LLMResponse, Message


class OpenAIProvider(LLMProvider):
    """OpenAI 官方 SDK · 支持 gpt-4o / gpt-4o-mini / o1 / o3 等"""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key 未设置（设置 OPENAI_API_KEY 环境变量或传 api_key 参数）"
            )
        self.default_model = default_model
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=base_url)

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        kwargs = {
            "model": model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
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
        stream = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
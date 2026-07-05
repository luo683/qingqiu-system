"""Anthropic provider"""

from __future__ import annotations

import os
from typing import AsyncIterator

from anthropic import AsyncAnthropic

from qingqiu.llm.base import LLMProvider, LLMResponse, Message


class AnthropicProvider(LLMProvider):
    """Anthropic 官方 SDK · 支持 claude-sonnet / claude-opus / claude-haiku"""

    name = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "claude-sonnet-4-5",
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key 未设置（设置 ANTHROPIC_API_KEY 环境变量或传 api_key 参数）"
            )
        self.default_model = default_model
        self.client = AsyncAnthropic(api_key=self.api_key)

    @staticmethod
    def _split_system(messages: list[Message]) -> tuple[str | None, list[dict]]:
        """Anthropic 单独传 system message"""
        system = None
        rest = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                rest.append({"role": m.role, "content": m.content})
        return system, rest

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        json_mode: bool = False,  # Anthropic 通过 prompt 实现，不原生支持
    ) -> LLMResponse:
        system, rest = self._split_system(messages)
        kwargs: dict = {
            "model": model or self.default_model,
            "messages": rest,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        response = await self.client.messages.create(**kwargs)
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
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
        system, rest = self._split_system(messages)
        kwargs: dict = {
            "model": model or self.default_model,
            "messages": rest,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
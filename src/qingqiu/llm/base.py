"""LLM 抽象层基类 · 所有 provider 必须实现 LLMProvider Protocol"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class Message:
    """单条消息 · 简化版 OpenAI/Anthropic 通用格式"""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """LLM 统一响应格式"""

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)  # {input_tokens, output_tokens}
    provider: str = ""


class LLMProvider(ABC):
    """LLM Provider Protocol

    所有 provider 必须实现 complete() 和 stream()
    embed() 可选（v1.0 只有 Ollama 实现）
    """

    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        """非流式调用 · 返回完整响应"""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """流式调用 · 逐 chunk 返回文本"""
        ...
        yield ""  # 让 mypy 接受这是 AsyncIterator

    async def embed(self, text: str) -> list[float]:
        """嵌入向量 · v1.0 只 Ollama 实现，其他 provider 抛 NotImplementedError"""
        raise NotImplementedError(f"{self.name} provider 不支持 embedding")
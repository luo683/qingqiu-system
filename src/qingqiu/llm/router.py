"""LLM 智能路由 · 按角色分派到不同 provider"""

from __future__ import annotations

from qingqiu.llm.base import LLMProvider, LLMResponse, Message
from qingqiu.llm.exceptions import ProviderNotFoundError


class LLMRouter:
    """智能路由：不同任务角色用不同 provider

    用法（参见 TECH-STACK.md §8.4）：
        router = LLMRouter({
            "router":   OpenAIProvider(default_model="gpt-4o-mini"),     # 意图识别
            "planner":  AnthropicProvider(default_model="claude-sonnet-4-5"),  # 复杂推理
            "memory":   OllamaProvider(default_model="nomic-embed-text"), # 嵌入
        })
        response = await router.dispatch("router", [Message("user", "hi")])
    """

    def __init__(
        self,
        providers: dict[str, LLMProvider],
        default_role: str | None = None,
    ) -> None:
        if not providers:
            raise ValueError("LLMRouter 至少需要一个 provider")
        self.providers = providers
        self.default_role = default_role or next(iter(providers))

    def get(self, role: str) -> LLMProvider:
        """按角色拿 provider · 找不到回退到 default_role"""
        if role not in self.providers:
            return self.providers[self.default_role]
        return self.providers[role]

    def roles(self) -> list[str]:
        """所有可用角色"""
        return list(self.providers.keys())

    async def dispatch(
        self,
        role: str,
        messages: list[Message],
        **kwargs: object,
    ) -> LLMResponse:
        """按角色分派调用"""
        provider = self.get(role)
        if provider is None:
            raise ProviderNotFoundError(f"No provider for role '{role}' and no default")
        return await provider.complete(messages, **kwargs)
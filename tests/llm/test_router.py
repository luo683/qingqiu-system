"""Router 测试"""

from typing import AsyncIterator

import pytest

from qingqiu.llm.base import LLMProvider, LLMResponse, Message
from qingqiu.llm.router import LLMRouter
from qingqiu.llm.exceptions import ProviderNotFoundError


class MockProvider(LLMProvider):
    """测试用 mock provider · 记录被调用的角色"""

    name = "mock"

    def __init__(self, label: str = "mock") -> None:
        self.label = label
        self.call_count = 0

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(
            content=f"[{self.label}] {messages[-1].content}",
            model="mock",
            usage={"input_tokens": 0, "output_tokens": 0},
            provider=self.label,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        yield f"[{self.label}] stream"


def test_router_requires_at_least_one_provider():
    with pytest.raises(ValueError, match="至少需要一个"):
        LLMRouter({})


def test_router_default_role_is_first_key():
    p1 = MockProvider("a")
    p2 = MockProvider("b")
    router = LLMRouter({"a": p1, "b": p2})
    assert router.default_role == "a"


def test_router_default_role_can_be_set():
    p1 = MockProvider("a")
    p2 = MockProvider("b")
    router = LLMRouter({"a": p1, "b": p2}, default_role="b")
    assert router.default_role == "b"


def test_router_get_known_role():
    p1 = MockProvider("a")
    p2 = MockProvider("b")
    router = LLMRouter({"a": p1, "b": p2})
    assert router.get("a") is p1
    assert router.get("b") is p2


def test_router_get_unknown_falls_back_to_default():
    p1 = MockProvider("a")
    p2 = MockProvider("b")
    router = LLMRouter({"a": p1, "b": p2}, default_role="b")
    # 未知角色 → fallback 到 default
    assert router.get("unknown") is p2


def test_router_roles():
    p1 = MockProvider()
    p2 = MockProvider()
    router = LLMRouter({"a": p1, "b": p2})
    assert set(router.roles()) == {"a", "b"}


async def test_router_dispatch_calls_correct_provider():
    p_router = MockProvider("router")
    p_planner = MockProvider("planner")
    router = LLMRouter({"router": p_router, "planner": p_planner})

    response = await router.dispatch("router", [Message("user", "hi")])
    assert response.provider == "router"
    assert p_router.call_count == 1
    assert p_planner.call_count == 0

    response = await router.dispatch("planner", [Message("user", "think")])
    assert response.provider == "planner"
    assert p_router.call_count == 1
    assert p_planner.call_count == 1


async def test_router_dispatch_unknown_role_uses_default():
    p_router = MockProvider("router")
    router = LLMRouter({"router": p_router}, default_role="router")

    response = await router.dispatch("nonexistent_role", [Message("user", "hi")])
    assert response.provider == "router"
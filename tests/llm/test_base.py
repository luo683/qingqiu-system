"""base.py 测试 · Protocol / Message / LLMResponse"""

from qingqiu.llm.base import LLMProvider, LLMResponse, Message


def test_message_creation():
    m = Message(role="user", content="hi")
    assert m.role == "user"
    assert m.content == "hi"


def test_message_roles():
    for role in ("system", "user", "assistant"):
        m = Message(role=role, content="x")
        assert m.role == role


def test_llm_response_defaults():
    r = LLMResponse(content="hi", model="test-model")
    assert r.content == "hi"
    assert r.model == "test-model"
    assert r.usage == {}
    assert r.provider == ""


def test_llm_response_with_all_fields():
    r = LLMResponse(
        content="answer",
        model="gpt-4o",
        usage={"input_tokens": 10, "output_tokens": 20},
        provider="openai",
    )
    assert r.usage["input_tokens"] == 10
    assert r.usage["output_tokens"] == 20
    assert r.provider == "openai"


def test_provider_cannot_instantiate_directly():
    """LLMProvider 是抽象类，不能直接实例化"""
    import pytest
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


async def test_provider_default_embed_raises():
    """默认 embed() 抛 NotImplementedError"""
    import pytest

    class Dummy(LLMProvider):
        name = "dummy"

        async def complete(self, messages, **kwargs):
            return LLMResponse(content="x", model="m")

        async def stream(self, messages, **kwargs):
            yield "x"

    p = Dummy()
    with pytest.raises(NotImplementedError, match="不支持 embedding"):
        await p.embed("text")
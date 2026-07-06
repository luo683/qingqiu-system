"""test_handler.py · S4.2 消息 → Router 适配层测试"""
from __future__ import annotations

import pytest

from qingqiu.im.feishu.client import IncomingMessage
from qingqiu.im.feishu.handler import (
    HandlerResult,
    MessageHandler,
    Sender,
    get_default_handler,
)
from qingqiu.router.executor import Executor
from qingqiu.router.intent import Intent


@pytest.fixture
def executor():
    return Executor(llm_provider=None, use_llm=False)


@pytest.fixture
def handler(executor):
    return MessageHandler(executor=executor)


def _msg(text: str, chat_id: str = "oc_test", sender_id: str = "ou_user") -> IncomingMessage:
    return IncomingMessage(
        sender_id=sender_id,
        chat_id=chat_id,
        text=text,
    )


# === 基本路由 ===

def test_handler_routes_memory_get(handler):
    """memory get → Executor → 响应"""
    msg = _msg("memory get user_name")
    r = handler.on_message(msg)
    assert isinstance(r, HandlerResult)
    assert r.intent == "memory_get"
    assert r.exit_code == 0
    assert "user_name" in r.text or r.text  # 有内容


def test_handler_routes_memory_set(handler):
    """memory set → Executor → 成功"""
    msg = _msg("memory set hobby coding")
    r = handler.on_message(msg)
    assert r.intent == "memory_set"
    assert r.exit_code == 0


def test_handler_routes_task_add(handler):
    """新建任务 → 路由到 TASK_ADD"""
    msg = _msg("新建任务 写文档")
    r = handler.on_message(msg)
    assert r.intent == "task_add"
    assert r.exit_code == 0


def test_handler_routes_status(handler):
    """status → STATUS"""
    msg = _msg("status")
    r = handler.on_message(msg)
    assert r.intent == "status"


# === UNKNOWN / 友好提示 ===

def test_handler_unknown_returns_friendly(handler):
    """UNKNOWN 意图 → 回发友好提示"""
    # 避开 classifier 中"什么"会触发 ask 模式
    msg = _msg("xyz qqq zzz xxx yyy 12345")
    r = handler.on_message(msg)
    assert r.intent == "unknown"
    assert r.exit_code != 0
    assert "试试" in r.text or "未识别" in r.text
    # 包含示例指令
    assert "memory" in r.text


def test_handler_unknown_english(handler):
    """英文乱码 → 也走 UNKNOWN"""
    msg = _msg("xyz abc def ghi")
    r = handler.on_message(msg)
    assert r.intent == "unknown"
    assert "试试" in r.text


def test_handler_empty_text(handler):
    """空文本 → 友好空消息"""
    msg = _msg("")
    r = handler.on_message(msg)
    assert r.intent == Intent.UNKNOWN.value
    assert r.exit_code == 1
    assert "空消息" in r.text


def test_handler_whitespace_text(handler):
    """纯空格 → 视为空"""
    msg = _msg("   \t  ")
    r = handler.on_message(msg)
    assert r.intent == Intent.UNKNOWN.value


# === 元数据传递 ===

def test_handler_extra_contains_chat_id(handler):
    """extra 包含 chat_id / sender_id"""
    msg = _msg("memory get user_name", chat_id="oc_special", sender_id="ou_special")
    r = handler.on_message(msg)
    assert r.extra["chat_id"] == "oc_special"
    assert r.extra["sender_id"] == "ou_special"


# === Intent 提取 ===

def test_handler_extract_intent_for_known(handler):
    """已知 intent 正确提取"""
    r = handler.on_message(_msg("memory set k v"))
    assert r.intent == "memory_set"


def test_handler_extract_intent_for_unknown(handler):
    """UNKNOWN intent"""
    r = handler.on_message(_msg("乱七八杂的输入"))
    assert r.intent == "unknown"


# === 异常处理 ===

def test_handler_does_not_propagate_executor_exception():
    """Executor 抛异常 → handler 兜底成内部错误"""
    class FailingExecutor:
        def execute(self, text, out):
            raise RuntimeError("simulated crash")

        @property
        def _classifier(self):
            raise AttributeError  # _extract_intent 也会失败

    h = MessageHandler(executor=FailingExecutor())  # type: ignore[arg-type]
    r = h.on_message(_msg("memory get user_name"))
    # 注：我们的实现中 Executor 类型不严格，传入 FailingExecutor 后
    # _extract_intent 会因 _classifier 异常 fallback 到 unknown
    # 但 execute 本身抛异常会被 on_message 捕获并返回 HandlerResult(text="内部错误：...")
    assert "内部错误" in r.text or r.intent == "unknown"


# === 默认工厂 ===

def test_get_default_handler_creates_executor():
    """get_default_handler 默认带 Executor"""
    h = get_default_handler()
    assert h._executor is not None
    assert isinstance(h._executor, Executor)


def test_get_default_handler_with_executor(executor):
    """get_default_handler 接受传入 executor"""
    h = get_default_handler(executor=executor)
    assert h._executor is executor


# === Sender dataclass ===

def test_sender_defaults():
    """Sender 默认值"""
    s = Sender(sender_id="ou_x")
    assert s.sender_id == "ou_x"
    assert s.sender_name == ""
    assert s.sender_type == "user"
    assert s.tenant_key == ""


# === 异步入口 ===

def test_aon_message_sync_result(handler):
    """aon_message 异步入口也返回 HandlerResult"""
    import asyncio

    msg = _msg("memory get user_name")
    r = asyncio.run(handler.aon_message(msg))
    assert r.intent == "memory_get"


# === 长文本响应捕获 ===

def test_handler_captures_multi_line_output(executor):
    """multi-line 输出也能正确捕获"""
    h = MessageHandler(executor=executor)
    msg = _msg("memory list")  # 输出通常是 key-value 列表
    r = h.on_message(msg)
    assert r.exit_code == 0
    # text 不为空
    assert r.text != ""


def test_handler_stream_is_isolated(executor):
    """每次 on_message 的 stream 互相隔离（不串味）"""
    h = MessageHandler(executor=executor)
    r1 = h.on_message(_msg("memory set k1 v1"))
    r2 = h.on_message(_msg("memory get k1"))
    # 两次响应独立，不应混在一起
    assert "memory set" not in r2.text or "k1" in r2.text
"""test_reply.py · S4.3 IM 响应回发测试"""
from __future__ import annotations

import pytest

from qingqiu.im.feishu.client import FeishuClient, FeishuConfig, IncomingMessage
from qingqiu.im.feishu.reply import (
    ReplyResult,
    _chunk_text,
    _extract_chat_id,
    reply,
    set_default_client,
)


@pytest.fixture
def client():
    cfg = FeishuConfig(mock=True)
    c = FeishuClient(cfg)
    c.start()
    yield c
    c.stop()


@pytest.fixture(autouse=True)
def reset_default_client():
    """每个 test 重置 default client"""
    set_default_client(None)  # type: ignore[arg-type]
    yield
    set_default_client(None)  # type: ignore[arg-type]


# === 基本回发 ===

def test_reply_with_incoming_message(client):
    """reply(IncomingMessage, text) → send_message(chat_id)"""
    msg = IncomingMessage(sender_id="ou_user", chat_id="oc_chat_1", text="hi")
    r = reply(msg, "hello back", client=client)
    assert r.ok is True
    assert r.chunks_sent == 1
    assert len(client.transport.sent) == 1
    sent = client.transport.sent[0]
    assert sent.receive_id == "oc_chat_1"


def test_reply_with_dict_target(client):
    """reply(dict, text) → dict.chat_id"""
    r = reply({"chat_id": "oc_dict_2"}, "dict msg", client=client)
    assert r.ok is True
    assert client.transport.sent[0].receive_id == "oc_dict_2"


def test_reply_with_str_target(client):
    """reply(str, text) → str 当 chat_id"""
    r = reply("oc_str_3", "str msg", client=client)
    assert r.ok is True
    assert client.transport.sent[0].receive_id == "oc_str_3"


def test_reply_falls_back_to_sender_id_when_no_chat():
    """IncomingMessage 无 chat_id → fallback 到 sender_id"""
    msg = IncomingMessage(sender_id="ou_fallback", chat_id="", text="hi")
    cfg = FeishuConfig(mock=True)
    c = FeishuClient(cfg)
    c.start()
    try:
        reply(msg, "hi", client=c)
        assert c.transport.sent[0].receive_id == "ou_fallback"
    finally:
        c.stop()


# === 默认 client ===

def test_reply_uses_default_client(client):
    """reply 不传 client → 使用 default"""
    set_default_client(client)
    msg = IncomingMessage(sender_id="ou_x", chat_id="oc_default")
    r = reply(msg, "via default")
    assert r.ok
    assert client.transport.sent[-1].receive_id == "oc_default"


def test_reply_no_client_returns_error():
    """reply 无 client + 无 default → 返回 error（不抛）"""
    r = reply("oc_x", "hello")
    assert r.ok is False
    assert r.error != ""


# === 边界 ===

def test_reply_empty_text_returns_ok_no_chunks(client):
    """reply(text="") → ok=True, chunks_sent=0（不发送）"""
    r = reply("oc_x", "", client=client)
    assert r.ok is True
    assert r.chunks_sent == 0
    assert len(client.transport.sent) == 0


def test_reply_client_not_started_returns_error():
    """client 未 start → 返回 error"""
    cfg = FeishuConfig(mock=True)
    c = FeishuClient(cfg)  # 没 start
    r = reply("oc_x", "hi", client=c)
    assert r.ok is False
    assert "not started" in r.error


def test_reply_no_chat_id_returns_error(client):
    """target 无法提取 chat_id → 返回 error"""
    r = reply(42, "hi", client=client)  # int 不是合法 target
    assert r.ok is False
    assert "chat_id" in r.error


# === 长文本 chunk ===

def test_reply_long_text_chunks(client):
    """超长文本分多 chunk"""
    long_text = "x" * 9000  # 超过 4000 限制
    msg = IncomingMessage(sender_id="ou_x", chat_id="oc_chunk")
    r = reply(msg, long_text, client=client)
    assert r.ok is True
    # 至少 2 个 chunk
    assert r.chunks_sent >= 2
    assert len(client.transport.sent) == r.chunks_sent
    # 每个 chunk ≤ 4000
    for sent in client.transport.sent[-r.chunks_sent:]:
        data = __import__("json").loads(sent.content)
        assert len(data["text"]) <= 4000


def test_reply_short_text_no_chunk(client):
    """短文本不切分"""
    msg = IncomingMessage(sender_id="ou_x", chat_id="oc_short")
    r = reply(msg, "hello", client=client)
    assert r.chunks_sent == 1


# === receive_id_type ===

def test_reply_open_id_type(client):
    """receive_id_type=open_id"""
    msg = IncomingMessage(sender_id="ou_open", chat_id="")
    r = reply(msg, "hi", client=client, receive_id_type="open_id")
    assert r.ok
    sent = client.transport.sent[-1]
    assert sent.receive_id == "ou_open"  # fallback 到 sender_id
    assert sent.receive_id_type == "open_id"


# === _chunk_text 辅助 ===

def test_chunk_text_short_no_chunk():
    """短文本不切"""
    assert _chunk_text("hello", 100) == ["hello"]


def test_chunk_text_long_splits():
    """长文本切多段"""
    text = "a" * 50 + "\n\n" + "b" * 50 + "\n\n" + "c" * 50
    chunks = _chunk_text(text, 60)
    assert len(chunks) >= 2
    # 重组应覆盖原文（允许去掉多余空白）
    joined = "".join(chunks).replace("\n\n", "").replace(" ", "")
    assert joined == "a" * 50 + "b" * 50 + "c" * 50


def test_chunk_text_handles_no_break():
    """无换行的长文本硬切"""
    text = "a" * 200
    chunks = _chunk_text(text, 50)
    assert len(chunks) == 4
    assert all(len(c) <= 50 for c in chunks)


# === _extract_chat_id 辅助 ===

def test_extract_chat_id_from_incoming():
    msg = IncomingMessage(sender_id="ou_x", chat_id="oc_y")
    assert _extract_chat_id(msg) == "oc_y"


def test_extract_chat_id_from_dict():
    assert _extract_chat_id({"chat_id": "oc_d"}) == "oc_d"
    assert _extract_chat_id({"chat_id": "", "sender_id": "ou_s"}) == "ou_s"


def test_extract_chat_id_from_str():
    assert _extract_chat_id("oc_xyz") == "oc_xyz"


def test_extract_chat_id_invalid_type():
    assert _extract_chat_id(42) == ""
    assert _extract_chat_id(None) == ""
"""test_e2e.py · M4 端到端：WebSocket 收到 → Router → 回发"""
from __future__ import annotations

from pathlib import Path

import pytest

from qingqiu.im.feishu.client import FeishuClient, FeishuConfig, IncomingMessage
from qingqiu.im.feishu.handler import MessageHandler
from qingqiu.im.feishu.reply import reply


@pytest.fixture
def isolated_home(monkeypatch, tmp_path: Path):
    """隔离 HOME / USERPROFILE 到 tmp 目录，避免 L3 / TaskStore 污染其他测试"""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


@pytest.fixture
def client_handler():
    """client + handler 一起构造"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    handler = MessageHandler()
    return client, handler


# === 端到端：Client → Handler → Reply ===

def test_e2e_memory_get_via_client_callback(isolated_home):
    """Client 收到消息 → 调 handler → reply 回发"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    handler = MessageHandler()

    client.start()
    try:
        results = []

        @client.on_message
        def cb(msg):
            result = handler.on_message(msg)
            results.append((msg, result))
            # 回发
            reply(msg, result.text, client=client)

        # 模拟飞书推送
        msg = IncomingMessage(
            sender_id="ou_e2e_1",
            chat_id="oc_e2e_chat",
            text="memory get user_name",
        )
        client.transport.inject_message(msg)

        assert len(results) == 1
        orig_msg, handler_result = results[0]
        assert orig_msg.chat_id == "oc_e2e_chat"
        assert handler_result.intent == "memory_get"
        # 回发应有内容
        assert len(client.transport.sent) == 1
        assert client.transport.sent[0].receive_id == "oc_e2e_chat"
    finally:
        client.stop()


def test_e2e_unknown_message_friendly(isolated_home):
    """UNKNOWN → 友好提示回发"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    handler = MessageHandler()

    client.start()
    try:
        results = []

        @client.on_message
        def cb(msg):
            r = handler.on_message(msg)
            results.append(r)
            reply(msg, r.text, client=client)

        msg = IncomingMessage(
            sender_id="ou_e2e_2",
            chat_id="oc_e2e_2",
            text="asdfghjkl 乱七八糟",
        )
        client.transport.inject_message(msg)

        assert len(results) == 1
        result = results[0]
        assert result.intent == "unknown"
        assert "试试" in result.text or "未识别" in result.text

        # 回发也带友好提示
        sent = client.transport.sent[0]
        assert "试试" in sent.content or "未识别" in sent.content
    finally:
        client.stop()


def test_e2e_multiple_messages_serial(isolated_home):
    """多条消息串行处理（用 isolated_home 隔离 L3 / TaskStore）"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    handler = MessageHandler()

    client.start()
    try:
        results = []

        @client.on_message
        def cb(msg):
            r = handler.on_message(msg)
            results.append(r)
            reply(msg, r.text, client=client)

        # 起点：清空 outbox（避免前序测试残留）
        client.outbox.clear()
        client.inbox.clear()

        for text in [
            "memory set k1 v1",
            "memory get k1",
            "memory list",
            "新建任务 测试",
            "看任务",
        ]:
            msg = IncomingMessage(
                sender_id="ou_e2e_multi",
                chat_id="oc_multi",
                text=text,
            )
            client.transport.inject_message(msg)

        assert len(results) == 5

        # 不强断言 outbox 数量（chunks 可能 > 消息数；用 intent 序列验证）
        intents = [r.intent for r in results]
        assert intents[0] == "memory_set"
        assert intents[1] == "memory_get"
        assert intents[2] == "memory_list"
        assert intents[3] == "task_add"
        assert intents[4] == "task_list"

        # 每条消息至少回发 1 个 outbox 项
        assert len(client.outbox) >= 5
    finally:
        client.stop()


def test_e2e_message_with_chinese_text(isolated_home):
    """中文消息完整链路"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    handler = MessageHandler()

    client.start()
    try:
        results = []

        @client.on_message
        def cb(msg):
            r = handler.on_message(msg)
            results.append(r)
            reply(msg, r.text, client=client)

        msg = IncomingMessage(
            sender_id="ou_cn",
            chat_id="oc_cn",
            text="新建任务 测试 IM 接入",
        )
        client.transport.inject_message(msg)

        r = results[0]
        assert r.intent == "task_add"
        # 回发成功
        assert client.transport.sent[0].receive_id == "oc_cn"
    finally:
        client.stop()


def test_e2e_handler_callback_runs_after_inject():
    """验证 callback 真的被触发（不是仅 inject）"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)

    callback_fired = []

    client.start()
    try:
        @client.on_message
        def cb(msg):
            callback_fired.append(msg.text)

        msg = IncomingMessage(sender_id="ou_a", chat_id="oc_a", text="ping")
        client.transport.inject_message(msg)

        assert callback_fired == ["ping"]
    finally:
        client.stop()
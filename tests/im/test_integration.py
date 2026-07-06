"""tests/im/test_integration.py · M4 IM 端到端 mock 验证

模拟真实飞书 IM 推送：
- "memory set user_name ROG" → set 成功
- "memory get user_name" → 返 "user_name=ROG, layer=L3"
- "memory list" → 看 keys
- "ask unknown" → UNKNOWN → 友好提示
- 收到后立即回发（automation）
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qingqiu.im.feishu.client import FeishuClient
from qingqiu.im.feishu.handler import MessageHandler
from qingqiu.im.feishu.reply import run_reply_loop


@pytest.fixture
def tmp_mem(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


@pytest.fixture
def client_with_handler(tmp_mem):
    client = FeishuClient()
    handler = MessageHandler()
    run_reply_loop(client, handler, in_thread=False)
    yield client
    client.stop()


def _find_outbox_text(client, chat_id="oc_test"):
    """找出最近一条发给 chat_id 的 reply"""
    for m in reversed(client.outbox):
        if m.chat_id == chat_id:
            return m.text
    return ""


def test_e2e_memory_set_then_get(client_with_handler):
    cli = client_with_handler
    # 用户发消息：设置
    cli.inject_mock_event("memory set user_name ROG", sender_id="user_a", chat_id="oc_chat_1")
    set_reply = _find_outbox_text(cli, "oc_chat_1")
    assert set_reply
    assert "user_name" in set_reply

    # 用户发消息：查
    cli.inject_mock_event("memory get user_name", sender_id="user_a", chat_id="oc_chat_1")
    get_reply = _find_outbox_text(cli, "oc_chat_1")
    assert "ROG" in get_reply
    assert "L3" in get_reply, f"reply should mention layer L3, got {get_reply!r}"


def test_e2e_memory_list(client_with_handler):
    cli = client_with_handler
    cli.inject_mock_event("memory set k1 v1", sender_id="u", chat_id="oc_x")
    cli.inject_mock_event("memory set k2 v2", sender_id="u", chat_id="oc_x")
    cli.inject_mock_event("memory list", sender_id="u", chat_id="oc_x")
    last = _find_outbox_text(cli, "oc_x")
    assert "k1" in last or "k2" in last


def test_e2e_unknown_returns_friendly(client_with_handler):
    cli = client_with_handler
    cli.inject_mock_event("随便说点乱码 123", sender_id="u", chat_id="oc_y")
    last = _find_outbox_text(cli, "oc_y")
    assert last
    assert "未识别" in last or "试试" in last or "memory" in last


def test_e2e_multi_user_separate_chats(client_with_handler):
    """两个 chat → 各自回发，互不串扰"""
    cli = client_with_handler
    cli.inject_mock_event("memory set alpha alice", sender_id="u1", chat_id="oc_alpha")
    cli.inject_mock_event("memory get alpha", sender_id="u2", chat_id="oc_beta")
    alpha_reply = _find_outbox_text(cli, "oc_alpha")
    beta_reply = _find_outbox_text(cli, "oc_beta")
    assert "alpha" in alpha_reply or "alice" in alpha_reply
    # beta get alpha → 应该从同一 memory 拿到（共享 L3）
    assert "alice" in beta_reply


def test_e2e_inbox_outbox_grows_symmetrically(client_with_handler):
    cli = client_with_handler
    for i in range(3):
        cli.inject_mock_event(f"ping {i}", sender_id="u", chat_id="oc_t")
    assert len(cli.inbox) >= 3
    assert len(cli.outbox) >= 3

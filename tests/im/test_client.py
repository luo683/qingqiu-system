"""test_client.py · S4.1 飞书 WebSocket 客户端测试"""
from __future__ import annotations

import asyncio
import json
import os

import pytest

from qingqiu.im.feishu.client import (
    FeishuClient,
    FeishuConfig,
    IncomingMessage,
)
from qingqiu.im.feishu.mock import MockTransport


# === Config ===

def test_config_from_env_no_creds_is_mock(monkeypatch):
    """无 creds → 自动 mock"""
    monkeypatch.delenv("FEISHU_APP_ID", raising=False)
    monkeypatch.delenv("FEISHU_APP_SECRET", raising=False)
    monkeypatch.delenv("FEISHU_USE_MOCK", raising=False)
    cfg = FeishuConfig.from_env()
    assert cfg.mock is True
    assert cfg.is_real is False
    assert cfg.app_id == ""
    assert cfg.app_secret == ""


def test_config_from_env_with_creds_is_real(monkeypatch):
    """有 creds + 无强制 mock → 真实模式"""
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test123")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret_abc")
    monkeypatch.delenv("FEISHU_USE_MOCK", raising=False)
    cfg = FeishuConfig.from_env()
    assert cfg.mock is False
    assert cfg.is_real is True


def test_config_force_mock_overrides_creds(monkeypatch):
    """FEISHU_USE_MOCK=1 强制覆盖"""
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test123")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret_abc")
    monkeypatch.setenv("FEISHU_USE_MOCK", "1")
    cfg = FeishuConfig.from_env()
    assert cfg.mock is True
    assert cfg.is_real is False


def test_config_explicit_construction():
    """显式构造"""
    cfg = FeishuConfig(app_id="x", app_secret="y", mock=True)
    assert cfg.is_real is False
    cfg2 = FeishuConfig(app_id="x", app_secret="y", mock=False)
    assert cfg2.is_real is True


# === Client 启动 / 停止 ===

def test_client_mock_start_stop():
    """mock 模式 start/stop"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    assert client.is_started is False
    client.start()
    assert client.is_started is True
    assert client.is_mock is True
    client.stop()
    assert client.is_started is False


def test_client_double_start_raises():
    """重复 start 抛 RuntimeError"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    client.start()
    try:
        with pytest.raises(RuntimeError, match="already started"):
            client.start()
    finally:
        client.stop()


def test_client_double_stop_is_idempotent():
    """重复 stop 不抛"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    client.start()
    client.stop()
    client.stop()  # no error
    assert client.is_started is False


def test_client_send_without_start_raises():
    """未启动就 send 抛错"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    with pytest.raises(RuntimeError, match="not started"):
        client.send_message("oc_chat", "hello")


# === Callback 注册 ===

def test_client_on_message_decorator():
    """on_message 装饰器"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)

    received = []

    @client.on_message
    def cb(msg):
        received.append(msg)

    assert cb in client._callbacks
    assert len(client._callbacks) == 1


def test_client_register_message_callback():
    """非装饰器注册"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)

    def cb(msg):
        pass

    client.register_message_callback(cb)
    assert cb in client._callbacks


def test_client_inject_message_dispatches():
    """inject → callback 触发"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    client.start()
    try:
        received = []
        client.register_message_callback(lambda m: received.append(m))
        # 重新注册到 transport（start 后）
        client.transport.register_callback(client._dispatch)

        msg = IncomingMessage(sender_id="ou_x", chat_id="oc_y", text="hi")
        client.transport.inject_message(msg)

        assert len(received) == 1
        assert received[0].sender_id == "ou_x"
        assert received[0].text == "hi"
    finally:
        client.stop()


def test_client_send_message_text():
    """send_message 把文本打包成飞书 content JSON"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    client.start()
    try:
        client.send_message("oc_chat", "hello world")
        assert len(client.transport.sent) == 1
        sent = client.transport.sent[0]
        assert sent.receive_id == "oc_chat"
        assert sent.msg_type == "text"
        # content 是 JSON 字符串
        data = json.loads(sent.content)
        assert data["text"] == "hello world"
    finally:
        client.stop()


def test_client_send_message_with_open_id_type():
    """send_message 支持 receive_id_type=open_id"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    client.start()
    try:
        client.send_message("ou_open_xxx", "hi", receive_id_type="open_id")
        sent = client.transport.sent[0]
        assert sent.receive_id == "ou_open_xxx"
        assert sent.receive_id_type == "open_id"
    finally:
        client.stop()


# === IncomingMessage ===

def test_incoming_message_defaults():
    """IncomingMessage 默认值"""
    msg = IncomingMessage(sender_id="ou_x", text="hi")
    assert msg.sender_id == "ou_x"
    assert msg.chat_id == ""
    assert msg.chat_type == "p2p"
    assert msg.msg_type == "text"
    assert msg.text == "hi"
    assert msg.raw is None


def test_incoming_message_all_fields():
    """IncomingMessage 全字段"""
    msg = IncomingMessage(
        sender_id="ou_x",
        sender_name="ROG",
        chat_id="oc_chat",
        chat_type="group",
        message_id="om_msg",
        text="hello",
        msg_type="text",
    )
    assert msg.sender_name == "ROG"
    assert msg.chat_type == "group"
    assert msg.message_id == "om_msg"


# === MockTransport ===

def test_mock_transport_basic():
    """MockTransport 基本行为"""
    t = MockTransport()
    t.mark_started()
    t.sent.append("dummy")  # 直接操作
    assert t.is_started is True
    assert len(t.sent) == 1


def test_mock_transport_reset():
    """MockTransport.reset"""
    t = MockTransport()
    t.sent.append("dummy")
    t._received.append("dummy2")
    t.reset()
    assert len(t.sent) == 0
    assert len(t._received) == 0
    assert t.is_started is False


def test_extract_text_from_message():
    """_extract_text 处理 text 类型"""
    content = json.dumps({"text": "hello"})
    assert FeishuClient._extract_text(content, "text") == "hello"


def test_extract_text_post_type():
    """_extract_text 处理 post 类型"""
    content = json.dumps({
        "zh_cn": {
            "content": [[{"tag": "text", "text": "标题"}], [{"tag": "text", "text": "正文"}]]
        }
    })
    result = FeishuClient._extract_text(content, "post")
    assert "标题" in result
    assert "正文" in result


def test_extract_text_invalid_json():
    """_extract_text 处理非法 JSON"""
    assert FeishuClient._extract_text("not json", "text") == "not json"
    assert FeishuClient._extract_text("", "text") == ""
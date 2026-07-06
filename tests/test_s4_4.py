"""test_s4_4.py · S4.4 飞书按钮 + 卡片消息"""

from __future__ import annotations

import json
import asyncio
import pytest

from qingqiu.im.feishu import (
    FeishuClient,
    FeishuConfig,
    InteractiveMessage,
    ButtonAction,
    ButtonClickDispatcher,
    ACTION_CONFIRM,
    ACTION_CANCEL,
    new_dispatcher,
)


# === InteractiveMessage.to_dict / to_json ===

def test_text_card_to_dict():
    """纯文本卡片结构"""
    msg = InteractiveMessage.from_text("你好", tip="tip123")
    d = msg.to_dict()
    assert d["msg_type"] == "interactive"
    assert "card" in d
    assert d["card"]["header"]["template"] == "blue"
    print(f"  [PASS] from_text card: {len(d['card']['elements'])} elements")


def test_confirm_card_has_buttons():
    """confirm_card 必须含 2 个按钮"""
    msg = InteractiveMessage.confirm_card("确认？", "待执行 X", confirm_value="x1")
    d = msg.to_dict()
    # 找 action 元素
    action_elements = [e for e in d["card"]["elements"] if e["tag"] == "action"]
    assert len(action_elements) >= 1, "missing action row"
    actions = action_elements[0]["actions"]
    assert len(actions) == 2
    assert actions[0]["name"] == ACTION_CONFIRM
    assert actions[1]["name"] == ACTION_CANCEL
    assert actions[0]["value"] == "x1"
    print(f"  [PASS] confirm_card 2 buttons: {actions[0]['text']['content']} / {actions[1]['text']['content']}")


def test_info_card_no_buttons():
    """info_card 无按钮"""
    msg = InteractiveMessage.info_card("通知", "系统已启动")
    d = msg.to_dict()
    actions = [e for e in d["card"]["elements"] if e["tag"] == "action"]
    assert len(actions) == 0
    print(f"  [PASS] info_card no buttons")


def test_card_to_json_round_trip():
    """卡片 dict → JSON → dict 往返"""
    msg = InteractiveMessage.confirm_card("t", "b")
    s = msg.to_json()
    d = json.loads(s)
    assert d["card"]["header"]["title"]["content"] == "t"
    print(f"  [PASS] to_json round trip")


# === Dispatcher 按钮点击 ===

def test_dispatcher_simple_action():
    """简单 action 派发"""
    d = ButtonClickDispatcher()
    received = []
    @d.on(ACTION_CONFIRM)
    def handle(action):
        received.append(action.value)
    a = ButtonAction(action=ACTION_CONFIRM, value="task_42")
    count = d.dispatch(a)
    assert count == 1
    assert received == ["task_42"]
    print(f"  [PASS] confirm action handled: {received}")


def test_dispatcher_multiple_handlers():
    """同一 action 多 handler 都触发"""
    d = ButtonClickDispatcher()
    a_count = [0]
    b_count = [0]
    @d.on(ACTION_CONFIRM)
    def a(action):
        a_count[0] += 1
    @d.on(ACTION_CONFIRM)
    def b(action):
        b_count[0] += 1
    a = ButtonAction(action=ACTION_CONFIRM)
    d.dispatch(a)
    assert a_count[0] == 1
    assert b_count[0] == 1
    print(f"  [PASS] dual handlers triggered")


def test_dispatcher_wildcard_handler():
    """通配 handler 触发"""
    d = ButtonClickDispatcher()
    received = []
    @d.on_any
    def any_handler(action):
        received.append(action.action)
    d.dispatch(ButtonAction(action=ACTION_CONFIRM))
    d.dispatch(ButtonAction(action=ACTION_CANCEL))
    assert received == [ACTION_CONFIRM, ACTION_CANCEL]
    print(f"  [PASS] wildcard: {received}")


def test_dispatcher_unknown_action_no_handler():
    """未注册 action → 0 个 handler 触发"""
    d = ButtonClickDispatcher()
    a = ButtonAction(action="unknown_action")
    count = d.dispatch(a)
    assert count == 0
    print(f"  [PASS] unknown action → count=0")


def test_dispatcher_handler_exception_doesnt_stop():
    """handler 抛异常不影响其他 handler"""
    d = ButtonClickDispatcher()
    received = []
    @d.on(ACTION_CONFIRM)
    def boom(action):
        raise RuntimeError("boom")
    @d.on(ACTION_CONFIRM)
    def good(action):
        received.append("ok")
    count = d.dispatch(ButtonAction(action=ACTION_CONFIRM))
    assert count == 2  # 2 handler 都被 call（尽管一个炸了）
    assert received == ["ok"]
    print(f"  [PASS] exception isolated")


# === FeishuClient.send_interactive mock 模式 ===

def test_client_send_interactive_mock():
    """client.send_interactive → mock 模式记录到 transport.sent"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    client.start()
    msg = InteractiveMessage.confirm_card("Hi", "b", confirm_value="42")
    client.send_interactive("oc_test", msg)
    # mock 模式记录
    assert hasattr(client, "_transport") and client._transport is not None
    sent = client._transport.sent
    assert len(sent) == 1
    assert sent[0].msg_type == "interactive"
    assert sent[0].receive_id == "oc_test"
    card = json.loads(sent[0].content)
    assert "elements" in card
    print(f"  [PASS] client.send_interactive → mock recorded")


def test_client_send_interactive_not_started_raises():
    """client 未 start 时 send_interactive 报错"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    # 不 start
    msg = InteractiveMessage.info_card("x", "y")
    with pytest.raises(RuntimeError, match="not started"):
        client.send_interactive("oc_x", msg)
    print(f"  [PASS] not-started raises RuntimeError")


def test_client_send_interactive_no_chat_id_raises():
    """不传 receive_id 报错"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    client.start()
    msg = InteractiveMessage.info_card("x", "y")
    with pytest.raises(ValueError, match="receive_id required"):
        client.send_interactive("", msg)
    print(f"  [PASS] empty receive_id raises")


# === 端到端：confirm 流程 ===

def test_end_to_end_confirm_flow():
    """端到端：发送确认卡 → 用户点 confirm → handler 触发 → 收到 task_id"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    client.start()

    dispatcher = new_dispatcher()
    confirmed_tasks = []
    cancelled_tasks = []

    @dispatcher.on(ACTION_CONFIRM)
    def on_confirm(action):
        confirmed_tasks.append(action.value)

    @dispatcher.on(ACTION_CANCEL)
    def on_cancel(action):
        cancelled_tasks.append(action.value)

    # 1) 发送 confirm card
    msg = InteractiveMessage.confirm_card(
        "执行任务？", "即将执行 task_001", confirm_value="task_001"
    )
    client.send_interactive("oc_user", msg)
    assert len(client._transport.sent) == 1

    # 2) 用户点击 confirm（mock 注入 click 事件）
    click = ButtonAction(
        action=ACTION_CONFIRM,
        value="task_001",
        sender_id="ou_user",
        chat_id="oc_user",
    )
    count = dispatcher.dispatch(click)
    assert count == 1
    assert confirmed_tasks == ["task_001"]
    assert cancelled_tasks == []
    print(f"  [PASS] E2E confirm flow: task={confirmed_tasks}")


def test_end_to_end_cancel_flow():
    """端到端 cancel 流程"""
    cfg = FeishuConfig(mock=True)
    client = FeishuClient(cfg)
    client.start()

    dispatcher = new_dispatcher()
    cancels = []
    @dispatcher.on(ACTION_CANCEL)
    def on_cancel(action):
        cancels.append(action.value)

    msg = InteractiveMessage.confirm_card("执行？", "body", confirm_value="t1")
    client.send_interactive("oc_user", msg)

    # 注入 cancel click
    click = ButtonAction(
        action=ACTION_CANCEL, value="t1", sender_id="ou_x", chat_id="oc_y"
    )
    dispatcher.dispatch(click)
    assert cancels == ["t1"]
    print(f"  [PASS] E2E cancel flow")
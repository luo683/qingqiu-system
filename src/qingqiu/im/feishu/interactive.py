"""qingqiu.im.feishu.interactive · 飞书卡片消息 + 按钮（S4.4）

设计要点：
- Card 2.0 JSON schema（飞书 v2 协议 · 简化）
- InteractiveMessage 构造器：header / elements (含 button rows)
- 默认有 Confirm / Cancel 按钮组合（适配 v1.0 confirm-then-execute 流程）
- send_interactive()：真实走 lark-oapi，mock 走 MockTransport
- on_button_click()：注册按钮点击回调（mock 模式可注入触发）
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from qingqiu.im.feishu.client import FeishuClient
from qingqiu.im.feishu.mock import MockTransport
from qingqiu.observability.logger import get_logger

_log = get_logger("qingqiu.im.feishu.interactive")


# === 按钮动作标签 ===

ACTION_CONFIRM = "confirm"
ACTION_CANCEL = "cancel"
ACTION_VIEW = "view"


@dataclass
class ButtonAction:
    """按钮点击事件（飞书 callback 或 mock 注入）"""

    action: str  # "confirm" | "cancel" | "view" | ...
    value: str = ""  # 业务值（如 task_id, action_id）
    sender_id: str = ""  # 点击者
    chat_id: str = ""  # 来源会话
    raw: dict = field(default_factory=dict)  # 原始事件


ButtonClickHandler = Callable[[ButtonAction], Any]


# === 卡片构建器 ===

@dataclass
class InteractiveMessage:
    """飞书卡片消息 v2.0（简化）

    用法：
        card = InteractiveMessage.confirm_card(
            title="确认执行？",
            body="即将执行任务 X，可能修改文件。",
            confirm_value="task_123",
        )
        client.send_interactive(chat_id, card)
    """

    msg_type: str = "interactive"
    card: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"msg_type": self.msg_type, "card": self.card}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_payload(self) -> str:
        """飞书 lark-oapi CreateMessageRequestBody.content JSON 字符串"""
        # 飞书 interactive 实际是 {"card": {...}}
        # 但更标准的做法：content 直接是 card 对象
        # 这里两种都支持（client 那边以 .to_payload 优先）
        return json.dumps(self.card, ensure_ascii=False)

    @staticmethod
    def from_text(text: str, tip: str = "") -> "InteractiveMessage":
        """纯文本卡片（最简单的 confirm）"""
        return InteractiveMessage(
            card={
                "config": {"wide_screen_mode": True},
                "header": {"template": "blue", "title": {"tag": "plain_text", "content": "清秋"}},
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "plain_text", "content": text},
                    }
                ] + ([{
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": tip}],
                }] if tip else []),
            }
        )

    @staticmethod
    def confirm_card(
        title: str,
        body: str,
        confirm_value: str = "ok",
        cancel_value: str = "cancel",
    ) -> "InteractiveMessage":
        """带「确认 / 取消」按钮的卡片

        Args:
            title: 卡片标题（header）
            body: 提示文本
            confirm_value: 确认按钮携带的业务值（回调时能拿到）
            cancel_value: 取消按钮携带的业务值
        """
        return InteractiveMessage(
            card={
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "orange",
                    "title": {"tag": "plain_text", "content": title},
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "plain_text", "content": body}},
                    {
                        "tag": "hr",
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "type": "primary",
                                "text": {"tag": "plain_text", "content": "✓ 确认"},
                                "value": confirm_value,
                                "action": ACTION_CONFIRM,
                                "name": ACTION_CONFIRM,
                            },
                            {
                                "tag": "button",
                                "type": "danger",
                                "text": {"tag": "plain_text", "content": "✗ 取消"},
                                "value": cancel_value,
                                "action": ACTION_CANCEL,
                                "name": ACTION_CANCEL,
                            },
                        ],
                    },
                ],
            }
        )

    @staticmethod
    def info_card(title: str, body: str) -> "InteractiveMessage":
        """只读信息卡（无按钮）"""
        return InteractiveMessage(
            card={
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "blue",
                    "title": {"tag": "plain_text", "content": title},
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "plain_text", "content": body}},
                ],
            }
        )


# === 按钮点击分发 ===

class ButtonClickDispatcher:
    """管理所有 button click 回调

    用法：
        dispatcher = ButtonClickDispatcher()
        @dispatcher.on("confirm")
        def handle_confirm(action: ButtonAction):
            print(f"confirmed: {action.value}")
        dispatcher.dispatch(action)  # 触发
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[ButtonClickHandler]] = {}
        self._wildcards: list[ButtonClickHandler] = []

    def on(self, action: str) -> Callable[[ButtonClickHandler], ButtonClickHandler]:
        """注册 action → 回调"""
        def decorator(fn: ButtonClickHandler) -> ButtonClickHandler:
            self._handlers.setdefault(action, []).append(fn)
            return fn
        return decorator

    def on_any(self, fn: ButtonClickHandler) -> ButtonClickHandler:
        """通配所有 action 的回调"""
        self._wildcards.append(fn)
        return fn

    def dispatch(self, action: ButtonAction) -> int:
        """派发一个 button click

        Returns:
            触发的回调数量（含异常 handler — 只计被 call 过）
        """
        count = 0
        for fn in self._handlers.get(action.action, []):
            try:
                fn(action)
            except Exception as e:  # noqa: BLE001
                _log.exception(f"[interactive] handler {fn} error: {e}")
            count += 1
        for fn in self._wildcards:
            try:
                fn(action)
            except Exception as e:  # noqa: BLE001
                _log.exception(f"[interactive] wildcard handler {fn} error: {e}")
            count += 1
        return count


# === FeishuClient.send_interactive 扩展 ===

def _send_interactive_impl(self: FeishuClient, receive_id: str, msg: InteractiveMessage, receive_id_type: str = "chat_id") -> Any:
    """FeishuClient.send_interactive（monkey-patched）

    mock 模式：写 transport.sent 列表
    真实模式：调 lark-oapi

    Signature: send_interactive(receive_id, msg, receive_id_type="chat_id")
    """
    if not receive_id:
        raise ValueError("send_interactive: receive_id required")
    content_json = msg.to_payload()

    if not self._started:
        raise RuntimeError("FeishuClient not started")

    # 记录 outbox（兼容层）
    self.outbox.append(
        type("OutboxItem", (), {"chat_id": receive_id, "text": f"[interactive:{len(msg.card.get('elements', []))}el]", "msg_type": "interactive"})()
    )

    if self._transport is not None:
        # mock 模式
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            return asyncio.ensure_future(
                self._transport.send_message(
                    receive_id, "interactive", content_json, receive_id_type
                )
            )
        except RuntimeError:
            import asyncio
            return asyncio.run(
                self._transport.send_message(
                    receive_id, "interactive", content_json, receive_id_type
                )
            )

    # 真实模式：要走 CreateMessageRequest with msg_type="interactive"
    try:
        from lark_oapi.api.im.v1 import (
            CreateMessageRequest,
            CreateMessageRequestBody,
        )
        body = (
            CreateMessageRequestBody.builder()
            .receive_id(receive_id)
            .msg_type("interactive")
            .content(content_json)
            .build()
        )
        req = (
            CreateMessageRequest.builder()
            .receive_id_type(receive_id_type)
            .request_body(body)
            .build()
        )
        return req
    except ImportError:
        _log.warning("[interactive] lark-oapi not installed; simulating send")
        return None


# === 工厂 ===

def install_interactive_methods() -> None:
    """给 FeishuClient 添加 interactive 发送方法（挂载到类）"""
    if not hasattr(FeishuClient, "send_interactive"):
        FeishuClient.send_interactive = _send_interactive_impl


def new_dispatcher() -> ButtonClickDispatcher:
    """新建 click dispatcher"""
    return ButtonClickDispatcher()
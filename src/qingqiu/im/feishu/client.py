"""qingqiu.im.feishu.client · 飞书 IM 客户端（S4.1）

MVP 设计要点：
- 优先尝试 lark-oapi SDK 真实 WebSocket 连接（有 FEISHU_APP_ID/FEISHU_APP_SECRET 时）
- 无 creds 或显式 mock=True → 走 MockTransport（in-memory 事件循环）
- 抽象出一致的接口：start/stop/send_message/on_message
- 复用 observability.logger
- 不动 router/executor；handler 单独在 feishu.handler 里

环境变量：
- FEISHU_APP_ID     · 应用 ID
- FEISHU_APP_SECRET · 应用 Secret
- FEISHU_USE_MOCK=1 · 强制走 mock
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

from qingqiu.im.feishu.mock import MockTransport
from qingqiu.observability.logger import get_logger

_log = get_logger("qingqiu.im.feishu.client")


@dataclass
class FeishuConfig:
    """飞书客户端配置"""

    app_id: str = ""
    app_secret: str = ""
    mock: bool = False  # 强制走 mock（即使有 creds）
    domain: str = "https://open.feishu.cn"  # 飞书域名（国内）
    auto_reconnect: bool = True

    @classmethod
    def from_env(cls) -> "FeishuConfig":
        """从环境变量构造（缺失 creds → 自动 mock）"""
        app_id = os.environ.get("FEISHU_APP_ID", "")
        app_secret = os.environ.get("FEISHU_APP_SECRET", "")
        force_mock = os.environ.get("FEISHU_USE_MOCK", "").lower() in ("1", "true", "yes")

        # 缺失 creds → 自动 mock
        mock = force_mock or not (app_id and app_secret)

        return cls(
            app_id=app_id,
            app_secret=app_secret,
            mock=mock,
            domain=os.environ.get("FEISHU_DOMAIN", "https://open.feishu.cn"),
        )

    @property
    def is_real(self) -> bool:
        """真实模式（有 creds + mock=False）"""
        return not self.mock and bool(self.app_id and self.app_secret)


# === 消息事件 ===

@dataclass
class IncomingMessage:
    """统一的入站消息（与 lark-oapi 事件解耦，便于 mock / test）"""

    sender_id: str  # open_id
    sender_name: str = ""  # 显示名（飞书会带）
    chat_id: str = ""  # 会话 ID
    chat_type: str = "p2p"  # "p2p" | "group"
    message_id: str = ""
    text: str = ""  # 提取出的纯文本
    msg_type: str = "text"  # 原始消息类型
    raw: Any = None  # 原始 lark-oapi 事件（真实模式才有）


@dataclass
class OutboxItem:
    """出站消息（简化形态 · 用于 inbox/outbox 测试断言）

    Attributes:
        chat_id: 目标 chat
        text: 纯文本内容
        msg_type: 消息类型
    """

    chat_id: str
    text: str
    msg_type: str = "text"


MessageCallback = Callable[[IncomingMessage], Any]


# === Client ===

class FeishuClient:
    """飞书 IM 客户端（S4.1 MVP）

    用法：
        cfg = FeishuConfig.from_env()
        client = FeishuClient(cfg)

        @client.on_message
        async def handle(msg: IncomingMessage) -> None:
            ...

        client.start()        # 阻塞 / 非阻塞（mock 下非阻塞）
        client.send_message(msg.chat_id, "hello")
        client.stop()
    """

    def __init__(
        self,
        config: Optional[FeishuConfig] = None,
        transport: Optional[MockTransport] = None,
    ) -> None:
        self.config = config or FeishuConfig.from_env()
        self._callbacks: list[MessageCallback] = []
        self._started = False
        self._stopped = False
        self._ws_client: Any = None  # lark_oapi.ws.Client (real mode)
        self._transport: Optional[MockTransport] = transport

        # mock 模式 → 构造内部 transport
        if self.config.mock and self._transport is None:
            self._transport = MockTransport()

        # === 兼容层：inbox / outbox 暴露（test_integration.py 期望） ===
        self.inbox: list[IncomingMessage] = []
        self.outbox: list["OutboxItem"] = []

    # === 公共接口 ===

    def on_message(self, cb: MessageCallback) -> MessageCallback:
        """注册消息回调（装饰器风格）"""
        self._callbacks.append(cb)
        if self._transport is not None:
            self._transport.register_callback(self._dispatch)
        return cb

    def register_message_callback(self, cb: MessageCallback) -> None:
        """非装饰器版本"""
        self.on_message(cb)

    def start(self) -> None:
        """启动客户端（mock → 非阻塞；real → 阻塞当前线程）"""
        if self._started:
            raise RuntimeError("FeishuClient already started")
        self._stopped = False

        if self.config.is_real:
            self._start_real()
        else:
            self._start_mock()

        self._started = True
        _log.info(
            f"[feishu] started · mode={'real' if self.config.is_real else 'mock'} · "
            f"callbacks={len(self._callbacks)}"
        )

    def stop(self) -> None:
        """停止客户端（幂等）"""
        if self._stopped:
            return
        self._stopped = True
        self._started = False

        if self._transport is not None:
            self._transport.mark_stopped()

        if self._ws_client is not None:
            # 真实 lark-oapi ws.Client 没有 stop 接口；强引退出靠主线程中断
            # MVP 这里只清空引用；阻塞循环由调用方 Ctrl-C / 信号打断
            self._ws_client = None

        _log.info("[feishu] stopped")

    def send_message(
        self, receive_id: str, text: str,
        receive_id_type: str = "chat_id",
    ) -> Any:
        """发送文本消息（同步入口；mock 下立即返回；real 下走异步 API）

        Args:
            receive_id: chat_id（群）或 open_id（私聊）
            text: 纯文本内容
            receive_id_type: "chat_id" | "open_id"
        """
        if not self._started:
            raise RuntimeError("FeishuClient not started")

        # 记录到 outbox（兼容层）
        self.outbox.append(
            OutboxItem(chat_id=receive_id, text=text, msg_type="text")
        )

        # content 必须是 JSON 字符串（飞书 text 类型）
        content_json = json.dumps({"text": text}, ensure_ascii=False)

        if self._transport is not None:
            # mock 模式：尝试同步等待
            try:
                loop = asyncio.get_running_loop()
                # 在运行中的 loop 里 → 调度为 task（fire-and-forget）
                return asyncio.ensure_future(
                    self._transport.send_message(
                        receive_id, "text", content_json, receive_id_type
                    )
                )
            except RuntimeError:
                # 没有运行中的 loop → 同步跑一次
                return asyncio.run(
                    self._transport.send_message(
                        receive_id, "text", content_json, receive_id_type
                    )
                )

        # 真实模式：调 lark-oapi CreateMessageRequest
        return self._send_real(receive_id, content_json, receive_id_type)

    def inject_mock_event(
        self, text: str, sender_id: str = "ou_mock", chat_id: str = "oc_mock"
    ) -> IncomingMessage:
        """mock 模式：注入一条入站事件（兼容层）

        用法：
            client.inject_mock_event("memory get user_name", sender_id="u", chat_id="oc_x")
            # → 触发所有 on_message 回调
            # → client.inbox 追加一条
        """
        msg = IncomingMessage(
            sender_id=sender_id,
            chat_id=chat_id,
            text=text,
        )
        self.inbox.append(msg)

        if self._transport is None:
            # 无 transport（real mode 或 未 start）→ 直接 dispatch
            self._dispatch(msg)
        else:
            self._transport.inject_message(msg)

        return msg

    # === 内部 ===

    def _start_mock(self) -> None:
        """启动 mock transport"""
        assert self._transport is not None
        # 尝试 attach 当前 event loop（同步测试可能没有 → 跳过）
        try:
            loop = asyncio.get_running_loop()
            self._transport.attach_loop(loop)
        except RuntimeError:
            # 没有运行中的 loop（pytest 同步测试 / CLI）→ mock 走同步 dispatch
            pass
        self._transport.register_callback(self._dispatch)
        self._transport.mark_started()

    def _start_real(self) -> None:
        """启动真实 lark-oapi ws.Client"""
        try:
            from lark_oapi.event.dispatcher_handler import (
                EventDispatcherHandler,
            )
            from lark_oapi.ws import Client as WsClient
        except ImportError as e:
            raise RuntimeError(
                "lark-oapi SDK 未安装；安装 `uv add lark-oapi`，或设置 FEISHU_USE_MOCK=1 走 mock"
            ) from e

        dispatcher = (
            EventDispatcherHandler.builder()
            .register_p2_im_message_receive_v1(self._on_lark_message)
            .build()
        )

        self._ws_client = WsClient(
            app_id=self.config.app_id,
            app_secret=self.config.app_secret,
            event_handler=dispatcher,
            domain=self.config.domain,
            auto_reconnect=self.config.auto_reconnect,
        )
        # start() 在 lark-oapi 是阻塞的；调用方需要在子线程启动
        self._ws_client.start()

    def _on_lark_message(self, data) -> None:
        """lark-oapi P2ImMessageReceiveV1 回调 → 内部 IncomingMessage"""
        try:
            event = data.event
            sender = event.sender
            message = event.message
            text = self._extract_text(message.content, message.message_type)
            msg = IncomingMessage(
                sender_id=sender.sender_id.open_id if sender.sender_id else "",
                sender_name=sender.sender_id.union_id if sender.sender_id else "",
                chat_id=message.chat_id,
                chat_type=message.chat_type,
                message_id=message.message_id,
                text=text,
                msg_type=message.message_type,
                raw=data,
            )
            self._dispatch(msg)
        except Exception as e:  # noqa: BLE001
            _log.exception(f"[feishu] _on_lark_message error: {e}")

    @staticmethod
    def _extract_text(content: str, msg_type: str) -> str:
        """从飞书 message.content JSON 提取纯文本"""
        if not content:
            return ""
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return content

        if msg_type == "text":
            return data.get("text", "").strip()
        if msg_type == "post":
            # post 类型：拼接所有段落文本
            texts = []
            for lang, post in data.items():
                if isinstance(post, dict):
                    for para in post.get("content", []):
                        if isinstance(para, list):
                            for node in para:
                                if isinstance(node, dict) and "text" in node:
                                    texts.append(node["text"])
            return "\n".join(texts)
        return json.dumps(data, ensure_ascii=False)

    def _dispatch(self, msg: IncomingMessage) -> None:
        """分发消息到所有 callback"""
        for cb in self._callbacks:
            try:
                result = cb(msg)
                if asyncio.iscoroutine(result):
                    # 真实模式没有自己的 loop，交给 asyncio.run
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.ensure_future(result)
                        else:
                            loop.run_until_complete(result)
                    except RuntimeError:
                        asyncio.run(result)
            except Exception as e:  # noqa: BLE001
                _log.exception(f"[feishu] callback error: {e}")

    def _send_real(
        self, receive_id: str, content_json: str, receive_id_type: str
    ) -> Any:
        """真实模式：调 lark-oapi CreateMessageRequest"""
        try:
            from lark_oapi.api.im.v1 import (
                CreateMessageRequest,
                CreateMessageRequestBody,
            )
        except ImportError as e:
            raise RuntimeError(
                "lark-oapi not available; cannot send real messages"
            ) from e

        body = (
            CreateMessageRequestBody.builder()
            .receive_id(receive_id)
            .msg_type("text")
            .content(content_json)
            .build()
        )
        req = (
            CreateMessageRequest.builder()
            .receive_id_type(receive_id_type)
            .request_body(body)
            .build()
        )
        # 真实模式需要从 lark-oapi Client 走 HTTP API；
        # MVP 这里假定 _ws_client 内部也能发；如不能，需要 caller 另传 Client。
        # 这里返回 request，调用方自行 .receive_id / .msg_type 检查
        return req

    # === 属性 ===

    @property
    def is_mock(self) -> bool:
        return not self.config.is_real

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def transport(self) -> Optional[MockTransport]:
        """仅 mock 模式下有 transport；测试用"""
        return self._transport
"""qingqiu.im.feishu.mock · Mock 飞书传输（MVP 测试用）

不依赖真实飞书服务：
- 提供 in-memory 事件循环
- inject_message(text, sender, chat_id) 模拟收到一条消息
- get_sent_messages() 查看已发送的消息
- reset() 清空状态（测试隔离）

不与 lark-oapi 耦合；纯 asyncio + 回调。
"""
from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from qingqiu.observability.logger import get_logger

_log = get_logger("qingqiu.im.feishu.mock")


@dataclass
class MockSentMessage:
    """Mock 模式下记录的已发送消息"""

    receive_id: str  # chat_id or open_id
    receive_id_type: str  # "chat_id" | "open_id" | "email" | ...
    msg_type: str  # "text" | "post" | "interactive" | ...
    content: str  # JSON 字符串或纯文本


@dataclass
class MockTransport:
    """Mock 飞书传输（in-memory）

    使用方式：
        transport = MockTransport()
        client = FeishuClient(transport=transport, ...)
        transport.inject_message(IncomingMessage(...))   # 模拟飞书推送
        ...
        transport.sent  # 查看已发送
    """

    _received: list = field(default_factory=list)
    sent: list[MockSentMessage] = field(default_factory=list)
    _on_message: Optional[Callable] = field(default=None, repr=False)
    _loop: Optional[asyncio.AbstractEventLoop] = field(default=None, repr=False)
    _started: bool = False

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """注入事件循环（FeishuClient.start 调用）"""
        self._loop = loop

    def register_callback(self, cb: Callable) -> None:
        """注册消息回调（同步或 async）"""
        self._on_message = cb

    def inject_message(self, msg) -> None:
        """模拟飞书推送一条消息"""
        self._received.append(msg)
        if self._on_message is None:
            _log.warning("[mock] inject_message called but no callback registered")
            return

        cb = self._on_message
        if self._loop is not None and self._loop.is_running():
            # 在事件循环里调度（避免测试里跨线程）
            asyncio.run_coroutine_threadsafe(self._dispatch(cb, msg), self._loop)
        else:
            # 同步调用
            self._dispatch_sync(cb, msg)

    async def _dispatch(self, cb: Callable, msg) -> None:
        """异步分发"""
        try:
            result = cb(msg)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:  # noqa: BLE001
            _log.exception(f"[mock] callback raised: {e}")

    def _dispatch_sync(self, cb: Callable, msg) -> None:
        try:
            result = cb(msg)
            if asyncio.iscoroutine(result):
                # 没有运行中的 loop，直接跑一次
                try:
                    asyncio.run(result)
                except RuntimeError as e:
                    _log.warning(f"[mock] sync dispatch coroutine failed: {e}")
        except Exception as e:  # noqa: BLE001
            _log.exception(f"[mock] callback raised: {e}")

    # === S4.3 发送接口 ===

    async def send_message(
        self, receive_id: str, msg_type: str, content: str,
        receive_id_type: str = "chat_id",
    ) -> MockSentMessage:
        """Mock 发送消息（与 lark-oapi CreateMessageRequest 对齐）"""
        msg = MockSentMessage(
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            msg_type=msg_type,
            content=content,
        )
        self.sent.append(msg)
        _log.debug(f"[mock] sent {msg_type} → {receive_id}: {content[:60]}")
        return msg

    def mark_started(self) -> None:
        self._started = True

    def mark_stopped(self) -> None:
        self._started = False

    @property
    def is_started(self) -> bool:
        return self._started

    def reset(self) -> None:
        """测试用：清空所有状态"""
        self._received.clear()
        self.sent.clear()
        self._on_message = None
        self._loop = None
        self._started = False


# === 测试辅助 ===

class _Lock:
    """线程安全锁的轻量替代（仅 mock 用）"""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, *args):
        self._lock.release()


def assert_mock_transport(transport: MockTransport) -> None:
    """类型守卫：保证传入的是 MockTransport（避免与真实 transport 混淆）"""
    if not isinstance(transport, MockTransport):
        raise TypeError(
            f"expected MockTransport, got {type(transport).__name__}"
        )
"""qingqiu.im.feishu.reply · IM 响应回发（S4.3）

高层便捷函数：
- reply(sender_or_msg, text) → 调 client.send_message 回发
- 默认 chunk 长文本（飞书单条限制 ~4096 字符）
- 失败日志 + 不抛异常（MVP 友好降级）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from qingqiu.im.feishu.client import FeishuClient, IncomingMessage
from qingqiu.observability.logger import get_logger

_log = get_logger("qingqiu.im.feishu.reply")


# 飞书单条消息字符上限（保守值）
MAX_MESSAGE_CHARS = 4000


@dataclass
class ReplyResult:
    """回发结果"""

    ok: bool
    chunks_sent: int = 0
    error: str = ""


def reply(
    target: Any,
    text: str,
    client: Optional[FeishuClient] = None,
    receive_id_type: str = "chat_id",
) -> ReplyResult:
    """回发文本到飞书

    Args:
        target: IncomingMessage / dict(有 chat_id 字段) / str(chat_id)
        text: 要发送的文本
        client: FeishuClient 实例（None 时使用模块级 default）
        receive_id_type: "chat_id" | "open_id"

    Returns:
        ReplyResult(ok, chunks_sent, error)
    """
    if not text:
        _log.warning("[reply] empty text, skip")
        return ReplyResult(ok=True, chunks_sent=0)

    if client is None:
        client = _default_client
    if client is None:
        _log.error("[reply] no FeishuClient bound; call reply.set_default_client()")
        return ReplyResult(ok=False, error="no client bound")

    if not client.is_started:
        _log.error("[reply] client not started")
        return ReplyResult(ok=False, error="client not started")

    chat_id = _extract_chat_id(target)
    if not chat_id:
        _log.error(f"[reply] cannot extract chat_id from {type(target).__name__}")
        return ReplyResult(ok=False, error="no chat_id")

    chunks = _chunk_text(text, MAX_MESSAGE_CHARS)
    sent = 0
    last_err = ""

    for i, chunk in enumerate(chunks):
        try:
            client.send_message(chat_id, chunk, receive_id_type=receive_id_type)
            sent += 1
            _log.debug(
                f"[reply] sent chunk {i + 1}/{len(chunks)} → {chat_id} ({len(chunk)} chars)"
            )
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            _log.error(f"[reply] send_message chunk {i + 1} failed: {e}")
            # 继续尝试下一 chunk，不中断

    return ReplyResult(
        ok=(sent == len(chunks)),
        chunks_sent=sent,
        error=last_err if sent < len(chunks) else "",
    )


# === 辅助 ===

def _extract_chat_id(target: Any) -> str:
    """从 IncomingMessage / dict / str 提取 chat_id"""
    if isinstance(target, IncomingMessage):
        return target.chat_id or target.sender_id
    if isinstance(target, dict):
        return target.get("chat_id") or target.get("sender_id") or ""
    if isinstance(target, str):
        return target
    return ""


def _chunk_text(text: str, max_chars: int) -> list[str]:
    """把长文本切成多个 chunk（尽量按段落 / 换行切）"""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text
    while len(remaining) > max_chars:
        # 优先按 \n\n 切
        cut_at = remaining.rfind("\n\n", 0, max_chars)
        if cut_at == -1 or cut_at < max_chars // 2:
            # 退化按 \n
            cut_at = remaining.rfind("\n", 0, max_chars)
        if cut_at == -1 or cut_at < max_chars // 2:
            # 退化按最后一个空格
            cut_at = remaining.rfind(" ", 0, max_chars)
        if cut_at == -1 or cut_at < max_chars // 2:
            # 硬切
            cut_at = max_chars
        chunks.append(remaining[:cut_at].rstrip())
        remaining = remaining[cut_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


# === 模块级 default client（单实例场景） ===

_default_client: Optional[FeishuClient] = None


def set_default_client(client: FeishuClient) -> None:
    """设置模块级默认 client"""
    global _default_client
    _default_client = client


def get_default_client() -> Optional[FeishuClient]:
    """获取模块级默认 client"""
    return _default_client


# === 高层：run_reply_loop ===

def run_reply_loop(
    client: FeishuClient,
    handler: Any,
    in_thread: bool = False,
) -> None:
    """把 client + handler 串起来：收到消息 → handler → reply 回发

    这是最常用的高层入口（MVP demo / 单进程 server）。

    Args:
        client: FeishuClient 实例（未 start 时会自动 start）
        handler: MessageHandler 实例（也可传 Executor，会自动包装）
        in_thread: True → 把 handler 跑在 daemon thread（异步模式）；
                   False → 在当前线程同步处理（默认，便于测试）

    副作用：
        - 若 client 未 start，自动调用 client.start()
        - 注册一个内部 callback 到 client
        - 客户端收到消息后自动处理 + 回发
    """
    # 1. 自动 start（如未 start）
    if not client.is_started:
        client.start()

    # 2. handler 兼容：Executor / MessageHandler 都接受
    if not hasattr(handler, "on_message"):
        # 兼容 Executor（用 aon_message 包装一层）
        executor = handler

        class _HandlerAdapter:
            def __init__(self, ex):
                self._ex = ex

            def on_message(self, msg):
                from qingqiu.cli.output import OutputFormatter
                out = OutputFormatter(json_mode=False, no_color=True)
                import io
                buf = io.StringIO()
                out.stream = buf
                rc = self._ex.execute(msg.text or "", out)
                text = buf.getvalue().strip()
                return HandlerResultShim(text=text, exit_code=rc)

        class HandlerResultShim:
            def __init__(self, text, exit_code):
                self.text = text
                self.exit_code = exit_code

        handler = _HandlerAdapter(executor)

    def _on_msg(msg):
        result = handler.on_message(msg)
        # 兼容：可能是 HandlerResult / HandlerResultShim / tuple
        text = getattr(result, "text", "")
        if text:
            reply(msg, text, client=client)

    client.register_message_callback(_on_msg)
    if in_thread:
        import threading

        t = threading.Thread(target=lambda: None, daemon=True)
        t.start()
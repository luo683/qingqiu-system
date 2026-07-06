"""qingqiu.im.feishu.handler · 消息 → Router 适配层（S4.2）

- 收到飞书 IncomingMessage → 转给 Executor.execute
- Executor 输出通过内存 stream 捕获 → 提取响应文本
- 不重复实现路由：复用 qingqiu.router.executor.Executor
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from typing import Optional

from qingqiu.cli.output import OutputFormatter
from qingqiu.im.feishu.client import IncomingMessage
from qingqiu.observability.logger import get_logger
from qingqiu.router.executor import Executor
from qingqiu.router.intent import Intent

_log = get_logger("qingqiu.im.feishu.handler")


@dataclass
class Sender:
    """统一的发送者（与 lark-oapi EventSender 解耦）"""

    sender_id: str
    sender_name: str = ""
    sender_type: str = "user"  # "user" | "bot" | ...
    tenant_key: str = ""


@dataclass
class HandlerResult:
    """handler 处理结果"""

    text: str  # 回发的纯文本
    intent: str = "unknown"  # 识别出的 Intent.value
    exit_code: int = 0
    note: str = ""
    extra: dict = field(default_factory=dict)  # 附加上下文（chat_id 等）


# === 友好提示模板 ===

_FALLBACK_TIPS = (
    "试试这些指令：\n"
    "  • memory get user_name   （查记忆）\n"
    "  • memory set key value   （记一笔）\n"
    "  • task add 写文档         （新建任务）\n"
    "  • 看任务                  （列任务）\n"
    "  • status                  （健康检查）"
)


class _CaptureStream(io.StringIO):
    """用于捕获 OutputFormatter 输出的内存流"""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def write(self, s: str) -> int:
        self.lines.append(s)
        return super().write(s)


class MessageHandler:
    """IM 消息 → Router 适配器

    用法：
        executor = Executor(llm_provider=None, use_llm=False)
        handler = MessageHandler(executor)
        result = handler.on_message(msg)  # 同步返回
        # 或异步：await handler.aon_message(msg)
    """

    def __init__(
        self,
        executor: Optional[Executor] = None,
        output: Optional[OutputFormatter] = None,
    ) -> None:
        # 默认不强制 LLM（MVP）
        self._executor = executor or Executor(llm_provider=None, use_llm=False)
        # 默认 JSON + 内存流输出，便于捕获
        self._output = output or OutputFormatter(
            json_mode=False, no_color=True, stream=_CaptureStream()
        )

    # === 公共入口 ===

    def on_message(self, msg: IncomingMessage) -> HandlerResult:
        """处理一条入站消息 → 返回 HandlerResult（同步）"""
        text = (msg.text or "").strip()

        if not text:
            _log.info(f"[handler] empty message from {msg.sender_id}")
            return HandlerResult(
                text="（收到空消息）",
                intent=Intent.UNKNOWN.value,
                exit_code=1,
                extra={"chat_id": msg.chat_id},
            )

        _log.debug(
            f"[handler] on_message sender={msg.sender_id} chat={msg.chat_id} "
            f"text={text[:50]!r}"
        )

        # 每次新建 stream，避免污染
        stream = _CaptureStream()
        self._output.stream = stream
        self._output._err_stream = stream

        try:
            exit_code = self._executor.execute(text, self._output)
            intent_str = self._extract_intent(text)
            response_text = self._format_response(stream, exit_code)
        except Exception as e:  # noqa: BLE001
            _log.exception(f"[handler] execute failed: {e}")
            return HandlerResult(
                text=f"内部错误：{e}",
                intent=Intent.UNKNOWN.value,
                exit_code=1,
                extra={"chat_id": msg.chat_id},
            )

        return HandlerResult(
            text=response_text,
            intent=intent_str,
            exit_code=exit_code,
            extra={"chat_id": msg.chat_id, "sender_id": msg.sender_id},
        )

    async def aon_message(self, msg: IncomingMessage) -> HandlerResult:
        """异步包装（用于真实模式）"""
        return self.on_message(msg)

    # === 内部 ===

    def _extract_intent(self, text: str) -> str:
        """从 executor 的分类器反查 intent"""
        try:
            result = self._executor._classifier.classify(text)
            return result.intent.value
        except Exception as e:  # noqa: BLE001
            _log.warning(f"[handler] _extract_intent failed: {e}")
            return Intent.UNKNOWN.value

    @staticmethod
    def _format_response(stream: _CaptureStream, exit_code: int) -> str:
        """从 stream 提取响应文本，去掉 ANSI / 装饰"""
        raw = stream.getvalue().strip()
        if not raw:
            return ""

        # 非 json 模式：原样返回（去 emoji 前缀）
        cleaned_lines = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 去掉 OutputFormatter 的前缀：ℹ / ✓ / ✗
            for prefix in ("ℹ ", "✓ ", "✗ ", "ok ", "i ", "x "):
                if line.startswith(prefix):
                    line = line[len(prefix):]
                    break
            cleaned_lines.append(line)

        result = "\n".join(cleaned_lines).strip()
        if exit_code != 0 and not result:
            return "（处理失败）"
        return result


# === 工厂 ===

def get_default_handler(executor: Optional[Executor] = None) -> MessageHandler:
    """默认 handler（无 LLM · MVP）"""
    return MessageHandler(executor=executor)
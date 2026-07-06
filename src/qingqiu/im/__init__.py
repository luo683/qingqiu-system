"""qingqiu.im · 飞书 IM 接入（M4）

S4.1 / S4.2 / S4.3 MVP 切片：
- feishu.client · 飞书 WebSocket 客户端（lark-oapi SDK · 可 fallback mock）
- feishu.handler · 消息 → Router（Executor.execute）
- feishu.reply · IM 响应回发

约束（来自 task_prompt_M4.json）：
- 不动 llm/ memory/ cli/ security/ personality/ chat/ planner/ daemon/ router/ voice/
- 复用 router.executor.Executor
- 复用 observability.logger
- mock-first：无真实 credentials 时自动走 mock transport
"""

from qingqiu.im.feishu.client import FeishuClient, FeishuConfig
from qingqiu.im.feishu.handler import (
    IncomingMessage,
    MessageHandler,
    Sender,
    get_default_handler,
)
from qingqiu.im.feishu.reply import reply

__all__ = [
    "FeishuClient",
    "FeishuConfig",
    "MessageHandler",
    "IncomingMessage",
    "Sender",
    "get_default_handler",
    "reply",
]
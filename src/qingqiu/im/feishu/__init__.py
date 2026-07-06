"""qingqiu.im.feishu · 飞书 IM 子包（M4）

对外暴露：
- FeishuClient：飞书 WebSocket 客户端（lark-oapi 或 mock）
- MessageHandler：消息 → Router 适配层
- reply：响应回发便捷函数
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
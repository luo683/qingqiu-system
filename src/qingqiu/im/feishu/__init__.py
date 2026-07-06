"""qingqiu.im.feishu · 飞书 IM 子包（M4 + S4.4）

对外暴露：
- FeishuClient：飞书 WebSocket 客户端（lark-oapi 或 mock）
- MessageHandler：消息 → Router 适配层
- reply：响应回发便捷函数
- InteractiveMessage：卡片消息（S4.4）
- ButtonClickDispatcher：按钮点击分发（S4.4）
"""

from qingqiu.im.feishu.client import FeishuClient, FeishuConfig
from qingqiu.im.feishu.handler import (
    IncomingMessage,
    MessageHandler,
    Sender,
    get_default_handler,
)
from qingqiu.im.feishu.interactive import (
    ACTION_CANCEL,
    ACTION_CONFIRM,
    ACTION_VIEW,
    ButtonAction,
    ButtonClickDispatcher,
    InteractiveMessage,
    install_interactive_methods,
    new_dispatcher,
)
from qingqiu.im.feishu.reply import reply

# 自动挂载 send_interactive 方法
install_interactive_methods()

__all__ = [
    "FeishuClient",
    "FeishuConfig",
    "MessageHandler",
    "IncomingMessage",
    "Sender",
    "get_default_handler",
    "reply",
    # S4.4
    "ACTION_CONFIRM",
    "ACTION_CANCEL",
    "ACTION_VIEW",
    "ButtonAction",
    "ButtonClickDispatcher",
    "InteractiveMessage",
    "install_interactive_methods",
    "new_dispatcher",
]  # noqa: E501
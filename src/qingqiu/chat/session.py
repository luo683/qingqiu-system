"""chat.session · Chat 多轮会话管理（P0-2 实装）

- 单 session = List[Message]
- 复用 LLMProvider.complete
- 复用 PersonalityConfig.system_prompt
- 复用 Memory L0 持久化（可选）
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from qingqiu.llm import Message


@dataclass
class ChatSession:
    """单次 chat session"""

    session_id: str = field(default_factory=lambda: f"chat-{uuid.uuid4().hex[:8]}")
    messages: list[Message] = field(default_factory=list)
    system_prompt: str = ""
    max_history: int = 20  # 保留最近 20 轮

    def add_user(self, content: str) -> None:
        self.messages.append(Message(role="user", content=content))
        self._trim()

    def add_assistant(self, content: str) -> None:
        self.messages.append(Message(role="assistant", content=content))
        self._trim()

    def _trim(self) -> None:
        """超过 max_history 时丢弃最早 user/assistant 对（保留 system）"""
        if len(self.messages) <= self.max_history:
            return
        # 保留 system + 最近 max_history 条
        non_system = [m for m in self.messages if m.role != "system"]
        if len(non_system) <= self.max_history:
            return
        keep = non_system[-self.max_history :]
        system_msgs = [m for m in self.messages if m.role == "system"]
        self.messages = system_msgs + keep

    def to_messages(self) -> list[Message]:
        """组装 LLM 调用的 messages（system 在前 + 历史）"""
        msgs: list[Message] = []
        if self.system_prompt:
            msgs.append(Message(role="system", content=self.system_prompt))
        msgs.extend(self.messages)
        return msgs


async def chat_turn(session: ChatSession, user_input: str, provider) -> str:
    """单轮 chat：调 LLM + 记录历史"""
    session.add_user(user_input)
    response = await provider.complete(session.to_messages(), max_tokens=1024)
    session.add_assistant(response.content)
    return response.content


def chat_repl(provider, session: ChatSession, input_fn=input, output_fn=print) -> int:
    """交互 REPL（CLI 入口）

    input_fn/output_fn 可注入（测试用）
    """
    if not session.system_prompt:
        session.system_prompt = "你是清秋，给 ROG 个人使用。"

    output_fn(f"[chat] session={session.session_id} · model={provider.__class__.__name__}")
    output_fn("[chat] 输入 /quit 退出，/clear 清空历史")

    while True:
        try:
            user_input = input_fn("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            output_fn("\n[chat] bye")
            return 0

        if not user_input:
            continue
        if user_input == "/quit":
            output_fn("[chat] bye")
            return 0
        if user_input == "/clear":
            session.messages.clear()
            output_fn("[chat] history cleared")
            continue

        try:
            answer = asyncio.run(chat_turn(session, user_input, provider))
            output_fn(f"qingqiu> {answer}")
        except Exception as e:
            output_fn(f"[chat] LLM error: {type(e).__name__}: {e}")
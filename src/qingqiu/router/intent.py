"""router.intent · 意图枚举

S2.2 Router 意图识别（IMPLEMENTATION-PLAN §M2 · S2.2）

支持的所有意图（基于现有 CLI 子命令）：
"""

from __future__ import annotations

from enum import Enum


class Intent(str, Enum):
    """用户输入的意图分类

    按 M2 现有 CLI 子命令映射：
    - ASK / CHAT: 单次提问 / 交互对话（M2 占位）
    - TASK_*: 任务管理
    - MEMORY_*: 记忆管理
    - STATUS: 健康状态
    - CONFIG_*: 配置管理
    - LLM_*: LLM provider 管理
    - UNKNOWN: 无法识别（fallback）
    """

    # 单次交互
    ASK = "ask"
    CHAT = "chat"

    # 任务管理
    TASK_LIST = "task_list"
    TASK_SHOW = "task_show"
    TASK_ADD = "task_add"
    TASK_DONE = "task_done"
    TASK_ARCHIVE = "task_archive"

    # 记忆管理
    MEMORY_GET = "memory_get"
    MEMORY_SET = "memory_set"
    MEMORY_LIST = "memory_list"
    MEMORY_DELETE = "memory_delete"
    MEMORY_SEARCH = "memory_search"

    # 系统
    STATUS = "status"
    CONFIG_SHOW = "config_show"
    CONFIG_PATH = "config_path"

    # LLM
    LLM_TEST = "llm_test"

    # Fallback
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, s: str) -> "Intent":
        """从字符串解析（容错）"""
        s = (s or "").strip().lower()
        for member in cls:
            if member.value == s:
                return member
        return cls.UNKNOWN

    @property
    def cli_subcommand(self) -> tuple[str, str | None]:
        """映射到 (subcommand, subaction) for CLI 派发

        例：
        - Intent.TASK_ADD → ("task", "add")
        - Intent.MEMORY_GET → ("memory", "get")
        - Intent.ASK → ("ask", None)
        """
        mapping: dict[Intent, tuple[str, str | None]] = {
            Intent.ASK: ("ask", None),
            Intent.CHAT: ("chat", None),
            Intent.TASK_LIST: ("task", "list"),
            Intent.TASK_SHOW: ("task", "show"),
            Intent.TASK_ADD: ("task", "add"),
            Intent.TASK_DONE: ("task", "done"),
            Intent.TASK_ARCHIVE: ("task", "archive"),
            Intent.MEMORY_GET: ("memory", "get"),
            Intent.MEMORY_SET: ("memory", "set"),
            Intent.MEMORY_LIST: ("memory", "list"),
            Intent.MEMORY_DELETE: ("memory", "delete"),
            Intent.MEMORY_SEARCH: ("memory", "search"),
            Intent.STATUS: ("status", None),
            Intent.CONFIG_SHOW: ("config", "show"),
            Intent.CONFIG_PATH: ("config", "path"),
            Intent.LLM_TEST: ("llm", "test"),
            Intent.UNKNOWN: ("", None),
        }
        return mapping[self]
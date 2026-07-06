"""security.blacklist · 危险操作黑名单

S5.3 切片（PRD §6.3）：

shell 命令级：
- ``rm -rf`` / ``rm -fr``（递归删除）
- ``git push --force`` / ``git push -f``
- ``format c:``（格式化盘符）
- 改系统配置（``reg add`` / ``systemctl stop|disable|mask`` / ``chmod 777 /``）

操作级：
- 发送邮件 / IM
- 上传文件到云端 / 第三方
- 跨白名单目录移动文件
- 读取私密文件
- 导出记忆库 / 用户偏好
- 批量修改/删除 vault 笔记

设计要点：
- 命中黑名单默认抛 :class:`BlacklistError`（code=1 · 用户错），由上层
  决定是否 prompt 用户二次确认；本模块本身不阻断。
- 模式按 ``re.IGNORECASE`` 编译，``RM -rf foo`` 等大小写变体也能识别。
- 提供 ``is_*_blacklisted`` 不抛异常的版本，用于前置判断。
"""

from __future__ import annotations

import re
from enum import Enum

from qingqiu.cli.errors import CLIError


class BlacklistError(CLIError):
    """命中危险操作黑名单时抛出。

    exit code = 1（用户错）—— 表示应当让用户明确确认后绕过，
    而非静默放行。本模块只负责"抛"，不负责"阻断"。
    """

    code = 1


class OperationType(str, Enum):
    """与 shell 命令无关的高层"操作"枚举。"""

    EMAIL_SEND = "email_send"
    IM_SEND = "im_send"
    CLOUD_UPLOAD = "cloud_upload"
    CROSS_DIR_MOVE = "cross_dir_move"
    PRIVATE_FILE_READ = "private_file_read"
    MEMORY_EXPORT = "memory_export"
    VAULT_BATCH_MODIFY = "vault_batch_modify"
    VAULT_DELETE = "vault_delete"


# Shell 命令黑名单（regex 源串，公开供文档/审计引用）
SHELL_PATTERNS: list[str] = [
    r"\brm\s+(-[rRfF]*[rRfF]|-[rRfF]+\s+\S+|.*-r.*\s+/)\b",  # rm -rf / -fr / rm * -r /
    r"\bgit\s+push\s+(.*\s)?--?force\b",  # git push --force / -force
    r"\bgit\s+push\s+-f\b",  # git push -f
    r"\bformat\s+[a-zA-Z]:",  # format c: / format X:
    r"\breg\s+add\b",  # Windows 注册表写入
    r"\bsystemctl\s+(stop|disable|mask)\b",  # Linux 服务停用
    r"\bchmod\s+(-R\s+)?777\s+/",  # chmod 777 /（root 全开；末尾无 \b，因为 / 之后常跟非 word 字符或字符串尾）
]

# 预编译（大小写不敏感：`RM -rf foo` 也命中）
_SHELL_PATTERNS_COMPILED: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE) for p in SHELL_PATTERNS
)


BLOCKED_OPERATIONS: set[OperationType] = {
    OperationType.EMAIL_SEND,
    OperationType.IM_SEND,
    OperationType.CLOUD_UPLOAD,
    OperationType.CROSS_DIR_MOVE,
    OperationType.PRIVATE_FILE_READ,
    OperationType.MEMORY_EXPORT,
    OperationType.VAULT_BATCH_MODIFY,
    OperationType.VAULT_DELETE,
}


def _match_shell(command: str) -> re.Match[str] | None:
    """返回首个命中的 match 对象；无命中返回 None。"""
    for pat in _SHELL_PATTERNS_COMPILED:
        m = pat.search(command)
        if m is not None:
            return m
    return None


def check_shell(command: str) -> None:
    """检查 shell 命令是否命中黑名单；命中抛 :class:`BlacklistError`。

    错误信息会包含具体命中的模式片段，方便审计/回溯。
    """
    m = _match_shell(command)
    if m is not None:
        raise BlacklistError(
            f"shell 命令命中危险操作黑名单: {command!r}",
            hint=f"命中的片段: {m.group(0)!r}（如确需执行，请用户显式确认）",
        )


def is_blacklisted_shell(command: str) -> bool:
    """``check_shell`` 的不抛异常版本；命中返回 True。"""
    return _match_shell(command) is not None


def check_operation(op: OperationType) -> None:
    """检查高层操作是否在黑名单；命中抛 :class:`BlacklistError`。"""
    if op in BLOCKED_OPERATIONS:
        raise BlacklistError(
            f"操作命中危险操作黑名单: {op.value!r}",
            hint="如确需执行，请用户显式确认后再调用。",
        )


def is_blacklisted_operation(op: OperationType) -> bool:
    """``check_operation`` 的不抛异常版本；命中返回 True。"""
    return op in BLOCKED_OPERATIONS

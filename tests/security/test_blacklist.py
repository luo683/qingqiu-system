"""S5.3 测试 · 危险操作黑名单（shell + operation）"""

from __future__ import annotations

import pytest

from qingqiu.cli.errors import CLIError
from qingqiu.security.blacklist import (
    BLOCKED_OPERATIONS,
    OperationType,
    check_operation,
    check_shell,
    is_blacklisted_operation,
    is_blacklisted_shell,
)
from qingqiu.security.blacklist import BlacklistError  # re-export for clarity


# === 黑名单 shell 命令 ===

@pytest.mark.parametrize(
    "cmd",
    [
        "rm -rf /tmp/test",
        "rm -fr foo",
        "rm -rf /",
        "rm  -rf /tmp/multi",  # 多空格
        "RM -rf /tmp/case",  # 大小写混合
        "git push --force",
        "git push --force origin main",
        "git push -f origin main",
        "git push -f",
        "format c:",
        "format d:",
        "reg add HKLM\\Software\\Foo bar",
        "systemctl stop nginx",
        "systemctl disable nginx",
        "systemctl mask nginx",
        "chmod 777 /",
        "chmod -R 777 /",
    ],
)
def test_shell_blacklisted(cmd: str) -> None:
    with pytest.raises(BlacklistError):
        check_shell(cmd)


# === 安全 shell 命令 ===

@pytest.mark.parametrize(
    "cmd",
    [
        "ls /tmp",
        "rm file.txt",  # 没有 -r
        "rm -i foo",  # -i 不是 r/f
        "git push origin main",
        "git status",
        "echo hello",
        "mkdir -p /tmp/test",
    ],
)
def test_shell_safe_passes(cmd: str) -> None:
    check_shell(cmd)  # 不抛即通过


# === is_blacklisted_shell 不抛异常 ===

def test_is_blacklisted_shell_blocks() -> None:
    assert is_blacklisted_shell("rm -rf /") is True
    assert is_blacklisted_shell("git push --force origin main") is True
    assert is_blacklisted_shell("format c:") is True


def test_is_blacklisted_shell_safe() -> None:
    assert is_blacklisted_shell("echo hello") is False
    assert is_blacklisted_shell("ls /tmp") is False
    assert is_blacklisted_shell("git push origin main") is False


# === 黑名单操作（OperationType） ===

@pytest.mark.parametrize(
    "op",
    [
        OperationType.EMAIL_SEND,
        OperationType.IM_SEND,
        OperationType.CLOUD_UPLOAD,
        OperationType.CROSS_DIR_MOVE,
        OperationType.PRIVATE_FILE_READ,
        OperationType.MEMORY_EXPORT,
        OperationType.VAULT_BATCH_MODIFY,
        OperationType.VAULT_DELETE,
    ],
)
def test_operation_blacklisted(op: OperationType) -> None:
    with pytest.raises(BlacklistError):
        check_operation(op)


def test_operation_blacklist_set_complete() -> None:
    """BLOCKED_OPERATIONS 应包含全部 8 个 OperationType。"""
    assert len(BLOCKED_OPERATIONS) == 8
    assert BLOCKED_OPERATIONS == set(OperationType)


def test_is_blacklisted_operation_returns_true() -> None:
    assert is_blacklisted_operation(OperationType.VAULT_BATCH_MODIFY) is True


# === BlacklistError 是 CLIError 子类，code=1 ===

def test_blacklist_error_is_cli_error() -> None:
    err = BlacklistError("test")
    assert isinstance(err, CLIError)
    assert err.code == 1
    assert err.message == "test"


def test_blacklist_error_message_contains_input() -> None:
    """错误信息应回显原始输入，方便审计定位。"""
    with pytest.raises(BlacklistError) as exc_info:
        check_shell("rm -rf /tmp/x")
    assert "rm -rf /tmp/x" in str(exc_info.value)

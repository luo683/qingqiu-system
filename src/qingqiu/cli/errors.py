"""cli.errors · CLI 异常体系 + exit code 映射

S2.1 验收：友好错误提示 + exit code 规范（0 OK / 1 用户错 / 2 系统错 / 130 SIGINT）
"""

from __future__ import annotations


class CLIError(Exception):
    """CLI 错误基类"""

    code: int = 1
    """退出码（默认 1 = 用户错）"""

    hint: str | None = None
    """可选的修复提示"""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if hint is not None:
            self.hint = hint

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message} (hint: {self.hint})"
        return self.message


class UserError(CLIError):
    """用户错（参数、用法、值域）"""

    code = 1


class SystemError_(CLIError):
    """系统错（IO、网络、数据库、权限）"""

    code = 2


class NotFoundError(UserError):
    """资源不存在（task id / memory key）"""


class AlreadyExistsError(UserError):
    """资源已存在（重复创建）"""


class ValidationError(UserError):
    """参数校验失败"""


class ConfigError(SystemError_):
    """配置文件错误"""


class StorageError(SystemError_):
    """存储层错误（SQLite / Markdown IO）"""
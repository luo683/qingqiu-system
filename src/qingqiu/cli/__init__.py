"""qingqiu.cli · 子命令入口包

S2.1 重构：
- 老 cli.py (单文件 167 行) → 拆成 cli/ 包
- cli/main.py 装配 parser + dispatch
- cli/errors.py + cli/output.py 通用基础设施
- cli/memory.py 子命令（接 S1.5 facade）
- 后续：cli/ask.py / cli/chat.py / cli/task.py / cli/status.py / cli/config.py / cli/llm.py

pyproject.toml 入口：`qingqiu.cli:main` （由本 __init__.py 暴露）
"""

from qingqiu.cli.errors import (
    AlreadyExistsError,
    CLIError,
    ConfigError,
    NotFoundError,
    StorageError,
    SystemError_,
    UserError,
    ValidationError,
)
from qingqiu.cli.main import main
from qingqiu.cli.output import OutputFormatter

__all__ = [
    "main",  # pyproject.toml entry_point
    "OutputFormatter",
    "CLIError",
    "UserError",
    "SystemError_",
    "NotFoundError",
    "AlreadyExistsError",
    "ValidationError",
    "ConfigError",
    "StorageError",
]
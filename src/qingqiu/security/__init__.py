"""qingqiu.security · 安全相关（白名单 / 黑名单 / Confirm / 私密）

S5.1 阶段：confirm（写入前 Confirm 框架）
S5.2 阶段：whitelist（白名单）
S5.3 阶段：blacklist（黑名单）
S5.4 阶段：private_detect（私密识别 Detect）
S5.5 阶段：sensitive（私密处理 Block + Redact）
"""

from qingqiu.security.blacklist import (
    BLOCKED_OPERATIONS,
    SHELL_PATTERNS,
    BlacklistError,
    OperationType,
    check_operation,
    check_shell,
    is_blacklisted_operation,
    is_blacklisted_shell,
)
from qingqiu.security.confirm import (
    CLIPrompter,
    Confirm,
    ConfirmRejected,
    ConfirmTimeout,
    Prompter,
    ask,
    get_default_confirm,
)
from qingqiu.security.sensitive import (
    REDACT_PATTERNS,
    SENSITIVE_TYPES,
    BlockHandler,
    PrivateDetectResult,
    RedactHandler,
    SensitiveBlockError,
    SensitiveDetector,
    SensitiveField,
    SensitiveType,
)
from qingqiu.security.whitelist import (
    WHITELIST_DIRS,
    WhitelistError,
    check_path,
    is_whitelisted,
    resolve,
)

__all__ = [
    # whitelist (S5.2)
    "WHITELIST_DIRS",
    "WhitelistError",
    "is_whitelisted",
    "check_path",
    "resolve",
    # blacklist (S5.3)
    "BLOCKED_OPERATIONS",
    "SHELL_PATTERNS",
    "BlacklistError",
    "OperationType",
    "check_shell",
    "check_operation",
    "is_blacklisted_shell",
    "is_blacklisted_operation",
    # confirm (S5.1)
    "Prompter",
    "CLIPrompter",
    "Confirm",
    "ConfirmRejected",
    "ConfirmTimeout",
    "ask",
    "get_default_confirm",
    # sensitive (S5.5)
    "REDACT_PATTERNS",
    "SENSITIVE_TYPES",
    "BlockHandler",
    "PrivateDetectResult",
    "RedactHandler",
    "SensitiveBlockError",
    "SensitiveDetector",
    "SensitiveField",
    "SensitiveType",
]
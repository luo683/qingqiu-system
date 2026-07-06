"""security.sensitive · 私密处理 Block + Redact (脱敏映射)

S5.5 切片（PRD §6.4 · 私密信息保护 · 第二、三道闸）。

- :class:`PrivateDetector`（S5.4）只负责"识别"
- 本模块负责"处置"：命中 → Block / Redact
- 例外通道：``QINGQIU_INCLUDE_PRIVATE=1[;ts=<ISO8601>]``（1h TTL）·
  ``QINGQIU_REDACT_ONLY=1``

三道闸分工（S5.4 + S5.5 + S5.6）：
- Detect（S5.4）：识别 → ``PrivateMatch`` 列表
- Block（本模块）：命中 → 抛 ``SensitiveBlockError``
- Redact（本模块）：命中 → ``{local}***@{domain}`` 等脱敏形式
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Callable

from qingqiu.cli.errors import NotFoundError
from qingqiu.security.private_detect import (
    PrivateDetector,
    PrivateMatch,
    _id_card_valid,
)


# === 敏感类型枚举 ===

class SensitiveType(str, Enum):
    """私密字段类型（按检测优先级排序 · 优先级高的先匹配）"""

    ID_CARD = "id_card"
    PHONE = "phone"
    EMAIL = "email"
    CARD = "card"
    AWS_KEY = "aws_key"
    GITHUB_TOKEN = "github_token"
    JWT = "jwt"


SENSITIVE_TYPES: tuple[SensitiveType, ...] = tuple(SensitiveType)
"""所有敏感类型（按优先级排序 · 检测/脱敏顺序）。"""


# === 通道枚举（S5.6）===

class Channel(str, Enum):
    """私密信息通道 · 控制 Block/Redact/Allow 行为"""

    BLOCK = "block"  # 默认：命中即 Block（exit 1）
    REDACT = "redact"  # 命中即脱敏后输出
    PRIVATE_SEND = "private_send"  # S5.6：私密发送（强制 include_private + audit log）


def private_send_check(text: str, detector, audit_log=None) -> str:
    """私密发送通道：强制 require include_private 例外 + 写 audit log

    Args:
        text: 待发送内容
        detector: SensitiveDetector 实例
        audit_log: 可选 audit log 写入路径

    Returns:
        原 text（如开启 include_private 例外）或 raises SensitiveBlockError
    """
    result = detector.check_text(text)
    if not result.has_private:
        return text

    # 私密发送强制 require INCLUDE_PRIVATE 例外
    from qingqiu.security.sensitive import _include_private_enabled

    if not _include_private_enabled():
        raise SensitiveBlockError(
            f"private_send 检测到 {len(result.matches)} 个私密字段，"
            f"需先设置 QINGQIU_INCLUDE_PRIVATE=1;ts=<ISO8601> 开启例外（1h TTL）"
        )

    # 写 audit log
    if audit_log:
        from datetime import datetime

        Path(audit_log).parent.mkdir(parents=True, exist_ok=True)
        with Path(audit_log).open("a", encoding="utf-8") as f:
            ts = datetime.now().isoformat(timespec="seconds")
            types = ",".join(m.match_type for m in result.matches)
            f.write(f"[{ts}] private_send types={types} len={len(text)}\n")

    return text


# === 异常 ===

class SensitiveBlockError(NotFoundError):
    """检测到私密信息时由 BlockHandler 抛出。

    exit code = 1（用户错）；继承 :class:`NotFoundError` 以兼容 CLI 异常体系。
    """


# === PrivateDetector 结果聚合 ===

@dataclass(frozen=True)
class PrivateDetectResult:
    """PrivateDetector 检测结果聚合。"""

    matches: list[PrivateMatch]

    @property
    def has_private(self) -> bool:
        """是否存在任一私密命中"""
        return len(self.matches) > 0

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.matches)

    def __len__(self) -> int:
        return len(self.matches)


# === SensitiveField（识别 + 脱敏字段） ===

@dataclass(frozen=True)
class SensitiveField:
    """单个私密字段（识别结果 + 脱敏值）"""

    type: SensitiveType
    value: str
    masked: str


# === 脱敏映射函数（私有） ===

def _redact_email(email: str) -> str:
    """Email: 保留 local + *** + @ + domain（例 ``rog@qq.com`` → ``rog***@qq.com``）"""
    local, _, domain = email.partition("@")
    if not domain:
        return email
    return f"{local}***@{domain}"


def _redact_card(card: str) -> str:
    """银行卡: ****-****-****-last4"""
    last4 = card[-4:]
    return f"****-****-****-{last4}"


def _redact_token(token: str, *, head: int = 4, tail: int = 4) -> str:
    """通用 token: head + **** + tail"""
    if len(token) <= head + tail:
        return "****"
    return f"{token[:head]}****{token[-tail:]}"


REDACT_PATTERNS: dict[SensitiveType, Callable[[str], str]] = {
    SensitiveType.ID_CARD: lambda v: f"{v[:6]}****{v[-4:]}",
    SensitiveType.PHONE: lambda v: f"{v[:3]}****{v[-4:]}",
    SensitiveType.EMAIL: _redact_email,
    SensitiveType.CARD: _redact_card,
    SensitiveType.AWS_KEY: lambda v: _redact_token(v, head=4, tail=4),
    SensitiveType.GITHUB_TOKEN: lambda v: _redact_token(v, head=7, tail=4),
    SensitiveType.JWT: lambda v: _redact_token(v, head=10, tail=6),
}


# === 类型 → 正则（复用 S5.4 模式） ===

_TYPE_TO_PATTERN_NAME: dict[SensitiveType, str] = {
    SensitiveType.ID_CARD: "id_card_18",
    SensitiveType.PHONE: "cn_mobile",
    SensitiveType.EMAIL: "email",
    SensitiveType.CARD: "bank_card",
    SensitiveType.AWS_KEY: "aws_access_key",
    SensitiveType.GITHUB_TOKEN: "github_token",
    SensitiveType.JWT: "jwt_token",
}


def _compile_regexes() -> dict[SensitiveType, re.Pattern[str]]:
    """从 S5.4 CONTENT_PATTERNS 编译（运行期）"""
    out: dict[SensitiveType, re.Pattern[str]] = {}
    for sensitive_type, pattern_name in _TYPE_TO_PATTERN_NAME.items():
        src = PrivateDetector.CONTENT_PATTERNS.get(pattern_name)
        if src is None:
            continue
        out[sensitive_type] = re.compile(src)
    return out


_TYPE_REGEXES: dict[SensitiveType, re.Pattern[str]] = _compile_regexes()


# === 例外通道 env var 检查（S5.6 完整三档）===

_INCLUDE_TTL = timedelta(hours=1)


def _parse_ttl(raw: str, ttl: timedelta) -> bool:
    """通用 TTL 解析（QINGQIU_X=1;ts=<ISO8601> 形式）"""
    if not raw:
        return False
    parts = raw.split(";")
    if parts[0] != "1":
        return False
    for p in parts[1:]:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        if k == "ts":
            try:
                ts = datetime.fromisoformat(v)
            except ValueError:
                return False
            if datetime.now() - ts > ttl:
                return False
    return True


def _include_private_enabled() -> bool:
    """``QINGQIU_INCLUDE_PRIVATE`` 是否启用（含 1h TTL）。

    格式：
      - ``=1`` → 启用，无 TTL（用户需手动 unset）
      - ``=1;ts=<ISO8601>`` → 启用，1h 后自动失效
      - ``=0`` / 未设 → 禁用
    """
    return _parse_ttl(os.getenv("QINGQIU_INCLUDE_PRIVATE", ""), _INCLUDE_TTL)


def _redact_only_enabled() -> bool:
    """``QINGQIU_REDACT_ONLY=1`` 是否启用（含 1h TTL）"""
    return _parse_ttl(os.getenv("QINGQIU_REDACT_ONLY", ""), _INCLUDE_TTL)


def _private_send_enabled() -> bool:
    """``QINGQIU_PRIVATE_SEND=1`` 是否启用（S5.6 私密发送通道 · 含 1h TTL）

    格式同 INCLUDE_PRIVATE。
    """
    return _parse_ttl(os.getenv("QINGQIU_PRIVATE_SEND", ""), _INCLUDE_TTL)


def get_exception_channel() -> str:
    """返回当前激活的例外通道（None = 无 / "include" / "redact" / "private_send"）

    优先级：private_send > include > redact
    """
    if _private_send_enabled():
        return "private_send"
    if _include_private_enabled():
        return "include"
    if _redact_only_enabled():
        return "redact"
    return "none"


# === 主检测器 ===

class SensitiveDetector:
    """私密字段检测器 + 脱敏器（无状态 · 线程安全）。"""

    def __init__(self, private_detector: PrivateDetector | None = None) -> None:
        self._detector = private_detector or PrivateDetector()

    # --- 检测 ---

    def check_text(self, text: str) -> PrivateDetectResult:
        """检测文本，返回 :class:`PrivateDetectResult`"""
        return PrivateDetectResult(matches=self._detector.detect_content(text))

    def check_file(self, path: Path) -> PrivateDetectResult:
        """检测文件（路径 + 文件名 + 内容）"""
        return PrivateDetectResult(matches=self._detector.detect_file(path))

    # --- 分类 + 脱敏 ---

    def classify(self, text: str) -> list[SensitiveField]:
        """识别 + 分类 + 计算 masked 值（按 SENSITIVE_TYPES 优先级去重）"""
        seen: set[str] = set()
        out: list[SensitiveField] = []
        for sensitive_type in SENSITIVE_TYPES:
            regex = _TYPE_REGEXES.get(sensitive_type)
            if regex is None:
                continue
            for m in regex.finditer(text):
                value = m.group(0)
                if value in seen:
                    continue
                # 身份证需通过 GB 11643-1999 校验位
                if sensitive_type == SensitiveType.ID_CARD and not _id_card_valid(value):
                    continue
                seen.add(value)
                out.append(SensitiveField(
                    type=sensitive_type,
                    value=value,
                    masked=REDACT_PATTERNS[sensitive_type](value),
                ))
        return out

    def redact_text(self, text: str) -> str:
        """将文本中所有私密字段替换为 masked（按值长度倒序替换避免局部覆盖）"""
        fields = self.classify(text)
        if not fields:
            return text
        # 按 value 长度倒序替换（避免短串先替换后被长串包含）
        result = text
        for field in sorted(fields, key=lambda f: -len(f.value)):
            result = result.replace(field.value, field.masked)
        return result


# === Handler ===

class BlockHandler:
    """Block 处置：命中私密 → 抛 :class:`SensitiveBlockError`。

    例外通道：
      - ``QINGQIU_INCLUDE_PRIVATE=1[;ts=...]``：1h 内临时放行
      - ``QINGQIU_REDACT_ONLY=1``：跳过 block（让上层走 redact）
    """

    def __init__(self, detector: SensitiveDetector | None = None) -> None:
        self._detector = detector or SensitiveDetector()

    def check_text(self, text: str) -> None:
        if _include_private_enabled() or _redact_only_enabled():
            return
        result = self._detector.check_text(text)
        if result.has_private:
            sample = ", ".join(m.pattern for m in result.matches[:3])
            raise SensitiveBlockError(
                f"检测到私密信息 ({sample})",
                hint="如确需使用，请设置 QINGQIU_INCLUDE_PRIVATE=1 或 QINGQIU_REDACT_ONLY=1",
            )

    def check_file(self, path: Path) -> None:
        if _include_private_enabled() or _redact_only_enabled():
            return
        result = self._detector.check_file(path)
        if result.has_private:
            sample = ", ".join(m.pattern for m in result.matches[:3])
            raise SensitiveBlockError(
                f"文件 {path} 检测到私密信息 ({sample})",
                hint="如确需使用，请设置 QINGQIU_INCLUDE_PRIVATE=1 或 QINGQIU_REDACT_ONLY=1",
            )


class RedactHandler:
    """Redact 处置：命中私密 → 返回 masked 文本。"""

    def __init__(self, detector: SensitiveDetector | None = None) -> None:
        self._detector = detector or SensitiveDetector()

    def redact_text(self, text: str) -> str:
        return self._detector.redact_text(text)

    def redact_file(self, path: Path) -> str | None:
        """读取文件并 redact；文件不存在 / 不可读返回 ``None``"""
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeError):
            return None
        return self._detector.redact_text(text)

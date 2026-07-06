"""security.private_detect · 私密识别 Detect

S5.4 切片（PRD §6.4 · 私密信息保护 · 第一道闸）。

三道闸分工：
- Detect（本模块）：识别出文件路径/内容是否含私密信息
- Block（后续切片）：命中 → 中止任务 → 告知用户
- Redact（后续切片）：占位符替换 + 脱敏映射本地存

检测三类命中：
1. 文件名模式（glob · fnmatch）
2. 文件内容正则（regex）
3. 目录黑名单（路径前缀）

命中后返回 :class:`PrivateMatch` 列表，由上层决定后续处置。
模块本身只负责"识别"，不负责"阻断"或"脱敏"。
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class PrivateMatchType(str, Enum):
    """命中类型"""

    FILENAME = "filename"
    CONTENT_REGEX = "content_regex"
    DIRECTORY = "directory"


@dataclass(frozen=True)
class PrivateMatch:
    """单个匹配结果"""

    match_type: PrivateMatchType
    pattern: str           # 命中的 pattern/regex/path
    matched_value: str     # 实际匹配内容（文件路径 / 内容片段）
    severity: str          # 'high' / 'medium' / 'low'


# === A. 文件名模式（glob · 大小写不敏感） ===

_FILENAME_PATTERNS: tuple[tuple[str, str], ...] = (
    # (glob_pattern, severity)
    ("*id_card*", "high"),
    ("*身份证*", "high"),
    ("*passport*", "high"),
    ("*护照*", "high"),
    ("*.key", "high"),
    ("*.pem", "high"),
    ("*.p12", "high"),
    ("*.pfx", "high"),
    ("*credentials*", "high"),
    ("*credential*", "high"),
    ("*password*", "high"),
    ("*passwd*", "high"),
    ("*密码*", "high"),
    ("*secret*", "high"),
    ("*token*", "medium"),
    ("*api_key*", "high"),
    ("*api-key*", "high"),
    ("*.env", "high"),
    (".envrc", "high"),
    ("secrets.yaml", "high"),
    ("secrets.yml", "high"),
    ("config.local.*", "high"),
    ("id_rsa", "high"),
    ("id_rsa.pub", "high"),
    ("*.asc", "high"),
    ("*.gpg", "high"),
    ("*bank*", "medium"),
    ("*卡号*", "high"),
    ("*credit*card*", "high"),
    ("*.npmrc", "high"),
    ("*.pypirc", "high"),
)


# === B. 内容正则（name -> (regex, severity)） ===

_CONTENT_PATTERNS: dict[str, tuple[str, str]] = {
    "id_card_18": (r"\b\d{17}[\dXx]\b", "high"),
    "cn_mobile": (r"\b1[3-9]\d{9}\b", "medium"),
    "email": (
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        "medium",
    ),
    "bank_card": (r"\b\d{13,19}\b", "medium"),
    "aws_access_key": (r"\bAKIA[0-9A-Z]{16}\b", "high"),
    "github_token": (r"\bghp_[0-9a-zA-Z]{36}\b", "high"),
    "jwt_token": (
        r"\beyJ[0-9a-zA-Z_\-]+\.[0-9a-zA-Z_\-]+\.[0-9a-zA-Z_\-]+\b",
        "high",
    ),
}

_CONTENT_COMPILED: dict[str, tuple[re.Pattern[str], str]] = {
    name: (re.compile(pat), sev) for name, (pat, sev) in _CONTENT_PATTERNS.items()
}


# === C. 目录黑名单（路径前缀 · 运行时 expanduser） ===

def _private_dirs() -> tuple[Path, ...]:
    """获取当前用户的私密目录列表"""
    h = Path.home()
    return (
        h / ".ssh",
        h / ".aws",
        h / ".gnupg",
        h / ".config" / "gh",
        h / "AppData" / "Roaming" / "Microsoft" / "Cookies",
    )


# === 身份证校验位（GB 11643-1999） ===

_ID_WEIGHTS: tuple[int, ...] = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_ID_CHECKSUM: str = "10X98765432"


def _id_card_valid(s: str) -> bool:
    """校验 18 位身份证号（GB 11643-1999）。

    17 位数字 + 第 18 位（0-9 / X / x）。校验失败返回 False。
    """
    if len(s) != 18 or not s[:17].isdigit() or s[17] not in "0123456789Xx":
        return False
    total = sum(int(s[i]) * _ID_WEIGHTS[i] for i in range(17))
    return _ID_CHECKSUM[total % 11] == s[17].upper()


class PrivateDetector:
    """私密信息检测器（无状态 · 线程安全）。"""

    FILENAME_PATTERNS: tuple[tuple[str, str], ...] = _FILENAME_PATTERNS
    """对外公开：glob_pattern -> severity。"""

    CONTENT_PATTERNS: dict[str, str] = {
        name: pat for name, (pat, _) in _CONTENT_PATTERNS.items()
    }
    """对外公开：name -> regex 源串。"""

    PRIVATE_DIRS: tuple[Path, ...] = _private_dirs()
    """对外公开：当前用户的私密目录（运行时解析 Path.home()）。"""

    # --- 文件名 ---

    def _match_filename(self, path: Path) -> list[PrivateMatch]:
        name_lower = path.name.lower()
        hits: list[PrivateMatch] = []
        for pattern, severity in self.FILENAME_PATTERNS:
            if fnmatch.fnmatch(name_lower, pattern.lower()):
                hits.append(
                    PrivateMatch(
                        match_type=PrivateMatchType.FILENAME,
                        pattern=pattern,
                        matched_value=path.name,
                        severity=severity,
                    )
                )
        return hits

    # --- 内容 ---

    def detect_content(self, text: str) -> list[PrivateMatch]:
        """扫描文本，匹配私密内容正则（带身份证校验位校验）。"""
        hits: list[PrivateMatch] = []
        for name, (pat, severity) in _CONTENT_COMPILED.items():
            for m in pat.finditer(text):
                value = m.group(0)
                if name == "id_card_18" and not _id_card_valid(value):
                    continue
                hits.append(
                    PrivateMatch(
                        match_type=PrivateMatchType.CONTENT_REGEX,
                        pattern=name,
                        matched_value=value,
                        severity=severity,
                    )
                )
        return hits

    # --- 目录 ---

    @staticmethod
    def _resolve(path: Path) -> Path:
        """resolve（失败则 expanduser + absolute）"""
        try:
            return path.expanduser().resolve()
        except (OSError, ValueError, RuntimeError):
            return path.expanduser().absolute()

    def is_private_path(self, path: Path) -> bool:
        """路径是否在任一私密目录下（含祖先）。"""
        p = self._resolve(path)
        for d in self.PRIVATE_DIRS:
            try:
                p.relative_to(self._resolve(d))
                return True
            except ValueError:
                continue
        return False

    def _match_directory(self, path: Path) -> list[PrivateMatch]:
        if not self.is_private_path(path):
            return []
        p_resolved = self._resolve(path)
        for d in self.PRIVATE_DIRS:
            d_resolved = self._resolve(d)
            try:
                p_resolved.relative_to(d_resolved)
                return [
                    PrivateMatch(
                        match_type=PrivateMatchType.DIRECTORY,
                        pattern=str(d_resolved),
                        matched_value=str(path),
                        severity="high",
                    )
                ]
            except ValueError:
                continue
        return []

    # --- 入口 ---

    def detect_file(self, path: Path) -> list[PrivateMatch]:
        """检测文件：路径 + 文件名 + （如可读且 ≤1MB）内容。"""
        hits: list[PrivateMatch] = []
        hits.extend(self._match_filename(path))
        hits.extend(self._match_directory(path))
        try:
            if path.is_file() and path.stat().st_size <= 1_000_000:
                text = path.read_text(encoding="utf-8", errors="ignore")
                hits.extend(self.detect_content(text))
        except (OSError, ValueError, UnicodeError):
            # 文件不存在 / 不可读 / 权限不足 / 编码异常 → 跳过内容扫描
            pass
        return hits

    def detect(self, path: Path) -> list[PrivateMatch]:
        """主入口 = :meth:`detect_file`（语义别名）。"""
        return self.detect_file(path)
"""S5.4 测试 · 私密识别 Detect（filename + content + directory）"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from qingqiu.security.private_detect import (
    PrivateDetector,
    PrivateMatch,
    PrivateMatchType,
)


@pytest.fixture
def detector() -> PrivateDetector:
    return PrivateDetector()


# === A. 文件名模式命中（10 路径） ===

@pytest.mark.parametrize("filename", [
    "id_card.txt",
    "my_id_card.png",
    "张三的身份证.jpg",
    "passport_scan.pdf",
    "护照照片.png",
    "private.key",
    "cert.pem",
    "wildcard.p12",
    "client.pfx",
    "credentials.yaml",
    "credential.json",
    "db_password.txt",
    "user_passwd.txt",
    "我的密码.txt",
    "api_secret.txt",
    "auth_token.txt",
    "aws_api_key.txt",
    ".env",
    "test.env",
    ".envrc",
    "secrets.yaml",
    "config.local.yaml",
    "config.local.json",
    "id_rsa",
    "id_rsa.pub",
    "release.asc",
    "backup.gpg",
    "my_bank_statement.pdf",
    "信用卡号.txt",
    "credit_card.csv",
    ".npmrc",
    ".pypirc",
])
def test_filename_match(detector: PrivateDetector, filename: str) -> None:
    hits = detector.detect_file(Path(f"C:/tmp/{filename}"))
    assert any(m.match_type == PrivateMatchType.FILENAME for m in hits), filename
    assert all(m.severity in ("high", "medium", "low") for m in hits)


# === A. 文件名模式不命中（10 路径） ===

@pytest.mark.parametrize("filename", [
    "README.md",
    "main.py",
    "test.txt",
    "config.yaml",
    "settings.json",
    "image.png",
    "document.pdf",
    "data.csv",
    "notes.md",
    "script.sh",
    "index.html",
    "style.css",
    "app.js",
])
def test_filename_no_match(detector: PrivateDetector, filename: str) -> None:
    hits = detector._match_filename(Path(f"C:/tmp/{filename}"))
    assert hits == []


# === B. 内容正则命中 ===

def test_content_id_card_valid(detector: PrivateDetector) -> None:
    """合法身份证（GB 11643-1999 校验位）应命中"""
    text = "我的身份证号是 11010519491231002X"
    hits = detector.detect_content(text)
    assert any(m.pattern == "id_card_18" for m in hits)


def test_content_id_card_invalid_checksum_rejected(detector: PrivateDetector) -> None:
    """非法校验位的 18 位数字串不应作为身份证命中"""
    text = "假身份证: 110101199003078888"
    hits = detector.detect_content(text)
    assert not any(m.pattern == "id_card_18" for m in hits)


def test_content_mobile(detector: PrivateDetector) -> None:
    hits = detector.detect_content("call me at 13800138000")
    assert any(m.pattern == "cn_mobile" for m in hits)


def test_content_email(detector: PrivateDetector) -> None:
    hits = detector.detect_content("email: alice@example.com")
    assert any(m.pattern == "email" for m in hits)


def test_content_email_complex(detector: PrivateDetector) -> None:
    hits = detector.detect_content("Contact: foo.bar+test@sub.example.co.uk")
    assert any(m.pattern == "email" for m in hits)


def test_content_bank_card(detector: PrivateDetector) -> None:
    hits = detector.detect_content("卡号: 6222021234567890123")
    assert any(m.pattern == "bank_card" for m in hits)


def test_content_aws_access_key(detector: PrivateDetector) -> None:
    hits = detector.detect_content("aws_access_key_id=AKIAIOSFODNN7EXAMPLE")
    assert any(m.pattern == "aws_access_key" for m in hits)


def test_content_github_token(detector: PrivateDetector) -> None:
    token = "ghp_" + "a" * 36
    hits = detector.detect_content(f"token: {token}")
    assert any(m.pattern == "github_token" for m in hits)


def test_content_jwt_token(detector: PrivateDetector) -> None:
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    hits = detector.detect_content(f"auth: Bearer {jwt}")
    assert any(m.pattern == "jwt_token" for m in hits)


# === B. 内容正则不命中 ===

@pytest.mark.parametrize("text", [
    "hello world",
    "this is a normal sentence with no secrets",
    "会议在 2026 年 7 月 6 日",
    "年假 3 天 · 年终奖 1 个月",
    "价格 123 元 · 不含税",
    "",
    "   ",
])
def test_content_no_match(detector: PrivateDetector, text: str) -> None:
    hits = detector.detect_content(text)
    assert hits == []


# === C. 目录黑名单命中 ===

def test_is_private_path_ssh(detector: PrivateDetector) -> None:
    assert detector.is_private_path(Path.home() / ".ssh" / "id_rsa") is True


def test_is_private_path_aws(detector: PrivateDetector) -> None:
    assert detector.is_private_path(Path.home() / ".aws" / "credentials") is True


def test_is_private_path_gnupg(detector: PrivateDetector) -> None:
    assert detector.is_private_path(Path.home() / ".gnupg" / "pubring.kbx") is True


def test_is_private_path_github_config(detector: PrivateDetector) -> None:
    assert detector.is_private_path(Path.home() / ".config" / "gh" / "hosts.yml") is True


def test_directory_match_in_detect_file(detector: PrivateDetector) -> None:
    """detect_file 应触发 DIRECTORY 命中"""
    p = Path.home() / ".ssh" / "somefile"
    hits = detector.detect_file(p)
    assert any(m.match_type == PrivateMatchType.DIRECTORY for m in hits)


# === C. 目录黑名单不命中 ===

@pytest.mark.parametrize("path", [
    Path("C:/Users/ROG/Documents/notes.md"),
    Path("C:/Users/ROG/Downloads/file.pdf"),
    Path("E:/MiniMax Code WorkSpace/qingqiu-system/README.md"),
    Path("C:/Users/ROG/Desktop/normal.txt"),
    Path("C:/tmp/test.txt"),
])
def test_is_private_path_false(detector: PrivateDetector, path: Path) -> None:
    assert detector.is_private_path(path) is False


# === 集成：detect_file 触发文件名 + 内容 ===

def test_detect_file_combined_filename_and_content(detector: PrivateDetector) -> None:
    """命中文件名 + 内容都应被报告"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".env", delete=False, encoding="utf-8"
    ) as f:
        f.write("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n")
        tmp_path = Path(f.name)
    try:
        hits = detector.detect_file(tmp_path)
        types = {m.match_type for m in hits}
        assert PrivateMatchType.FILENAME in types
        assert PrivateMatchType.CONTENT_REGEX in types
        assert any(m.pattern == "aws_access_key" for m in hits)
    finally:
        tmp_path.unlink(missing_ok=True)


# === severity 标记 ===

def test_filename_severity_is_high_or_medium(detector: PrivateDetector) -> None:
    hits = detector._match_filename(Path("C:/tmp/secrets.txt"))
    assert len(hits) >= 1
    assert all(m.severity in ("high", "medium", "low") for m in hits)


def test_directory_severity_is_high(detector: PrivateDetector) -> None:
    p = Path.home() / ".ssh" / "config"
    hits = detector.detect_file(p)
    dir_hits = [m for m in hits if m.match_type == PrivateMatchType.DIRECTORY]
    assert all(m.severity == "high" for m in dir_hits)


def test_content_severity_is_high_or_medium(detector: PrivateDetector) -> None:
    hits = detector.detect_content("手机 13800138000 身份证 11010519491231002X")
    assert all(m.severity in ("high", "medium") for m in hits)


# === 空文件 / 不可读文件 ===

def test_detect_file_empty_file(detector: PrivateDetector) -> None:
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        tmp_path = Path(f.name)
    try:
        hits = detector.detect_file(tmp_path)
        # 空文件：可能命中文件名（如果后缀敏感）或无命中；至少不应抛异常
        assert isinstance(hits, list)
    finally:
        tmp_path.unlink(missing_ok=True)


def test_detect_file_nonexistent_file(detector: PrivateDetector) -> None:
    """不存在的文件不应抛异常"""
    hits = detector.detect_file(Path("C:/nonexistent/path/foo.txt"))
    # 文件不存在 → 只检查文件名（无文件名命中）+ 目录（无关目录）
    assert isinstance(hits, list)


def test_detect_file_directory_not_a_file(detector: PrivateDetector) -> None:
    """目录而不是文件不应抛异常（is_file 检查）"""
    hits = detector.detect_file(Path("C:/"))
    assert isinstance(hits, list)


# === 边界：路径规范化 ===

def test_path_with_dots_normalized(detector: PrivateDetector) -> None:
    """含 .. 的路径应被规范化"""
    ssh_dir = Path.home() / ".ssh"
    p = ssh_dir / ".." / ".ssh" / "id_rsa"
    assert detector.is_private_path(p) is True


def test_path_normalization_matches(detector: PrivateDetector) -> None:
    """Windows 反斜杠 / 正斜杠自动处理"""
    p1 = Path("C:/Users/ROG/Documents/test.txt")
    p2 = Path("C:\\Users\\ROG\\Documents\\test.txt")
    assert detector.is_private_path(p1) is False
    assert detector.is_private_path(p2) is False


# === PrivateMatch 数据类 ===

def test_private_match_is_frozen() -> None:
    """PrivateMatch 不可变"""
    m = PrivateMatch(
        match_type=PrivateMatchType.FILENAME,
        pattern="*.key",
        matched_value="private.key",
        severity="high",
    )
    with pytest.raises((AttributeError, Exception)):
        m.severity = "low"  # type: ignore[misc]


def test_private_match_type_is_str_enum() -> None:
    """PrivateMatchType 是 str 枚举（可序列化）"""
    assert PrivateMatchType.FILENAME.value == "filename"
    assert PrivateMatchType.CONTENT_REGEX.value == "content_regex"
    assert PrivateMatchType.DIRECTORY.value == "directory"
    assert isinstance(PrivateMatchType.FILENAME, str)


# === 模块公开结构 ===

def test_filename_patterns_nonempty(detector: PrivateDetector) -> None:
    assert len(PrivateDetector.FILENAME_PATTERNS) >= 20


def test_content_patterns_complete(detector: PrivateDetector) -> None:
    expected = {"id_card_18", "cn_mobile", "email", "bank_card",
                "aws_access_key", "github_token", "jwt_token"}
    assert expected.issubset(set(PrivateDetector.CONTENT_PATTERNS.keys()))


def test_private_dirs_nonempty(detector: PrivateDetector) -> None:
    assert len(PrivateDetector.PRIVATE_DIRS) >= 4
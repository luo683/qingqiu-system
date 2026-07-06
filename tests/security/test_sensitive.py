"""S5.5 测试 · 私密处理 Block + Redact (脱敏映射 + 例外通道)

Builds on S5.4 PrivateDetector (filename + content + directory detection).
S5.5 adds:
- PrivateDetectResult aggregate
- SensitiveField (type + value + masked)
- SensitiveDetector.check_text / check_file / classify / redact_text
- REDACT_PATTERNS dict
- BlockHandler (SensitiveBlockError on hit) + RedactHandler
- include_private / redact_only env-var exception channels (1h TTL)
- Mixed Chinese + English recognition
"""
from __future__ import annotations

from pathlib import Path

import pytest

from qingqiu.security.private_detect import (
    PrivateMatch,
    PrivateMatchType,
)
from qingqiu.security.sensitive import (
    BlockHandler,
    PrivateDetectResult,
    REDACT_PATTERNS,
    SENSITIVE_TYPES,
    SensitiveBlockError,
    SensitiveDetector,
    SensitiveField,
    SensitiveType,
    RedactHandler,
)


# === Fixtures ===

@pytest.fixture
def detector() -> SensitiveDetector:
    return SensitiveDetector()


@pytest.fixture
def block_handler() -> BlockHandler:
    return BlockHandler()


@pytest.fixture
def redact_handler(detector: SensitiveDetector) -> RedactHandler:
    return RedactHandler(detector)


def _make_match(pattern: str, value: str, severity: str = "medium") -> PrivateMatch:
    return PrivateMatch(
        match_type=PrivateMatchType.CONTENT_REGEX,
        pattern=pattern,
        matched_value=value,
        severity=severity,
    )


# === PrivateDetectResult ===

def test_private_detect_result_has_private_true() -> None:
    r = PrivateDetectResult(matches=[_make_match("email", "a@b.com")])
    assert r.has_private is True
    assert len(r.matches) == 1


def test_private_detect_result_has_private_false() -> None:
    r = PrivateDetectResult(matches=[])
    assert r.has_private is False


def test_private_detect_result_iterable() -> None:
    """PrivateDetectResult 应可迭代（兼容 matches 列表语义）"""
    r = PrivateDetectResult(matches=[_make_match("email", "a@b.com")])
    items = list(r)
    assert len(items) == 1


# === SENSITIVE_TYPES 枚举 ===

def test_sensitive_types_complete() -> None:
    expected = {"id_card", "phone", "email", "card", "aws_key", "github_token", "jwt"}
    actual = {t.value for t in SENSITIVE_TYPES}
    assert expected.issubset(actual)


def test_sensitive_type_is_str_enum() -> None:
    assert SensitiveType.EMAIL.value == "email"
    assert SensitiveType.ID_CARD.value == "id_card"
    assert isinstance(SensitiveType.EMAIL, str)


def test_sensitive_type_count() -> None:
    assert len(SENSITIVE_TYPES) >= 7


# === SensitiveField dataclass ===

def test_sensitive_field_basic() -> None:
    f = SensitiveField(type=SensitiveType.EMAIL, value="a@b.com", masked="a***@b.com")
    assert f.type is SensitiveType.EMAIL
    assert f.value == "a@b.com"
    assert f.masked == "a***@b.com"


def test_sensitive_field_is_frozen() -> None:
    f = SensitiveField(type=SensitiveType.EMAIL, value="a@b.com", masked="a***@b.com")
    with pytest.raises((AttributeError, Exception)):
        f.value = "x"  # type: ignore[misc]


# === SensitiveDetector.check_text ===

def test_check_text_id_card_valid(detector: SensitiveDetector) -> None:
    r = detector.check_text("身份证 11010519491231002X")
    assert r.has_private
    assert any(m.pattern == "id_card_18" for m in r.matches)


def test_check_text_phone(detector: SensitiveDetector) -> None:
    r = detector.check_text("call 13800138000")
    assert r.has_private
    assert any(m.pattern == "cn_mobile" for m in r.matches)


def test_check_text_email(detector: SensitiveDetector) -> None:
    r = detector.check_text("Email: rog@qq.com")
    assert r.has_private
    assert any(m.pattern == "email" for m in r.matches)


def test_check_text_email_complex(detector: SensitiveDetector) -> None:
    r = detector.check_text("foo.bar+test@sub.example.co.uk")
    assert r.has_private


def test_check_text_no_match(detector: SensitiveDetector) -> None:
    r = detector.check_text("hello world 没有敏感信息")
    assert not r.has_private
    assert r.matches == []


@pytest.mark.parametrize("text", [
    "张三的邮箱是 zhang.san@example.com",
    "李四 电话 13800138000",
    "邮箱 alice@qq.com 电话 13900139000 身份证 11010519491231002X",
    "Meeting at 2026-07-06 with email contact@anthropic.com",
])
def test_check_text_chinese_mixed(detector: SensitiveDetector, text: str) -> None:
    """中英文混合识别：周围有中文 / 英文上下文"""
    r = detector.check_text(text)
    assert r.has_private


def test_check_text_aws_key(detector: SensitiveDetector) -> None:
    r = detector.check_text("AKIAIOSFODNN7EXAMPLE")
    assert r.has_private


def test_check_text_github_token(detector: SensitiveDetector) -> None:
    r = detector.check_text("ghp_" + "a" * 36)
    assert r.has_private


def test_check_text_jwt(detector: SensitiveDetector) -> None:
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    r = detector.check_text(jwt)
    assert r.has_private


# === SensitiveDetector.check_file ===

def test_check_file_with_id_card(tmp_path: Path, detector: SensitiveDetector) -> None:
    p = tmp_path / "notes.txt"
    p.write_text("ID 11010519491231002X", encoding="utf-8")
    r = detector.check_file(p)
    assert r.has_private


def test_check_file_clean(tmp_path: Path, detector: SensitiveDetector) -> None:
    p = tmp_path / "notes.txt"
    p.write_text("hello world", encoding="utf-8")
    r = detector.check_file(p)
    assert not r.has_private


def test_check_file_sensitive_filename(tmp_path: Path, detector: SensitiveDetector) -> None:
    """文件名命中（如 id_card.txt）应被 check_file 捕获"""
    p = tmp_path / "my_id_card.txt"
    p.write_text("clean content", encoding="utf-8")
    r = detector.check_file(p)
    assert r.has_private
    assert any(m.match_type == PrivateMatchType.FILENAME for m in r.matches)


# === SensitiveDetector.classify ===

def test_classify_id_card(detector: SensitiveDetector) -> None:
    fields = detector.classify("身份证 11010519491231002X")
    assert any(f.type == SensitiveType.ID_CARD for f in fields)
    cards = [f for f in fields if f.type == SensitiveType.ID_CARD]
    assert cards[0].value == "11010519491231002X"
    assert cards[0].masked == "110105****002X"


def test_classify_phone(detector: SensitiveDetector) -> None:
    fields = detector.classify("13800138000")
    phones = [f for f in fields if f.type == SensitiveType.PHONE]
    assert phones
    assert phones[0].value == "13800138000"
    assert phones[0].masked == "138****8000"


def test_classify_email(detector: SensitiveDetector) -> None:
    fields = detector.classify("rog@qq.com")
    emails = [f for f in fields if f.type == SensitiveType.EMAIL]
    assert emails
    assert emails[0].value == "rog@qq.com"
    assert emails[0].masked == "rog***@qq.com"


def test_classify_bank_card(detector: SensitiveDetector) -> None:
    fields = detector.classify("卡号 6222021234567890123")
    cards = [f for f in fields if f.type == SensitiveType.CARD]
    assert cards
    assert cards[0].masked.endswith("0123")
    assert "****" in cards[0].masked


def test_classify_chinese_mixed(detector: SensitiveDetector) -> None:
    fields = detector.classify("张三 13800138000 邮箱 zhang@qq.com")
    types = {f.type for f in fields}
    assert SensitiveType.PHONE in types
    assert SensitiveType.EMAIL in types


def test_classify_empty(detector: SensitiveDetector) -> None:
    assert detector.classify("") == []
    assert detector.classify("hello world 没有敏感信息") == []


def test_classify_id_card_priority_over_bank_card(detector: SensitiveDetector) -> None:
    """合法的 18 位身份证应优先识别为 ID_CARD（不被 bank_card 抢去）"""
    fields = detector.classify("11010519491231002X")
    types = {f.type for f in fields}
    assert SensitiveType.ID_CARD in types


def test_classify_invalid_id_card_falls_to_bank_card(detector: SensitiveDetector) -> None:
    """非法校验位的 18 位数字串应作为 bank_card"""
    fields = detector.classify("110101199003078888")
    types = {f.type for f in fields}
    assert SensitiveType.CARD in types
    assert SensitiveType.ID_CARD not in types


# === SensitiveDetector.redact_text ===

def test_redact_text_phone(detector: SensitiveDetector) -> None:
    r = detector.redact_text("call 13800138000")
    assert "138****8000" in r
    assert "13800138000" not in r


def test_redact_text_email(detector: SensitiveDetector) -> None:
    r = detector.redact_text("Email: rog@qq.com")
    assert "rog***@qq.com" in r
    assert "rog@qq.com" not in r


def test_redact_text_id_card(detector: SensitiveDetector) -> None:
    r = detector.redact_text("身份证 11010519491231002X")
    assert "110105****002X" in r


def test_redact_text_bank_card(detector: SensitiveDetector) -> None:
    r = detector.redact_text("卡 6222021234567890123")
    assert "****-****-****-0123" in r
    assert "6222021234567890123" not in r


def test_redact_text_no_sensitive(detector: SensitiveDetector) -> None:
    assert detector.redact_text("hello world") == "hello world"


def test_redact_text_chinese_around_sensitive(detector: SensitiveDetector) -> None:
    r = detector.redact_text("张三的电话是 13800138000，请联系")
    assert "138****8000" in r
    assert "张三" in r
    assert "请联系" in r


def test_redact_text_multiple_sensitive(detector: SensitiveDetector) -> None:
    r = detector.redact_text("phone 13800138000 email rog@qq.com")
    assert "138****8000" in r
    assert "rog***@qq.com" in r


def test_redact_text_empty(detector: SensitiveDetector) -> None:
    assert detector.redact_text("") == ""


# === REDACT_PATTERNS dict ===

def test_redact_patterns_keys() -> None:
    expected = {SensitiveType.ID_CARD, SensitiveType.PHONE, SensitiveType.EMAIL, SensitiveType.CARD}
    actual = set(REDACT_PATTERNS.keys())
    assert expected.issubset(actual)


def test_redact_patterns_callable() -> None:
    """每个 REDACT_PATTERNS value 都应是可调用的"""
    for sensitive_type, fn in REDACT_PATTERNS.items():
        assert callable(fn)


def test_redact_pattern_id_card_format() -> None:
    """id_card: 110101****1234 格式"""
    fn = REDACT_PATTERNS[SensitiveType.ID_CARD]
    assert fn("11010519491231002X") == "110105****002X"
    assert fn("110101199003078812") == "110101****8812"


def test_redact_pattern_phone_format() -> None:
    """phone: 138****5678 格式"""
    fn = REDACT_PATTERNS[SensitiveType.PHONE]
    assert fn("13800138000") == "138****8000"
    assert fn("13912345678") == "139****5678"


def test_redact_pattern_email_format() -> None:
    """email: a***@x.com 格式（保留 local + *** + @ + domain）"""
    fn = REDACT_PATTERNS[SensitiveType.EMAIL]
    assert fn("a@b.com") == "a***@b.com"
    assert fn("rog@qq.com") == "rog***@qq.com"


def test_redact_pattern_card_format() -> None:
    """card: ****-****-****-1234 格式"""
    fn = REDACT_PATTERNS[SensitiveType.CARD]
    assert fn("6222021234567890123") == "****-****-****-0123"
    assert fn("1234567890123") == "****-****-****-0123"


# === BlockHandler ===

def test_block_handler_clean_text(block_handler: BlockHandler, monkeypatch) -> None:
    monkeypatch.delenv("QINGQIU_INCLUDE_PRIVATE", raising=False)
    monkeypatch.delenv("QINGQIU_REDACT_ONLY", raising=False)
    block_handler.check_text("hello world")  # 不抛


def test_block_handler_sensitive_raises(
    block_handler: BlockHandler, monkeypatch
) -> None:
    monkeypatch.delenv("QINGQIU_INCLUDE_PRIVATE", raising=False)
    monkeypatch.delenv("QINGQIU_REDACT_ONLY", raising=False)
    with pytest.raises(SensitiveBlockError):
        block_handler.check_text("身份证 11010519491231002X")


def test_block_handler_sensitive_block_error_is_not_found_error() -> None:
    """SensitiveBlockError 必须是 NotFoundError 子类（code=1）"""
    from qingqiu.cli.errors import NotFoundError

    assert issubclass(SensitiveBlockError, NotFoundError)
    err = SensitiveBlockError("test", hint="fix it")
    assert err.code == 1
    assert "test" in str(err)
    assert "fix it" in str(err)


def test_block_handler_file_raises(
    block_handler: BlockHandler, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("QINGQIU_INCLUDE_PRIVATE", raising=False)
    monkeypatch.delenv("QINGQIU_REDACT_ONLY", raising=False)
    p = tmp_path / "id_card.txt"
    p.write_text("clean content", encoding="utf-8")
    with pytest.raises(SensitiveBlockError):
        block_handler.check_file(p)


# === include_private 例外通道 ===

def test_block_handler_include_private_bypasses_block(
    block_handler: BlockHandler, monkeypatch
) -> None:
    """QINGQIU_INCLUDE_PRIVATE=1 应临时跳过 block"""
    monkeypatch.setenv("QINGQIU_INCLUDE_PRIVATE", "1")
    block_handler.check_text("身份证 11010519491231002X")  # 不抛


def test_block_handler_no_include_private_raises(
    block_handler: BlockHandler, monkeypatch
) -> None:
    monkeypatch.delenv("QINGQIU_INCLUDE_PRIVATE", raising=False)
    with pytest.raises(SensitiveBlockError):
        block_handler.check_text("身份证 11010519491231002X")


def test_block_handler_include_private_ttl_expired(
    block_handler: BlockHandler, monkeypatch
) -> None:
    """QINGQIU_INCLUDE_PRIVATE=1;ts=<过期> 应禁用"""
    monkeypatch.setenv("QINGQIU_INCLUDE_PRIVATE", "1;ts=2020-01-01T00:00:00")
    with pytest.raises(SensitiveBlockError):
        block_handler.check_text("身份证 11010519491231002X")


def test_block_handler_include_private_ttl_fresh(
    block_handler: BlockHandler, monkeypatch
) -> None:
    """QINGQIU_INCLUDE_PRIVATE=1;ts=<fresh> 应启用"""
    from datetime import datetime, timedelta

    fresh = (datetime.now() - timedelta(minutes=5)).isoformat()
    monkeypatch.setenv("QINGQIU_INCLUDE_PRIVATE", f"1;ts={fresh}")
    block_handler.check_text("身份证 11010519491231002X")  # 不抛


def test_block_handler_include_private_ttl_invalid(
    block_handler: BlockHandler, monkeypatch
) -> None:
    """无效的 ts 格式应保守视为不启用"""
    monkeypatch.setenv("QINGQIU_INCLUDE_PRIVATE", "1;ts=not-a-date")
    with pytest.raises(SensitiveBlockError):
        block_handler.check_text("身份证 11010519491231002X")


# === redact_only 例外通道 ===

def test_block_handler_redact_only_bypasses_block(
    block_handler: BlockHandler, monkeypatch
) -> None:
    """QINGQIU_REDACT_ONLY=1 应跳过 block（让上层处理 redact）"""
    monkeypatch.setenv("QINGQIU_REDACT_ONLY", "1")
    block_handler.check_text("身份证 11010519491231002X")  # 不抛


def test_block_handler_no_redact_only_raises(
    block_handler: BlockHandler, monkeypatch
) -> None:
    monkeypatch.delenv("QINGQIU_REDACT_ONLY", raising=False)
    with pytest.raises(SensitiveBlockError):
        block_handler.check_text("身份证 11010519491231002X")


# === RedactHandler ===

def test_redact_handler_redact_text(redact_handler: RedactHandler) -> None:
    r = redact_handler.redact_text("phone 13800138000")
    assert "138****8000" in r


def test_redact_handler_redact_file(
    redact_handler: RedactHandler, tmp_path: Path
) -> None:
    p = tmp_path / "test.txt"
    p.write_text("Email: alice@example.com", encoding="utf-8")
    r = redact_handler.redact_file(p)
    assert r is not None
    assert "alice***@example.com" in r
    assert "alice@example.com" not in r


def test_redact_handler_redact_file_missing(
    redact_handler: RedactHandler, tmp_path: Path
) -> None:
    r = redact_handler.redact_file(tmp_path / "nonexistent.txt")
    assert r is None


def test_redact_handler_redact_file_preserves_text(
    redact_handler: RedactHandler, tmp_path: Path
) -> None:
    """redact_file 应保留非敏感上下文"""
    p = tmp_path / "mixed.txt"
    p.write_text(
        "张三 13800138000 邮箱 alice@example.com",
        encoding="utf-8",
    )
    r = redact_handler.redact_file(p)
    assert r is not None
    assert "张三" in r
    assert "138****8000" in r
    assert "alice***@example.com" in r

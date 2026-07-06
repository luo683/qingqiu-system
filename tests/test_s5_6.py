"""test_s5_6.py · S5.6 三例外通道完整测试"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta

import pytest

from qingqiu.security.sensitive import (
    _include_private_enabled,
    _redact_only_enabled,
    _private_send_enabled,
    _parse_ttl,
    get_exception_channel,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """每个 test 前清空所有 QINGQIU 例外 env vars"""
    for key in ["QINGQIU_INCLUDE_PRIVATE", "QINGQIU_REDACT_ONLY", "QINGQIU_PRIVATE_SEND"]:
        monkeypatch.delenv(key, raising=False)
    yield


def test_no_exception_by_default():
    assert get_exception_channel() == "none"


def test_redact_only():
    os.environ["QINGQIU_REDACT_ONLY"] = "1"
    assert get_exception_channel() == "redact"
    assert _redact_only_enabled() is True


def test_include_private():
    os.environ["QINGQIU_INCLUDE_PRIVATE"] = "1"
    assert get_exception_channel() == "include"
    assert _include_private_enabled() is True


def test_private_send():
    os.environ["QINGQIU_PRIVATE_SEND"] = "1"
    assert get_exception_channel() == "private_send"
    assert _private_send_enabled() is True


def test_priority_private_send_beats_others():
    os.environ["QINGQIU_PRIVATE_SEND"] = "1"
    os.environ["QINGQIU_INCLUDE_PRIVATE"] = "1"
    os.environ["QINGQIU_REDACT_ONLY"] = "1"
    assert get_exception_channel() == "private_send"


def test_priority_include_beats_redact():
    os.environ["QINGQIU_INCLUDE_PRIVATE"] = "1"
    os.environ["QINGQIU_REDACT_ONLY"] = "1"
    assert get_exception_channel() == "include"


def test_ttl_expired():
    """1h 前的时间戳 → 应失效"""
    old_ts = (datetime.now() - timedelta(hours=2)).isoformat()
    os.environ["QINGQIU_INCLUDE_PRIVATE"] = f"1;ts={old_ts}"
    assert _include_private_enabled() is False


def test_ttl_fresh():
    """10 分钟前的时间戳 → 仍有效"""
    recent_ts = (datetime.now() - timedelta(minutes=10)).isoformat()
    os.environ["QINGQIU_INCLUDE_PRIVATE"] = f"1;ts={recent_ts}"
    assert _include_private_enabled() is True


def test_ttl_invalid_ts():
    """时间戳格式错误 → 视为无效"""
    os.environ["QINGQIU_INCLUDE_PRIVATE"] = "1;ts=not-a-date"
    assert _include_private_enabled() is False


def test_disabled_value_0():
    os.environ["QINGQIU_INCLUDE_PRIVATE"] = "0"
    assert _include_private_enabled() is False
    assert get_exception_channel() == "none"


def test_parse_ttl_helper():
    """TTL helper 单元测试"""
    assert _parse_ttl("1", timedelta(hours=1)) is True
    assert _parse_ttl("0", timedelta(hours=1)) is False
    assert _parse_ttl("", timedelta(hours=1)) is False
    assert _parse_ttl("1;ts=invalid", timedelta(hours=1)) is False
    assert _parse_ttl("1;foo=bar", timedelta(hours=1)) is True  # foo=bar 被忽略
    # 实际行为：遇到 invalid ts 立即 fail（最严格）
    assert _parse_ttl("1;ts=invalid;ts=2024-01-01T00:00:00", timedelta(hours=1)) is False


def test_three_channels_independent():
    """三档互不干扰"""
    os.environ["QINGQIU_REDACT_ONLY"] = "1"
    assert _include_private_enabled() is False
    assert _private_send_enabled() is False
    assert get_exception_channel() == "redact"

    del os.environ["QINGQIU_REDACT_ONLY"]
    os.environ["QINGQIU_INCLUDE_PRIVATE"] = "1"
    assert _redact_only_enabled() is False
    assert _private_send_enabled() is False
    assert get_exception_channel() == "include"
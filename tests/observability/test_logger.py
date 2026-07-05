"""日志系统测试 · S1.4"""

import logging as stdlib_logging
import os
from pathlib import Path

import pytest
from loguru import logger

from qingqiu.observability.logger import get_logger, setup_logging


def test_setup_logging_creates_dir(tmp_path):
    """setup_logging 自动建日志目录"""
    log_dir = tmp_path / "logs"
    assert not log_dir.exists()
    setup_logging(log_dir=log_dir, enable_console=False)
    assert log_dir.exists()


def test_setup_logging_writes_to_file(tmp_path):
    """setup_logging 后 logger.info 应该写到文件"""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir=log_dir, level="INFO", enable_console=False)

    logger.info("test message 12345")
    logger.info("another message")

    # loguru 是异步写入（enqueue=True），需要等
    logger.complete()

    log_file = log_dir / "qingqiu.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "test message 12345" in content
    assert "another message" in content


def test_setup_logging_separate_error_log(tmp_path):
    """ERROR 级别单独写 qingqiu.error.log"""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir=log_dir, level="DEBUG", enable_console=False)

    logger.debug("debug msg")
    logger.info("info msg")
    logger.error("error msg 999")
    logger.complete()

    main_log = log_dir / "qingqiu.log"
    error_log = log_dir / "qingqiu.error.log"

    assert "debug msg" in main_log.read_text(encoding="utf-8")
    assert "info msg" in main_log.read_text(encoding="utf-8")
    assert "error msg 999" in error_log.read_text(encoding="utf-8")
    # error log 不应该有 debug/info
    error_content = error_log.read_text(encoding="utf-8")
    assert "debug msg" not in error_content
    assert "info msg" not in error_content


def test_get_logger_binds_name():
    """get_logger 绑定名字"""
    setup_logging(log_dir=Path("/tmp"), enable_console=False)
    log = get_logger("test_module")
    # 不应该抛异常
    log.info("test")
    logger.complete()


def test_loguru_remove_default_handler():
    """setup_logging 应该移除 loguru 默认 handler（避免重复输出）"""
    import loguru
    initial_handlers = len(loguru.logger._core.handlers)
    setup_logging(log_dir=Path("/tmp"), enable_console=True)
    # setup 后 handler 数应该是 3（stderr + 2 文件）
    after_handlers = len(loguru.logger._core.handlers)
    assert after_handlers == 3


def test_loguru_level_filtering(tmp_path):
    """DEBUG 级别应该记录 DEBUG；INFO 级别不应该"""
    log_dir = tmp_path / "logs"

    # 先 INFO 级别
    setup_logging(log_dir=log_dir, level="INFO", enable_console=False)
    logger.debug("debug-only-message")
    logger.info("info-only-message")
    logger.complete()

    content = (log_dir / "qingqiu.log").read_text(encoding="utf-8")
    assert "info-only-message" in content
    assert "debug-only-message" not in content
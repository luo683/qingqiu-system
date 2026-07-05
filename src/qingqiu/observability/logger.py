"""日志系统（loguru + 滚动）"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logging(
    log_dir: Path | None = None,
    level: str = "INFO",
    max_bytes: int = 100 * 1024 * 1024,
    backup_days: int = 7,
    enable_console: bool = True,
) -> None:
    """初始化清秋日志系统

    Args:
        log_dir: 日志目录（默认 ~/.qingqiu/logs/）
        level: 日志级别（DEBUG / INFO / WARNING / ERROR）
        max_bytes: 单文件最大字节（超过滚动）
        backup_days: 保留天数
        enable_console: 是否输出到 stderr
    """
    if log_dir is None:
        log_dir = Path.home() / ".qingqiu" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    # 移除 loguru 默认 handler（避免重复）
    logger.remove()

    # 控制台 handler（简洁版 · 终端友好）
    if enable_console:
        logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:HH:MM:SS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=True,
        )

    # 文件 handler（详细版 · 含异常堆栈 + rotation）
    logger.add(
        log_dir / "qingqiu.log",
        level=level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        rotation=max_bytes,  # 字节数
        retention=f"{backup_days} days",
        encoding="utf-8",
        enqueue=True,  # 多进程安全（写入通过队列）
        backtrace=True,  # 异常链
        diagnose=True,  # 异常诊断（包含变量值，**不要在生产环境开**）
    )

    # 单独的错误日志（方便定位）
    logger.add(
        log_dir / "qingqiu.error.log",
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}\n{exception}"
        ),
        rotation=max_bytes,
        retention=f"{backup_days} days",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    logger.info(f"[logging] initialized: level={level}, log_dir={log_dir}, "
                f"max_bytes={max_bytes}, backup_days={backup_days}")


def get_logger(name: str | None = None):
    """获取绑定名字的 logger

    Args:
        name: 模块名（通常用 __name__）
    """
    if name:
        return logger.bind(module=name)
    return logger
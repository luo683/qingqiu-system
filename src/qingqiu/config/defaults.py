"""清秋默认配置路径 + 默认实例工厂"""

from __future__ import annotations

from pathlib import Path

from qingqiu.config.schema import Config, PersonalityConfig, SecurityConfig


def get_default_config_path() -> Path:
    """默认配置文件位置：~/.qingqiu/config.yaml"""
    return Path.home() / ".qingqiu" / "config.yaml"


def get_user_memory_path() -> Path:
    """默认用户记忆位置：~/.qingqiu/memory/user.md"""
    return Path.home() / ".qingqiu" / "memory" / "user.md"


def get_project_memory_dir() -> Path:
    """默认项目记忆目录：~/.qingqiu/memory/projects/"""
    return Path.home() / ".qingqiu" / "memory" / "projects"


def get_default_config() -> Config:
    """构建默认 Config 对象（含安全白名单默认值）

    注意：安全白名单默认值来自 PRD §10.1（4 个目录）。
    """
    return Config(
        security=SecurityConfig(
            whitelist_dirs=[
                r"E:\MiniMax Code WorkSpace",
                r"C:\Users\ROG\Downloads",
                r"C:\Users\ROG\Desktop",
                r"C:\Users\ROG\Documents",
            ],
        ),
        personality=PersonalityConfig(
            name="清秋",
        ),
    )
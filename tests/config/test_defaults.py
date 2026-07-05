"""defaults.py 测试 · 默认路径 + 默认实例"""

from pathlib import Path

from qingqiu.config.defaults import (
    get_default_config,
    get_default_config_path,
    get_project_memory_dir,
    get_user_memory_path,
)
from qingqiu.config.schema import Config, SecurityConfig


def test_default_config_path_is_under_home():
    p = get_default_config_path()
    assert p.parent.parent == Path.home()
    assert p.name == "config.yaml"


def test_user_memory_path():
    p = get_user_memory_path()
    assert p.name == "user.md"
    assert "memory" in str(p)


def test_project_memory_dir():
    p = get_project_memory_dir()
    assert p.name == "projects"


def test_default_config_has_security_whitelist():
    """PRD §10.1 规定的 4 目录白名单"""
    cfg = get_default_config()
    assert len(cfg.security.whitelist_dirs) == 4
    assert r"E:\MiniMax Code WorkSpace" in cfg.security.whitelist_dirs
    assert r"C:\Users\ROG\Downloads" in cfg.security.whitelist_dirs
    assert r"C:\Users\ROG\Desktop" in cfg.security.whitelist_dirs
    assert r"C:\Users\ROG\Documents" in cfg.security.whitelist_dirs


def test_default_config_personality_name():
    cfg = get_default_config()
    assert cfg.personality.name == "清秋"


def test_default_config_confirm_writes_enabled():
    """P5 默认开启：每次写入前询问"""
    cfg = get_default_config()
    assert cfg.security.confirm_writes is True


def test_default_config_auto_upload_disabled():
    """P8 默认关闭：禁止自动上传"""
    cfg = get_default_config()
    assert cfg.security.auto_upload is False


def test_get_default_config_returns_fresh_instances():
    """每次调用返回新对象（避免共享引用）"""
    cfg1 = get_default_config()
    cfg2 = get_default_config()
    cfg1.personality.name = "test"
    assert cfg2.personality.name == "清秋"  # 没被污染


def test_default_config_round_trip_via_dump():
    """默认值可以 dump / load 无丢失"""
    cfg = get_default_config()
    data = cfg.model_dump(mode="json")
    reloaded = Config(**data)
    assert reloaded.security.whitelist_dirs == cfg.security.whitelist_dirs
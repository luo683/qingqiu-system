"""manager.py 测试 · ConfigManager 加载 + 优先级 + 热重载"""

import asyncio
import os
import time
from pathlib import Path

import pytest
import yaml

from qingqiu.config import ConfigManager
from qingqiu.config.schema import Config


def test_manager_uses_default_path(monkeypatch):
    monkeypatch.delenv("QINGQIU_LLM_DEFAULT", raising=False)
    manager = ConfigManager()
    assert manager.config_path == Path.home() / ".qingqiu" / "config.yaml"


def test_manager_load_returns_config(monkeypatch, tmp_path):
    monkeypatch.delenv("QINGQIU_LLM_DEFAULT", raising=False)
    manager = ConfigManager(config_path=tmp_path / "nonexistent.yaml")
    cfg = manager.load()
    assert isinstance(cfg, Config)
    assert cfg.personality.name == "清秋"


def test_manager_loads_from_file(monkeypatch, tmp_path):
    monkeypatch.delenv("QINGQIU_LLM_DEFAULT", raising=False)
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump({
        "llm": {"default": "openai", "routing": {"planner": "openai"}},
        "personality": {"name": "测试清秋"},
    }, allow_unicode=True))

    manager = ConfigManager(config_path=config_file)
    cfg = manager.load()
    assert cfg.llm.default == "openai"
    assert cfg.personality.name == "测试清秋"


def test_manager_env_overrides_file(monkeypatch, tmp_path):
    """环境变量优先级高于文件"""
    monkeypatch.delenv("QINGQIU_LLM_DEFAULT", raising=False)
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump({
        "llm": {"default": "openai"},
    }, allow_unicode=True))

    monkeypatch.setenv("QINGQIU_LLM_DEFAULT", "anthropic")
    manager = ConfigManager(config_path=config_file)
    cfg = manager.load()
    # 环境变量赢
    assert cfg.llm.default == "anthropic"


def test_manager_env_overrides_nested(monkeypatch, tmp_path):
    monkeypatch.delenv("QINGQIU_PERSONALITY_NAME", raising=False)
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump({"personality": {"name": "原名"}}, allow_unicode=True))

    monkeypatch.setenv("QINGQIU_PERSONALITY_NAME", "新名")
    manager = ConfigManager(config_path=config_file)
    cfg = manager.load()
    assert cfg.personality.name == "新名"


def test_manager_save_atomic(tmp_path):
    """save 用 atomic write（写 tmp 后 rename）"""
    config_file = tmp_path / "config.yaml"
    manager = ConfigManager(config_path=config_file)
    manager._config.personality.name = "saved-name"
    manager.save()

    assert config_file.exists()
    assert not (tmp_path / "config.yaml.tmp").exists()
    loaded = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert loaded["personality"]["name"] == "saved-name"


def test_manager_save_creates_parent_dirs(tmp_path):
    config_file = tmp_path / "nested" / "deep" / "config.yaml"
    manager = ConfigManager(config_path=config_file)
    manager.save()
    assert config_file.exists()


def test_manager_load_corrupt_file_keeps_default(monkeypatch, tmp_path, capsys):
    """损坏的 YAML 文件不破坏 manager（保留默认配置）"""
    monkeypatch.delenv("QINGQIU_LLM_DEFAULT", raising=False)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("invalid: yaml: : :", encoding="utf-8")

    manager = ConfigManager(config_path=config_file)
    cfg = manager.load()
    # 用默认配置
    assert cfg.personality.name == "清秋"
    # 但应该有 stderr 输出
    captured = capsys.readouterr()
    assert "加载失败" in captured.out or "加载失败" in captured.err


def test_manager_on_change_registers_listener():
    manager = ConfigManager()
    callback = lambda c: None
    manager.on_change(callback)
    assert callback in manager._listeners


@pytest.mark.asyncio
async def test_manager_hot_reload_detects_change(tmp_path):
    """改配置文件后热重载在 1s 内检测到"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump({"personality": {"name": "原名"}}, allow_unicode=True))

    manager = ConfigManager(config_path=config_file)
    manager.load()
    assert manager.config.personality.name == "原名"

    # 启动监听
    await manager.start_watching(interval=0.2)

    # 改文件
    config_file.write_text(yaml.safe_dump({"personality": {"name": "新名"}}, allow_unicode=True))

    # 等 1 秒（2 个 poll 周期）
    await asyncio.sleep(0.5)

    # 应该自动重载
    assert manager.config.personality.name == "新名"

    await manager.stop_watching()


@pytest.mark.asyncio
async def test_manager_hot_reload_triggers_callback(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump({"personality": {"name": "原"}}, allow_unicode=True))

    manager = ConfigManager(config_path=config_file)
    manager.load()

    callback_count = {"n": 0}
    received_names: list[str] = []

    def on_change(cfg: Config) -> None:
        callback_count["n"] += 1
        received_names.append(cfg.personality.name)

    manager.on_change(on_change)
    await manager.start_watching(interval=0.2)

    config_file.write_text(yaml.safe_dump({"personality": {"name": "新"}}, allow_unicode=True))
    await asyncio.sleep(0.5)

    assert callback_count["n"] >= 1
    assert "新" in received_names

    await manager.stop_watching()


@pytest.mark.asyncio
async def test_manager_hot_reload_ignores_missing_file(tmp_path):
    """配置文件被删除时 polling 不报错"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump({"personality": {"name": "原"}}, allow_unicode=True))

    manager = ConfigManager(config_path=config_file)
    manager.load()
    await manager.start_watching(interval=0.2)

    # 删除文件
    config_file.unlink()
    await asyncio.sleep(0.4)

    # 配置保留（不回退到默认值）
    assert manager.config.personality.name == "原"

    await manager.stop_watching()
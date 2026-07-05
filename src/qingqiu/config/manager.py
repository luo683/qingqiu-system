"""ConfigManager · 加载 + 优先级 + 热重载

优先级（高 → 低）：
1. 环境变量（QINGQIU_<KEY>_<SUBKEY>）
2. 配置文件（~/.qingqiu/config.yaml）
3. 默认值（schema 定义）

热重载：asyncio polling · 每 1s 检查文件 mtime · 变更触发回调
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Callable

import yaml

from qingqiu.config.defaults import get_default_config, get_default_config_path
from qingqiu.config.schema import Config


# 环境变量到配置路径的映射（最高优先级）
_ENV_MAPPINGS: dict[str, tuple[str, ...]] = {
    "QINGQIU_LLM_DEFAULT": ("llm", "default"),
    "QINGQIU_LLM_ROUTING_PLANNER": ("llm", "routing", "planner"),
    "QINGQIU_LLM_ROUTING_ROUTER": ("llm", "routing", "router"),
    "QINGQIU_LLM_ROUTING_MEMORY": ("llm", "routing", "memory"),
    "QINGQIU_VOICE_HOTKEY": ("voice", "hotkey"),
    "QINGQIU_VOICE_STT_MODEL": ("voice", "stt_model"),
    "QINGQIU_OBSIDIAN_VAULT_PATH": ("obsidian", "vault_path"),
    "QINGQIU_PERSONALITY_NAME": ("personality", "name"),
    "QINGQIU_PERSONALITY_SYSTEM_PROMPT": ("personality", "system_prompt"),
}


class ConfigManager:
    """配置管理器

    用法：
        manager = ConfigManager()
        manager.load()                          # 同步加载
        cfg = manager.config                    # 访问当前配置

        await manager.start_watching()           # 启动异步热重载
        manager.on_change(lambda c: print(c))   # 注册变更回调
        ...
        await manager.stop_watching()
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or get_default_config_path()
        self._config: Config = get_default_config()
        self._last_signature: tuple[float, int] = (0.0, 0)  # (mtime, size)
        self._watch_task: asyncio.Task[None] | None = None
        self._listeners: list[Callable[[Config], None]] = []

    # ── 加载 ──────────────────────────────────────

    def load(self) -> Config:
        """按优先级加载配置（同步）"""
        # 1. 默认值（已在 __init__）
        # 2. 配置文件
        self._load_from_file()
        # 3. 环境变量（最高优先级）
        self._apply_env_overrides()
        return self._config

    def _load_from_file(self) -> None:
        """从 YAML 文件加载"""
        if not self.config_path.exists():
            return
        try:
            data = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._config = Config(**data)
                stat = self.config_path.stat()
                self._last_signature = (stat.st_mtime, stat.st_size)
        except (yaml.YAMLError, ValueError) as e:
            # 加载失败保留旧配置（不要让 config 损坏让整个 daemon 起不来）
            print(f"[config] 加载失败，保留旧配置：{e}")

    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        for env_key, path in _ENV_MAPPINGS.items():
            value = os.environ.get(env_key)
            if value is None:
                continue
            self._set_nested(path, value)

    def _set_nested(self, path: tuple[str, ...], value: str) -> None:
        """设置嵌套属性（如 ('llm', 'routing', 'planner') = 'anthropic'）"""
        target: object = self._config
        for key in path[:-1]:
            target = getattr(target, key)
        setattr(target, path[-1], value)

    # ── 持久化 ──────────────────────────────────────

    def save(self) -> None:
        """保存当前配置到文件（atomic write 防止崩溃损坏）"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._config.model_dump(mode="json", exclude_none=True)
        yaml_str = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)

        tmp = self.config_path.with_suffix(".yaml.tmp")
        tmp.write_text(yaml_str, encoding="utf-8")
        tmp.replace(self.config_path)
        stat = self.config_path.stat()
        self._last_signature = (stat.st_mtime, stat.st_size)

    # ── 访问 ──────────────────────────────────────

    @property
    def config(self) -> Config:
        """当前配置"""
        return self._config

    # ── 热重载 ──────────────────────────────────────

    def on_change(self, listener: Callable[[Config], None]) -> None:
        """注册配置变更回调"""
        self._listeners.append(listener)

    async def start_watching(self, interval: float = 1.0) -> None:
        """启动 polling 监听（每 1s 检查文件签名）

        满足 S1.3 验收"改 config 1s 内生效"

        用 (mtime, size) 元组检测变更，避免 Windows 上 mtime 精度问题
        （即使文件改了，mtime 可能不变，size 通常会变）
        """

        # 关键：同步初始化签名（在 task 启动前）
        # 否则 task 第一次醒来时读到的就是"修改后"的签名，
        # 导致永远检测不到"修改"事件（签名永远匹配）
        if self.config_path.exists():
            stat = self.config_path.stat()
            self._last_signature = (stat.st_mtime, stat.st_size)

        async def _watch_loop() -> None:
            while True:
                await asyncio.sleep(interval)
                if not self.config_path.exists():
                    continue
                try:
                    stat = self.config_path.stat()
                    signature = (stat.st_mtime, stat.st_size)
                    if signature != self._last_signature:
                        self._last_signature = signature
                        old_dump = self._config.model_dump_json()
                        self.load()
                        if self._config.model_dump_json() != old_dump:
                            for listener in self._listeners:
                                listener(self._config)
                except Exception as e:
                    print(f"[config] 热重载失败：{e}")

        self._watch_task = asyncio.create_task(_watch_loop())

    async def stop_watching(self) -> None:
        """停止热重载"""
        if self._watch_task is not None:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None
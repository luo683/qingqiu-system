"""人格 personality.yaml 加载 + 热重载

S6.5 切片：用户可编辑 ``~/.qingqiu/personality.yaml`` 调整人格字段，
下一轮 LLM 调用即生效（mtime polling）。

设计要点：
- personality.yaml 是**单独文件**，不嵌在 config.yaml 里（PRD §8.2）
- mtime 变化触发 reload（每次访问 config 时检查）
- 文件不存在时自动写入默认内容（首次启动友好）
- Pydantic 校验，缺字段走 schema default
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class PersonalityConfig(BaseModel):
    """人格配置

    字段：
    - name: 唤醒词 / 显示名
    - system_prompt: 注入 LLM 的 system prompt
    - tone: 语气（neutral / friendly / formal / humorous）
    - language: 主语言（默认 zh-CN）
    """

    name: str = "清秋"
    system_prompt: str = Field(
        default=(
            "你是清秋，给 ROG 个人使用。\n"
            "风格：简洁、直接、技术男、偶尔幽默。\n"
            "唤醒词：\"清秋\"。"
        ),
    )
    tone: str = "neutral"
    language: str = "zh-CN"


# 默认路径：与 config.yaml 同目录，独立文件
DEFAULT_PERSONALITY_PATH = Path.home() / ".qingqiu" / "personality.yaml"


def _build_default_yaml_text(default: PersonalityConfig) -> str:
    """渲染默认 personality.yaml 文本（带注释 + 多行 system_prompt）"""
    lines = [
        "# 清秋人格配置 · 改完下一轮 LLM 自动生效",
        f"name: {default.name}",
        f"tone: {default.tone}",
        f"language: {default.language}",
        "system_prompt: |",
    ]
    lines.extend(f"  {line}" for line in default.system_prompt.split("\n"))
    lines.append("")  # 末尾换行
    return "\n".join(lines)


class PersonalityLoader:
    """Personality 加载器（mtime hot reload）

    用法：
        loader = PersonalityLoader()          # 默认路径 ~/.qingqiu/personality.yaml
        loader = PersonalityLoader(custom)    # 测试用
        cfg = loader.config                   # 自动检测 mtime 变更
        loader.reload()                       # 主动重载
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path: Path = path or DEFAULT_PERSONALITY_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._config: PersonalityConfig | None = None
        self._last_mtime: float = 0.0
        self._ensure_default()
        self.reload()

    # ── 文件写入 ──────────────────────────────────────

    def _ensure_default(self) -> None:
        """文件不存在时写入默认配置（首次启动友好）"""
        if not self._path.exists():
            self._path.write_text(
                _build_default_yaml_text(PersonalityConfig()),
                encoding="utf-8",
            )

    # ── 加载 ──────────────────────────────────────────

    def reload(self) -> PersonalityConfig:
        """从文件 reload（hot reload 入口）

        支持两种 YAML 写法：
        1. 平铺：
           ```yaml
           name: 清秋
           system_prompt: |
             ...
           ```
        2. 嵌套（PRD §8.2）：
           ```yaml
           personality:
             name: 清秋
             system_prompt: |
               ...
           ```
        """
        with self._path.open("r", encoding="utf-8") as f:
            data: Any = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            data = {}
        # PRD §8.2: 嵌套 personality: 格式
        if "personality" in data and isinstance(data["personality"], dict):
            data = data["personality"]
        # Pydantic 校验：缺字段走 schema default
        self._config = PersonalityConfig(**data)
        try:
            self._last_mtime = self._path.stat().st_mtime
        except OSError:
            self._last_mtime = 0.0
        return self._config

    # ── 访问 ──────────────────────────────────────────

    @property
    def config(self) -> PersonalityConfig:
        """当前配置（访问时自动 mtime 检测）

        mtime 变化即 reload，无需手动调用。
        """
        try:
            current_mtime = self._path.stat().st_mtime
        except OSError:
            # 文件被删/无权限时保留旧配置，不抛
            if self._config is None:
                self._config = PersonalityConfig()
            return self._config
        if current_mtime != self._last_mtime:
            self.reload()
        assert self._config is not None  # reload() 已赋值
        return self._config

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def system_prompt(self) -> str:
        return self.config.system_prompt

    @property
    def path(self) -> Path:
        return self._path


# ── 模块级单例 + 便捷函数 ──────────────────────────────

_default_loader: PersonalityLoader | None = None


def get_personality(path: Path | None = None) -> PersonalityConfig:
    """获取全局人格配置（懒加载单例）

    测试场景：传入 ``path`` 会重建 loader（不修改单例），便于隔离。
    """
    global _default_loader
    if path is not None:
        # 调用方显式传 path → 走独立 loader（不影响默认单例）
        return PersonalityLoader(path).config
    if _default_loader is None:
        _default_loader = PersonalityLoader()
    return _default_loader.config


def get_system_prompt() -> str:
    """便捷函数：直接拿到 system_prompt 字符串"""
    return get_personality().system_prompt


def reset_default_loader() -> None:
    """测试辅助：重置单例

    让每个测试用 ``monkeypatch`` 切换 ``DEFAULT_PERSONALITY_PATH`` 后能干净重建。
    """
    global _default_loader
    _default_loader = None
"""PreferenceLearner · 用户偏好学习（M10 · S10.2）

用户纠正 / 显式偏好 → 追加到 personality.yaml 的 ``system_prompt``。
下一轮 LLM 调用即通过 PersonalityLoader hot reload 拿到新值。

复用：
- ``qingqiu.personality.DEFAULT_PERSONALITY_PATH``：默认 ~/.qingqiu/personality.yaml
- ``qingqiu.growth.config.GrowthConfig``：enabled 开关（默认 True）

不调 LLM：纯文本追加；不去重以外的语义处理。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from qingqiu.growth.config import GrowthConfig
from qingqiu.personality import DEFAULT_PERSONALITY_PATH


# 追加到 system_prompt 的列表标记（一行一个 preference）
_PREFERENCE_BULLET = "- "


class PreferenceLearner:
    """用户偏好学习器

    用法：
        learner = PreferenceLearner()
        new_prompt = learner.learn("不写 emoji")
        # → personality.yaml system_prompt 追加 "- 不写 emoji"

    MVP 行为：
    - read personality.yaml → 解析（含 nested `personality:` 兼容） → 追加偏好
      到 system_prompt 末尾（list-style，`- ` 前缀）→ 写回文件
    - 同一 preference 已存在 → 不重复追加
    - 空字符串 / 纯空白 → 跳过（返 None）
    - growth.enabled=False → 短路返 None，不读不写
    - 文件不存在 → 走 Pydantic schema default 创建后追加
    """

    def __init__(
        self,
        *,
        path: Path | None = None,
        growth: GrowthConfig | None = None,
    ) -> None:
        self._path: Path = Path(path) if path is not None else DEFAULT_PERSONALITY_PATH
        self._growth: GrowthConfig = growth if growth is not None else GrowthConfig()

    # ── 入口短路 ──────────────────────────────────────

    def is_enabled(self) -> bool:
        return self._growth.is_enabled()

    # ── 主入口 ──────────────────────────────────────

    def learn(self, preference: str) -> str | None:
        """追加一条 preference 到 personality.yaml system_prompt

        Args:
            preference: 用户偏好文本（自动 strip）

        Returns:
            更新后的完整 system_prompt；disabled / 空输入 / YAML 解析失败 → None
        """
        if not self.is_enabled():
            return None

        pref = (preference or "").strip()
        if not pref:
            return None

        # 读现有文件（保持原 root 结构 / nested 包装）
        root = self._read_yaml()
        if root is None:
            # YAML 损坏 / IO 错误 → 不写
            return None

        has_wrapper = (
            "personality" in root
            and isinstance(root["personality"], dict)
        )
        inner: dict[str, Any] = root["personality"] if has_wrapper else root

        current_prompt = str(inner.get("system_prompt", ""))

        # 幂等：已存在则不重复追加
        if self._preference_exists(current_prompt, pref):
            return current_prompt

        # 追加（用列表 bullet 风格，每行一条）
        new_prompt = self._append_prompt(current_prompt, pref)
        inner["system_prompt"] = new_prompt

        # 写回
        if not self._write_yaml(root):
            return None
        return new_prompt

    # ── 内部：YAML 读 / 写 ─────────────────────────────

    def _read_yaml(self) -> dict[str, Any] | None:
        """读 personality.yaml；不存在 → 走 Pydantic schema default"""
        if not self._path.exists():
            # 走 PersonalityLoader 的 _ensure_default 行为
            from qingqiu.personality import PersonalityConfig
            default_text = self._build_default_yaml_text(PersonalityConfig())
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(default_text, encoding="utf-8")

        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            return None
        if not isinstance(data, dict):
            return None
        return data

    def _write_yaml(self, data: dict[str, Any]) -> bool:
        """atomic write：写 .tmp → rename"""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(self._path.suffix + ".tmp")
            tmp.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            tmp.replace(self._path)
            return True
        except OSError:
            return False

    @staticmethod
    def _build_default_yaml_text(default: Any) -> str:
        """与 qingqiu.personality._build_default_yaml_text 同步（不依赖私有符号）"""
        lines = [
            "# 清秋人格配置 · 改完下一轮 LLM 自动生效",
            f"name: {default.name}",
            f"tone: {default.tone}",
            f"language: {default.language}",
            "system_prompt: |",
        ]
        lines.extend(f"  {line}" for line in default.system_prompt.split("\n"))
        lines.append("")
        return "\n".join(lines)

    # ── 内部：追加 / 去重 ─────────────────────────────

    @staticmethod
    def _preference_exists(prompt: str, pref: str) -> bool:
        """检查 preference 是否已存在于 prompt（按行匹配 bullet 风格）"""
        needle = f"{_PREFERENCE_BULLET}{pref}".strip()
        for line in prompt.splitlines():
            if line.strip() == needle:
                return True
            # 兼容：去前缀后比较
            stripped = line.strip()
            if stripped.startswith(_PREFERENCE_BULLET) and stripped[len(_PREFERENCE_BULLET):] == pref:
                return True
        return False

    @staticmethod
    def _append_prompt(current: str, pref: str) -> str:
        """追加一条 preference 到 prompt 末尾（保留原有换行结构）"""
        line = f"{_PREFERENCE_BULLET}{pref}"
        if not current:
            return line
        # 末尾是否已有换行：strip right 后再加
        base = current.rstrip()
        return f"{base}\n{line}"

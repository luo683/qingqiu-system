"""GrowthConfig · 自我成长开关配置（M10 · S10.6）

MVP 阶段：从环境变量读 growth.enabled，不动 Config schema。
复用人设路径：~/.qingqiu/personality.yaml 不动。

所有 growth 函数（reflect / weekly / preference / vault_feed / conflict）
都应在入口调用 ``is_enabled()``；返回 False 时应短路返 None。
"""

from __future__ import annotations

import os
from pathlib import Path


# 环境变量名（最高优先级；缺省走默认）
_GROWTH_ENABLED_ENV = "QINGQIU_GROWTH_ENABLED"


class GrowthConfig:
    """自我成长配置

    字段：
    - enabled: 是否启用成长机制（默认 True；env QINGQIU_GROWTH_ENABLED=false 关闭）
    - weekly_dir: 周报输出目录（默认 ~/.qingqiu/memory/weekly/）

    方法：
    - is_enabled() → bool：开关状态（所有 growth 函数的入口短路判定）
    """

    DEFAULT_WEEKLY_DIR = Path.home() / ".qingqiu" / "memory" / "weekly"

    def __init__(
        self,
        enabled: bool | None = None,
        weekly_dir: Path | None = None,
    ) -> None:
        # enabled：env > 参数 > 默认 True
        if enabled is None:
            env_val = os.environ.get(_GROWTH_ENABLED_ENV)
            if env_val is None:
                enabled = True
            else:
                enabled = env_val.strip().lower() not in ("0", "false", "no", "off")
        self.enabled = enabled
        self.weekly_dir = Path(weekly_dir) if weekly_dir is not None else self.DEFAULT_WEEKLY_DIR

    def is_enabled(self) -> bool:
        """开关状态：所有 growth 函数的入口短路判定

        Returns:
            bool: True → 允许执行；False → 应返 None / empty（不写文件、不更新 L2/L3）
        """
        return bool(self.enabled)

    def __repr__(self) -> str:
        return f"GrowthConfig(enabled={self.enabled}, weekly_dir={self.weekly_dir})"
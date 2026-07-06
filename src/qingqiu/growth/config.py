"""GrowthConfig · 自我成长开关配置（M10 · S10.6）

MVP 阶段：从环境变量读 growth.enabled，不动 Config schema。
复用人设路径：~/.qingqiu/personality.yaml 不动。
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

    def __repr__(self) -> str:
        return f"GrowthConfig(enabled={self.enabled}, weekly_dir={self.weekly_dir})"
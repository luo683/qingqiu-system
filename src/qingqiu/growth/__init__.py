"""growth module · 自我成长（M10）

S10.1 reflect agent · S10.2 preference learning · S10.3 vault feed
S10.4 每周复盘 · S10.5 偏好冲突检测 · S10.6 growth.enabled 开关

复用：
- memory.l3.L3FactsMemory（SQLite facts）
- memory.l2.L2UserMemory（key=value 文件）
- personality.DEFAULT_PERSONALITY_PATH（~/.qingqiu/personality.yaml）

不调 LLM（纯统计 / 文本 / YAML 操作）。
"""

from qingqiu.growth.config import GrowthConfig
from qingqiu.growth.conflict import ConflictDetector
from qingqiu.growth.preference import PreferenceLearner
from qingqiu.growth.reflect import Reflector
from qingqiu.growth.vault_feed import VaultFeeder, parse_note
from qingqiu.growth.weekly import WeeklyReport

# S10.6 canonical entry: re-export under "growth_config" name (same class)
from qingqiu.growth.growth_config import GrowthConfig as GrowthConfigS10_6

__all__ = [
    "ConflictDetector",
    "GrowthConfig",
    "GrowthConfigS10_6",
    "PreferenceLearner",
    "Reflector",
    "VaultFeeder",
    "WeeklyReport",
    "parse_note",
]

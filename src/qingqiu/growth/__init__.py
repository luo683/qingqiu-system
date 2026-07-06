"""growth module · 自我成长（M10）

S10.1 reflect agent · S10.4 每周复盘
复用 memory.l3.L3FactsMemory（SQLite facts），不调 LLM。
"""

from qingqiu.growth.config import GrowthConfig
from qingqiu.growth.reflect import Reflector
from qingqiu.growth.weekly import WeeklyReport

__all__ = [
    "GrowthConfig",
    "Reflector",
    "WeeklyReport",
]
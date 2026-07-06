"""growth_config · S10.6 growth.enabled 开关

本文件是 M10 S10.6 切片的规范入口。``GrowthConfig`` 实际定义在
``config.py``（S10.1/S10.4 时期实现的兼容入口），这里 re-export 让
调用方既能 ``from qingqiu.growth.growth_config import GrowthConfig``
（命名即文档），又能保持 ``from qingqiu.growth.config import GrowthConfig``
（旧代码兼容）。

用法：

    from qingqiu.growth.growth_config import GrowthConfig
    gc = GrowthConfig()
    if not gc.is_enabled():
        return None  # 所有 growth 函数的标准入口短路
"""

from qingqiu.growth.config import GrowthConfig

__all__ = ["GrowthConfig"]

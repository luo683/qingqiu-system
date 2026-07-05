"""S1.3 热重载真跑验证脚本

启动 ConfigManager watcher → 改文件 → 验证 1s 内重载
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "src")
from qingqiu.config import ConfigManager, get_default_config_path


async def main():
    config_path = get_default_config_path()
    print(f"[config] path: {config_path}")

    manager = ConfigManager(config_path=config_path)
    manager.load()
    initial_name = manager.config.personality.name
    print(f"[init] personality.name = {initial_name!r}")

    await manager.start_watching(interval=0.5)
    print("[watch] started, polling every 0.5s")
    await asyncio.sleep(0.6)  # 让 watcher 初始化

    # 第一次修改
    config_path.write_text(
        "personality:\n  name: 热重载测试清秋\n",
        encoding="utf-8",
    )
    print("[modify] file changed → name: 热重载测试清秋")

    await asyncio.sleep(1.2)

    after_reload_1 = manager.config.personality.name
    print(f"[after-reload-1] personality.name = {after_reload_1!r}")
    success_1 = after_reload_1 == "热重载测试清秋"
    print(f"[result-1] 热重载 #1: {'PASS' if success_1 else 'FAIL'}")

    # 第二次修改
    config_path.write_text(
        "personality:\n  name: 再次重载\n",
        encoding="utf-8",
    )
    print("[modify-2] file changed → name: 再次重载")

    await asyncio.sleep(1.2)

    after_reload_2 = manager.config.personality.name
    print(f"[after-reload-2] personality.name = {after_reload_2!r}")
    success_2 = after_reload_2 == "再次重载"
    print(f"[result-2] 热重载 #2: {'PASS' if success_2 else 'FAIL'}")

    await manager.stop_watching()

    # 总结
    print(f"\n[summary] 2 次热重载测试: {'BOTH PASS' if (success_1 and success_2) else 'FAIL'}")
    sys.exit(0 if (success_1 and success_2) else 1)


if __name__ == "__main__":
    asyncio.run(main())
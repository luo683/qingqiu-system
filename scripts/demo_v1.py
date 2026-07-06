"""demo_v1.py · 清秋 v1.0 MVP 端到端 Demo

跑 6 个真实场景证明 `qingqiu ask "<natural language>"` 可用：
1. memory CRUD (set/get/list/delete)
2. 中文混合记忆
3. task 全链路 (add/list/done)
4. status
5. memory delete + 验证 not found
6. UNKNOWN fallback

直接调用 Executor（不依赖子进程），验证 v1.0 MVP 全链路。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# 把 src 加进 path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# monkeypatch TaskStore 用临时路径（隔离真实 ~/.qingqiu/tasks.json）
from qingqiu.cli.task import TaskStore

_ORIG = TaskStore.__init__
_TMP = Path(tempfile.mkdtemp(prefix="qingqiu_demo_"))


def _patched(self, path=None):
    _ORIG(self, path=path or (_TMP / "tasks.json"))


TaskStore.__init__ = _patched

from qingqiu.cli.output import OutputFormatter
from qingqiu.router.executor import Executor

executor = Executor(llm_provider=None, use_llm=False)
out = OutputFormatter(json_mode=False, no_color=True)


BANNER = r"""
   ____         __    __  __
  / __/__ _____/ /__ / /_/ /
 / _// _ `/ _  / -_/ ___/_  __/
/___/\_,_/\_,_/_/\_\\__/   /_/

清秋 v1.0 MVP · 端到端 Demo
"""


def step(n: int, title: str, cmd: str):
    print(f"\n[{n}] {title}")
    print(f'    $ qingqiu ask "{cmd}"')
    rc = executor.execute(cmd, out)
    print(f"    exit_code = {rc}")
    return rc


def main():
    print(BANNER)
    print(f"使用临时 TaskStore: {_TMP}")
    print(f"使用 LLM: 否（规则匹配）")
    print(f"使用自然语言：是（router + executor）\n")

    passed = 0
    failed = 0

    def assert_pass(rc: int):
        nonlocal passed, failed
        if rc == 0:
            passed += 1
        else:
            failed += 1

    # === 1. memory CRUD ===
    assert_pass(step(1, "写入记忆（英文）", "memory set user_name ROG"))
    assert_pass(step(1, "写入记忆（中文 key）", "memory set 项目名 qingqiu-system"))
    assert_pass(step(1, "读取记忆", "memory get user_name"))
    assert_pass(step(1, "列出全部记忆", "memory list"))

    # === 2. 中文混合 ===
    assert_pass(step(2, "中文 key + value", "memory set 偏好 不写 emoji"))
    assert_pass(step(2, "读取中文 key", "memory get 偏好"))

    # === 3. task 全链路 ===
    assert_pass(step(3, "新建任务（中文触发）", "新建任务 写 MVP 文档"))
    assert_pass(step(3, "新建任务（英文触发）", "task add Implement S2.6"))
    assert_pass(step(3, "查看任务", "看任务"))

    store = TaskStore()
    tasks = store.list()
    if tasks:
        tid = tasks[0]["id"]
        assert_pass(step(3, f"完成任务 {tid}", f"完成 {tid}"))

    # === 4. status ===
    assert_pass(step(4, "健康状态", "status"))

    # === 5. delete + 验证 ===
    assert_pass(step(5, "写入待删除", "memory set tmp_k tmp_v"))
    assert_pass(step(5, "删除", "memory delete tmp_k"))
    rc = step(5, "再读（应 not found）", "memory get tmp_k")
    if rc == 1:
        passed += 1
        print("    [PASS] not found 友好提示")
    else:
        failed += 1

    # === 6. UNKNOWN fallback ===
    rc = step(6, "无法识别", "随便说点什么 123")
    if rc == 1:
        passed += 1
    else:
        failed += 1

    # === 总结 ===
    print("\n" + "=" * 60)
    print(f"[demo] v1.0 MVP 端到端 Demo · 通过 {passed} / 失败 {failed}")
    print("=" * 60)
    if failed == 0:
        print("\n✓ 清秋 v1.0 MVP 可落地第一版 验收通过")
        print("\n核心链路:")
        print("  自然语言 → IntentClassifier (规则优先) → 实体提取")
        print("  → Executor → 复用 cli/memory.py / cli/task.py / cli/status.py")
        print("  → Memory 4 层 / TaskStore → 输出")
        print("\n试试交互:")
        print('  qingqiu ask "memory get user_name"')
        print('  qingqiu ask "新建任务 写文档"')
        print('  qingqiu ask "看任务"')
        print('  qingqiu ask "status"')
        return 0
    else:
        print(f"\n✗ {failed} 个场景失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
"""verify_s2_4.py · S2.4 Executor 真跑验证

端到端跑 5 个真实指令 + 1 个 UNKNOWN + 1 个中文混合
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# 把 worktree src 加进 path
WORKTREE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKTREE / "src"))

# monkeypatch TaskStore 用临时路径
from qingqiu.cli.task import TaskStore

_ORIG_TASK_INIT = TaskStore.__init__
_TMP = Path(tempfile.mkdtemp(prefix="qingqiu_verify_"))


def _patched_init(self, path=None):
    _ORIG_TASK_INIT(self, path=path or (_TMP / "tasks.json"))


TaskStore.__init__ = _patched_init

from qingqiu.cli.output import OutputFormatter
from qingqiu.router.executor import Executor

executor = Executor(llm_provider=None, use_llm=False)
out = OutputFormatter(json_mode=False, no_color=True)


def section(title: str):
    print(f"\n{'=' * 60}")
    print(f"[verify] {title}")
    print("=" * 60)


def run(text: str, expect_intent: str = None) -> bool:
    print(f"\n>>> qingqiu ask \"{text}\"")
    rc = executor.execute(text, out)
    print(f"    exit_code = {rc}")
    return rc


def main():
    print(f"Tmp TaskStore path: {_TMP}")
    print("=" * 60)

    section("场景 1: memory set → memory get → memory list")
    assert run("memory set user_name ROG", "MEMORY_SET") == 0
    assert run("memory set project_name qingqiu-system", "MEMORY_SET") == 0
    assert run("memory get user_name", "MEMORY_GET") == 0
    assert run("memory list", "MEMORY_LIST") == 0

    section("场景 2: 中文混合指令")
    assert run("memory set 偏好 不写 emoji", "MEMORY_SET") == 0
    assert run("memory get 偏好", "MEMORY_GET") == 0

    section("场景 3: task add → task list → task done")
    assert run("新建任务 修 S2.4 bug", "TASK_ADD") == 0
    assert run("task add Write demo doc", "TASK_ADD") == 0
    assert run("看任务", "TASK_LIST") == 0
    # 抓任务 ID
    store = TaskStore()
    tasks = store.list()
    assert tasks, "expected tasks"
    tid = tasks[0]["id"]
    print(f"\n[verify] using task id: {tid}")
    assert run(f"完成 {tid}", "TASK_DONE") == 0
    # 再 list 看状态
    assert run("看任务", "TASK_LIST") == 0

    section("场景 4: status")
    assert run("status", "STATUS") == 0

    section("场景 5: memory delete")
    assert run("memory set tmp_key tmp_val", "MEMORY_SET") == 0
    assert run("memory delete tmp_key", "MEMORY_DELETE") == 0
    # 再 get 应该 not found
    rc = run("memory get tmp_key", "MEMORY_GET")
    print(f"    [verify] get deleted key exit_code = {rc} (期望 1 = not found)")
    assert rc == 1, "应该返 1（key not found）"

    section("场景 6: UNKNOWN fallback")
    assert run("随便说点乱码 123", "UNKNOWN") == 1

    section("场景 7: 缺实体（验证 ValueError 友好错误）")
    assert run("memory get", "MEMORY_GET") == 1

    print("\n" + "=" * 60)
    print("[verify] S2.4 PASS · 7 场景全过")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
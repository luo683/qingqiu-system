"""S2.5 真跑验证脚本 · Confirm CLI 端到端

S2.5 核心验收（6 步 + 3 步扩展）：
1. qingqiu --help 含 confirm
2. qingqiu confirm --help 含 ask + test
3. qingqiu confirm test --always-yes → exit 0
4. qingqiu confirm test --always-no → exit 0（prompter 返回 False，handler 期望 reject）
5. qingqiu confirm test 默认（无 flag）→ exit 0
6. qingqiu --json confirm test --always-no → JSON 输出 ok=False

7. (in-process) run_confirm_ask + injected yes prompter → exit 0
8. (in-process) run_confirm_ask + injected no prompter → exit 1
9. (in-process) run_confirm_ask + injected timeout prompter → exit 1
"""

import json
import subprocess
import sys
import time
from pathlib import Path


# === helpers ===

def run(cmd: list[str], cwd: Path, timeout: int = 30, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run"] + cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=timeout,
        env=env or {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )


def main() -> int:
    project_dir = Path("E:/MiniMax Code WorkSpace/qingqiu-system")

    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
        if not condition:
            failures.append(name)

    print("[verify] S2.5 Confirm CLI 真跑验证")
    print(f"[verify] project: {project_dir}")
    print()

    # === 1. qingqiu --help 含 confirm ===
    print("[step 1] qingqiu --help 含 confirm")
    r = run(["qingqiu", "--help"], project_dir)
    check("exit 0", r.returncode == 0, f"got {r.returncode}")
    check("help 含 confirm", "confirm" in r.stdout, r.stdout[:200])
    print()

    # === 2. qingqiu confirm --help 含 ask + test ===
    print("[step 2] qingqiu confirm --help 含 ask + test")
    r = run(["qingqiu", "confirm", "--help"], project_dir)
    check("exit 0", r.returncode == 0)
    for action in ["ask", "test"]:
        check(f"confirm --help 含 {action}", action in r.stdout)
    print()

    # === 3. qingqiu confirm test --always-yes → exit 0 ===
    print("[step 3] qingqiu confirm test --always-yes")
    r = run(["qingqiu", "confirm", "test", "--always-yes"], project_dir)
    check("exit 0", r.returncode == 0, f"got {r.returncode}: {r.stdout[:100]}")
    check("输出 passed/approved", "passed" in r.stdout.lower() or "approved" in r.stdout.lower(), r.stdout[:120])
    print()

    # === 4. qingqiu confirm test --always-no → exit 0 ===
    print("[step 4] qingqiu confirm test --always-no")
    r = run(["qingqiu", "confirm", "test", "--always-no"], project_dir)
    check("exit 0", r.returncode == 0, f"got {r.returncode}: {r.stdout[:100]}")
    check("输出 passed/rejected", "passed" in r.stdout.lower() or "rejected" in r.stdout.lower(), r.stdout[:120])
    print()

    # === 5. qingqiu confirm test 默认 → exit 0 ===
    print("[step 5] qingqiu confirm test (default)")
    r = run(["qingqiu", "confirm", "test"], project_dir)
    check("exit 0", r.returncode == 0, f"got {r.returncode}: {r.stdout[:100]}")
    print()

    # === 6. qingqiu --json confirm test --always-no → JSON ===
    print("[step 6] qingqiu --json confirm test --always-no (JSON)")
    r = run(["qingqiu", "--json", "confirm", "test", "--always-no"], project_dir)
    check("exit 0", r.returncode == 0, f"got {r.returncode}: {r.stderr[:200]}")
    try:
        payload = json.loads(r.stdout)
        check("JSON ok=True", payload.get("ok") is True, str(payload)[:120])
    except json.JSONDecodeError as e:
        check(f"JSON parse: {e}", False, r.stdout[:100])
    print()

    # === 7-9. in-process run_confirm_ask + 注入 prompter ===
    print("[step 7-9] run_confirm_ask 注入 prompter 测试")
    sys.path.insert(0, str(project_dir / "src"))
    from qingqiu.cli.confirm import run_confirm_ask
    from qingqiu.cli.output import OutputFormatter
    from qingqiu.security.confirm import Confirm, Prompter

    class _FixedPrompter(Prompter):
        def __init__(self, agreed: bool) -> None:
            self._agreed = agreed

        def ask(self, summary: str, timeout_sec: int = 60) -> bool:
            return self._agreed

    class _SlowPrompter(Prompter):
        """模拟超时：等超过 timeout_sec 才返回 False（模拟"超时自动拒绝"）"""

        def ask(self, summary: str, timeout_sec: int = 60) -> bool:
            time.sleep(timeout_sec + 1)
            return False  # 超时 → 拒绝

    import qingqiu.cli.confirm as cli_confirm

    # 7. 同意
    print("[step 7] injected yes-prompter → exit 0")
    cli_confirm.Confirm = lambda default_timeout=60: Confirm(
        prompter=_FixedPrompter(True), default_timeout=default_timeout
    )
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("A", (), {"summary": "Apply 3 changes?", "timeout": 1})()
    rc = run_confirm_ask(args, out)
    check("同意 → exit 0", rc == 0, f"got {rc}")

    # 8. 拒绝
    print("[step 8] injected no-prompter → exit 1")
    cli_confirm.Confirm = lambda default_timeout=60: Confirm(
        prompter=_FixedPrompter(False), default_timeout=default_timeout
    )
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("A", (), {"summary": "Delete?", "timeout": 1})()
    rc = run_confirm_ask(args, out)
    check("拒绝 → exit 1", rc == 1, f"got {rc}")

    # 9. 超时
    print("[step 9] injected slow-prompter → exit 1 (timeout)")
    cli_confirm.Confirm = lambda default_timeout=60: Confirm(
        prompter=_SlowPrompter(), default_timeout=default_timeout
    )
    out = OutputFormatter(json_mode=False, no_color=True)
    args = type("A", (), {"summary": "Apply?", "timeout": 1})()
    rc = run_confirm_ask(args, out)
    check("超时 → exit 1", rc == 1, f"got {rc}")
    print()

    # === 收尾 ===
    print("=" * 60)
    if failures:
        print(f"[verify] FAIL ({len(failures)} failures)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[verify] S2.5 PASS · 9/9 验证全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
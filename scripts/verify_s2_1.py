"""S2.1 真跑脚本：CLI 子命令树 + memory 子命令端到端验证

S2.1 核心验收（10 步）：
1. qingqiu --help 列出全部子命令
2. qingqiu memory --help 完整帮助
3. qingqiu memory set + get 一致
4. qingqiu memory set --layer L1 写到 Markdown 文件
5. qingqiu --json memory get 输出 JSON
6. qingqiu memory list 表格输出
7. qingqiu memory delete 成功
8. qingqiu memory delete 不存在 → exit 1
9. qingqiu memory search 匹配
10. 老命令 qingqiu config show / llm test 不回归
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run"] + cmd,
        capture_output=True, text=True,
        cwd=str(cwd), timeout=30,
    )


def main() -> int:
    project_dir = Path("E:/MiniMax Code WorkSpace/qingqiu-system")
    mem_dir = Path.home() / ".qingqiu" / "memory"

    # 清理之前测试残留
    if mem_dir.exists():
        shutil.rmtree(mem_dir)

    print(f"[verify] project: {project_dir}")
    print(f"[verify] memory dir: {mem_dir}")
    print()

    failures = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
        if not condition:
            failures.append(name)

    # === 1. --help 列出全部子命令 ===
    print("[step 1] qingqiu --help")
    r = run(["qingqiu", "--help"], project_dir)
    check("exit code 0", r.returncode == 0, f"got {r.returncode}")
    for cmd in ["ask", "chat", "task", "memory", "status", "config", "llm"]:
        check(f"--help 列出 {cmd}", cmd in r.stdout, f"missing: {cmd}")
    print()

    # === 2. memory --help 完整 ===
    print("[step 2] qingqiu memory --help")
    r = run(["qingqiu", "memory", "--help"], project_dir)
    check("exit code 0", r.returncode == 0)
    for action in ["get", "set", "list", "delete", "search"]:
        check(f"memory --help 列出 {action}", action in r.stdout)
    print()

    # === 3. memory set + get 一致 ===
    print("[step 3] memory set + get")
    r1 = run(["qingqiu", "memory", "set", "user_name", "ROG"], project_dir)
    check("set exit 0", r1.returncode == 0, r1.stdout[:50])
    r2 = run(["qingqiu", "memory", "get", "user_name"], project_dir)
    check("get exit 0", r2.returncode == 0)
    check("get 包含 ROG", "ROG" in r2.stdout, f"got: {r2.stdout[:80]}")
    print()

    # === 4. set --layer L1 写到 Markdown ===
    print("[step 4] memory set --layer L1")
    r = run(["qingqiu", "memory", "set", "--layer", "L1", "project_lang", "python"], project_dir)
    check("set L1 exit 0", r.returncode == 0)
    l1_file = mem_dir / "projects" / "default.md"
    check("L1 文件存在", l1_file.exists(), str(l1_file))
    if l1_file.exists():
        content = l1_file.read_text(encoding="utf-8")
        check("L1 文件包含 project_lang = python", "project_lang = python" in content, content[:100])
    print()

    # === 5. --json memory get ===
    print("[step 5] --json memory get")
    r = run(["qingqiu", "--json", "memory", "get", "user_name"], project_dir)
    check("exit 0", r.returncode == 0)
    try:
        payload = json.loads(r.stdout)
        check("JSON ok=True", payload.get("ok") is True)
        check("JSON data.value == ROG", payload.get("data", {}).get("value") == "ROG")
        check("JSON data.layer == L3", payload.get("data", {}).get("layer") == "L3")
    except json.JSONDecodeError as e:
        check(f"JSON parse: {e}", False, r.stdout[:100])
    print()

    # === 6. memory list 表格 ===
    print("[step 6] memory list")
    r = run(["qingqiu", "memory", "list"], project_dir)
    check("list exit 0", r.returncode == 0)
    check("list 包含 user_name", "user_name" in r.stdout)
    check("list 包含 project_lang", "project_lang" in r.stdout)
    print()

    # === 7. memory delete 成功 ===
    print("[step 7] memory delete 成功")
    r = run(["qingqiu", "memory", "delete", "user_name"], project_dir)
    check("delete exit 0", r.returncode == 0)
    r2 = run(["qingqiu", "memory", "get", "user_name"], project_dir)
    check("delete 后 get 应失败 (exit 1)", r2.returncode == 1, f"got {r2.returncode}")
    print()

    # === 8. memory delete 不存在 ===
    print("[step 8] memory delete 不存在")
    r = run(["qingqiu", "memory", "delete", "nonexistent_xyz"], project_dir)
    check("delete 不存在 exit 1", r.returncode == 1, f"got {r.returncode}")
    print()

    # === 9. memory search ===
    print("[step 9] memory search 'python'")
    r = run(["qingqiu", "memory", "search", "python"], project_dir)
    check("search exit 0", r.returncode == 0)
    check("search 找到 project_lang", "project_lang" in r.stdout)
    print()

    # === 10. 老命令不回归 ===
    print("[step 10] 老命令 qingqiu config show")
    r = run(["qingqiu", "config", "show"], project_dir)
    check("config show exit 0", r.returncode == 0)
    check("config show 输出 yaml 头", "llm:" in r.stdout or "logging:" in r.stdout)

    print("[step 10b] 老命令 qingqiu llm test openai（无 key）")
    r = run(["qingqiu", "llm", "test", "openai"], project_dir)
    # 应该 exit 1（无 API key）
    check("llm test openai exit 1 (无 key)", r.returncode == 1, f"got {r.returncode}")
    print()

    # === 收尾 ===
    print("=" * 60)
    if failures:
        print(f"[verify] FAIL ({len(failures)} failures)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[verify] S2.1 PASS · 10 步验证全过")
    print(f"[verify] L1 文件保留: {l1_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
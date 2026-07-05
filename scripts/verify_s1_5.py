"""S1.5 真跑脚本：4 层记忆 set/get 一致性"""

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_dir = Path("E:/MiniMax Code WorkSpace/qingqiu-system")
    mem_dir = Path.home() / ".qingqiu" / "memory"

    # 清理之前测试残留
    if mem_dir.exists():
        shutil.rmtree(mem_dir)

    print(f"[verify] project: {project_dir}")
    print(f"[verify] memory dir: {mem_dir}")
    print()

    # === step 1: 直接 Python 调 4 层独立 set/get ===
    print("[step 1] 4 层独立 set/get 一致性")
    code = f"""
import sys
sys.path.insert(0, r'{project_dir / "src"}')
from pathlib import Path
from qingqiu.memory import L0SessionMemory, L1ProjectMemory, L2UserMemory, L3FactsMemory

mem_dir = Path(r'{mem_dir}')
mem_dir.mkdir(parents=True, exist_ok=True)

# L0
l0 = L0SessionMemory()
l0.set('user_name', 'ROG')
assert l0.get('user_name') == 'ROG', 'L0 get mismatch'
print('L0 OK:', l0.get('user_name'))

# L1
l1 = L1ProjectMemory(mem_dir / 'projects' / 'test_proj.md')
l1.set('language', 'python')
assert l1.get('language') == 'python'
print('L1 OK:', l1.get('language'))

# L2
l2 = L2UserMemory(mem_dir / 'user.md')
l2.set('theme', 'dark_mode')
assert l2.get('theme') == 'dark_mode'
print('L2 OK:', l2.get('theme'))

# L3
l3 = L3FactsMemory(mem_dir / 'facts.sqlite')
l3.set('fact_count', '42')
assert l3.get('fact_count') == '42'
print('L3 OK:', l3.get('fact_count'))

# 验证磁盘持久化
assert (mem_dir / 'projects' / 'test_proj.md').exists(), 'L1 file should exist'
assert (mem_dir / 'user.md').exists(), 'L2 file should exist'
assert (mem_dir / 'facts.sqlite').exists(), 'L3 file should exist'

# L3 跨进程（模拟重启）
l3_new = L3FactsMemory(mem_dir / 'facts.sqlite')
assert l3_new.get('fact_count') == '42', 'L3 should persist'
print('L3 persistence OK')

print('STEP1 PASS')
"""
    result = subprocess.run(
        ["uv", "run", "python", "-c", code],
        capture_output=True, text=True,
        cwd=str(project_dir), timeout=60,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr[:500])
        return 1
    assert "STEP1 PASS" in result.stdout, "step 1 should pass"

    print()
    print("[step 2] Memory facade 跨层查找 + 显式分层写入")

    code2 = f"""
import sys
sys.path.insert(0, r'{project_dir / "src"}')
from pathlib import Path
from qingqiu.memory import Memory

mem_dir = Path(r'{mem_dir}')
m = Memory(base_dir=mem_dir)

# 默认写到 L3
m.set('project_version', '0.3.0')
value, layer = m.get('project_version')
assert value == '0.3.0', f'expected 0.3.0, got {{value}}'
assert layer == 'L3', f'expected L3, got {{layer}}'
print(f'Memory.set default → {{layer}}: {{value}}')

# 显式写到 L1
m.set('build_tool', 'uv', layer='L1')
v, layer = m.get('build_tool')
assert v == 'uv' and layer == 'L1', f'L1 set failed: {{v}}/{{layer}}'
print(f'Memory.set layer=L1 → {{layer}}: {{v}}')

# list_keys 应该合并所有层
keys = m.list_keys()
print(f'Memory.list_keys: {{keys}}')
assert 'project_version' in keys
assert 'build_tool' in keys

# 删除
assert m.delete('project_version', layer='L3') is True
assert m.get('project_version')[0] is None
print('Memory.delete OK')

print('STEP2 PASS')
"""
    result = subprocess.run(
        ["uv", "run", "python", "-c", code2],
        capture_output=True, text=True,
        cwd=str(project_dir), timeout=60,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr[:500])
        return 1
    assert "STEP2 PASS" in result.stdout, "step 2 should pass"

    print()
    print("[step 3] 文件内容 + SQLite 结构验证")
    # L1 file
    l1_file = mem_dir / "projects" / "test_proj.md"
    l1_content = l1_file.read_text(encoding="utf-8")
    print(f"  L1 file ({l1_file}):")
    for line in l1_content.splitlines():
        print(f"    {line}")
    assert "language = python" in l1_content

    # L2 file
    l2_file = mem_dir / "user.md"
    l2_content = l2_file.read_text(encoding="utf-8")
    print(f"  L2 file ({l2_file}):")
    for line in l2_content.splitlines():
        print(f"    {line}")
    assert "theme = dark_mode" in l2_content

    # L1 build_tool (step 2)
    l1_bt = mem_dir / "projects" / "default.md"
    if l1_bt.exists():
        l1_bt_content = l1_bt.read_text(encoding="utf-8")
        print(f"  L1 default file ({l1_bt}):")
        for line in l1_bt_content.splitlines():
            print(f"    {line}")
        assert "build_tool = uv" in l1_bt_content

    # SQLite
    l3_db = mem_dir / "facts.sqlite"
    print(f"  L3 db ({l3_db}): {l3_db.stat().st_size} bytes")
    assert l3_db.exists()

    print()
    print("[step 4] 验证日志系统记录了 S1.5 操作（可选）")
    # S1.4 没接 memory 的日志，但可以查 main log 是否有最近的 Python 进程日志
    log_file = Path.home() / ".qingqiu" / "logs" / "qingqiu.log"
    if log_file.exists():
        print(f"  log file: {log_file} ({log_file.stat().st_size} bytes)")

    print()
    print("[verify] S1.5 PASS · 4 层记忆 set/get 一致性 + 持久化 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
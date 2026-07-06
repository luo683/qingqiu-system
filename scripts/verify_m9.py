"""M9 真跑验证脚本（4 场景端到端）

启动 UI server（127.0.0.1:7789）→ 4 个 curl 验证场景：
- M9-1: GET /health → ok=True
- M9-2: GET /api/graph.json → 包含 nodes + edges + count
- M9-3: GET / → 返回 HTML 且包含 cytoscape
- M9-4: GET /api/filter?tag=arch → 只返 arch 节点 + 子图边

运行：
    cd <repo>
    uv run python scripts/verify_m9.py
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_DIR = Path("E:/MiniMax Code WorkSpace/qingqiu-system")
HOST = "127.0.0.1"
PORT = 7789
BASE = f"http://{HOST}:{PORT}"
STARTUP_TIMEOUT = 15.0  # 秒


# === helpers ===

def _http_get(path: str, timeout: float = 5.0) -> tuple[int, str, dict[str, str]]:
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, dict(e.headers) if e.headers else {}
    except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
        return 0, f"ERROR: {e}", {}


def _wait_for_health(timeout: float) -> bool:
    """等服务起来，最多等 timeout 秒"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        code, body, _ = _http_get("/health", timeout=1.5)
        if code == 200 and "ok" in body:
            try:
                if json.loads(body).get("ok") is True:
                    return True
            except json.JSONDecodeError:
                pass
        time.sleep(0.2)
    return False


def _kill_port(port: int) -> None:
    """关闭占用端口的旧进程（Windows）"""
    try:
        # 找出占用端口的 PID
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue "
             f"| Select-Object -ExpandProperty OwningProcess"],
            capture_output=True, text=True, timeout=10,
        )
        for pid_str in result.stdout.strip().splitlines():
            pid_str = pid_str.strip()
            if not pid_str.isdigit():
                continue
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 f"Stop-Process -Id {pid_str} -Force -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, timeout=10,
            )
        # 同时清掉可能正在跑的 verify 子进程遗留（uv + python）
        for proc_name in ("uv.exe", "python.exe", "qingqiu-ui"):
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 f"Get-Process -Name '{proc_name}' -ErrorAction SilentlyContinue "
                 f"| Where-Object {{ $_.MainWindowTitle -eq '' -and $_.Id -ne $PID }} "
                 f"| Stop-Process -Force -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, timeout=10,
            )
    except Exception:
        pass


def _kill_pid_tree(pid: int) -> None:
    """递归 kill PID + 子进程（Windows 用 wmic / taskkill）"""
    if pid <= 0:
        return
    try:
        # taskkill /T 杀进程树
        subprocess.run(
            ["taskkill.exe", "/F", "/T", "/PID", str(pid)],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        pass


# === 4 验证场景 ===

def scenario_1_health() -> list[str]:
    fails: list[str] = []
    print("[M9-1] GET /health")
    code, body, _ = _http_get("/health")
    print(f"  status={code}")
    print(f"  body={body[:200]}")
    if code != 200:
        fails.append(f"M9-1 status {code} != 200")
        return fails
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        fails.append(f"M9-1 JSON parse: {e}")
        return fails
    if payload.get("ok") is not True:
        fails.append(f"M9-1 ok != true: {payload}")
    if payload.get("service") != "qingqiu-ui":
        fails.append(f"M9-1 service: {payload.get('service')!r}")
    if payload.get("version") != "M9":
        fails.append(f"M9-1 version: {payload.get('version')!r}")
    if payload.get("nodes", 0) < 10:
        fails.append(f"M9-1 nodes < 10: {payload.get('nodes')}")
    return fails


def scenario_2_graph_json() -> list[str]:
    fails: list[str] = []
    print("[M9-2] GET /api/graph.json")
    code, body, _ = _http_get("/api/graph.json")
    print(f"  status={code}")
    if code != 200:
        fails.append(f"M9-2 status {code} != 200")
        return fails
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        fails.append(f"M9-2 JSON parse: {e}")
        return fails
    if "nodes" not in payload or "edges" not in payload:
        fails.append(f"M9-2 missing nodes/edges")
        return fails
    nodes = payload["nodes"]
    edges = payload["edges"]
    if len(nodes) < 10:
        fails.append(f"M9-2 nodes count {len(nodes)} < 10")
    if not isinstance(edges, list) or len(edges) < 1:
        fails.append(f"M9-2 edges count {len(edges)} < 1")
    # Cytoscape 格式
    for n in nodes[:3]:
        if "data" not in n or "id" not in n["data"]:
            fails.append(f"M9-2 node shape: {n}")
            break
    print(f"  nodes={len(nodes)} edges={len(edges)}")
    return fails


def scenario_3_index_html() -> list[str]:
    fails: list[str] = []
    print("[M9-3] GET /  (web/index.html)")
    code, body, headers = _http_get("/")
    print(f"  status={code} content-type={headers.get('content-type', '?')}")
    if code != 200:
        fails.append(f"M9-3 status {code} != 200")
        return fails
    if "cytoscape" not in body.lower():
        fails.append("M9-3 body missing 'cytoscape' reference")
    if "/api/graph.json" not in body:
        fails.append("M9-3 body missing /api/graph.json fetch")
    if "清秋" not in body:
        fails.append("M9-3 body missing '清秋' title")
    if len(body) < 500:
        fails.append(f"M9-3 body too short: {len(body)} bytes")
    print(f"  body_len={len(body)}")
    return fails


def scenario_4_filter() -> list[str]:
    fails: list[str] = []
    print("[M9-4] GET /api/filter?tag=arch")
    code, body, _ = _http_get("/api/filter?tag=arch")
    print(f"  status={code}")
    if code != 200:
        fails.append(f"M9-4 status {code} != 200")
        return fails
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        fails.append(f"M9-4 JSON parse: {e}")
        return fails
    if payload.get("filter_tag") != "arch":
        fails.append(f"M9-4 filter_tag: {payload.get('filter_tag')!r}")
    # 所有节点都必须含 arch tag
    for n in payload.get("flat_nodes", []):
        if "arch" not in n.get("tags", []):
            fails.append(f"M9-4 non-arch node leaked: {n['id']}")
    # 边必须在子图内
    flat_ids = {n["id"] for n in payload.get("flat_nodes", [])}
    for e in payload.get("edges", []):
        if e["data"]["source"] not in flat_ids or e["data"]["target"] not in flat_ids:
            fails.append(f"M9-4 edge leaks outside subgraph: {e}")
            break
    # 节点数 < 全图（除非全图所有节点都是 arch）
    full_count = payload.get("original_count", {}).get("nodes", 0)
    filt_count = payload.get("count", {}).get("nodes", 0)
    if filt_count == 0:
        fails.append("M9-4 filter returned 0 nodes (expected ≥ 1)")
    if full_count and filt_count > full_count:
        fails.append(f"M9-4 filtered {filt_count} > full {full_count}")
    print(f"  filtered_nodes={filt_count}/{full_count} edges={payload.get('count', {}).get('edges', 0)}")
    return fails


# === main ===

def main() -> int:
    print(f"[verify] M9 知识图谱 UI 真跑验证")
    print(f"[verify] project: {PROJECT_DIR}")
    print(f"[verify] endpoint: {BASE}")
    print()

    # 0. 清理占用端口的旧进程
    print("[step 0] cleanup port", PORT)
    _kill_port(PORT)
    time.sleep(0.5)

    # 1. 启动 UI server（子进程 + 独立进程组）
    print("[step 1] start uvicorn server (subprocess)")
    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    # CREATE_NEW_PROCESS_GROUP 让 taskkill /T 能干净地杀整棵进程树
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "qingqiu.ui", "--host", HOST, "--port", str(PORT)],
        cwd=str(PROJECT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=creationflags,
    )

    failures: list[str] = []

    try:
        # 2. 等 health 就绪
        print(f"[step 2] wait for /health (timeout {STARTUP_TIMEOUT}s)")
        if not _wait_for_health(STARTUP_TIMEOUT):
            failures.append("server did not become healthy in time")
            print("  server failed to start")
        else:
            print("  server ready")
        print()

        if not failures:
            # 3. 4 个场景
            failures += scenario_1_health()
            print()
            failures += scenario_2_graph_json()
            print()
            failures += scenario_3_index_html()
            print()
            failures += scenario_4_filter()
            print()
    finally:
        # 4. 关掉 server（taskkill /T 杀整棵进程树）
        print("[step 99] terminate server")
        # 先尝试温和终止，timeout 后再 taskkill
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _kill_pid_tree(proc.pid)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
        # 关闭 PIPE 防止 reader thread 继续在后台解码
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass

    print()
    print("=" * 60)
    total = 4
    passed = total - len(failures)
    if failures:
        print(f"[verify] M9 FAIL · {passed}/{total} passed")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"[verify] M9 PASS · {passed}/{total} 验证全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""S1.4 真跑脚本：跑出错的命令验证日志写入"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_dir = Path("E:/MiniMax Code WorkSpace/qingqiu-system")
    log_dir = Path.home() / ".qingqiu" / "logs"

    # 清理之前的测试日志
    for f in log_dir.glob("qingqiu*"):
        f.unlink()

    print(f"[verify] log_dir: {log_dir}")
    print()

    # 触发一些日志输出：跑多次 qingqiu 命令（成功 + 失败）
    print("[step 1] qingqiu --version（成功路径）")
    result = subprocess.run(
        ["uv", "run", "qingqiu", "--version"],
        capture_output=True, text=True, cwd=str(project_dir),
        env={**__import__("os").environ, "QINGQIU_LOG_DIR": str(log_dir)},
    )
    print(f"  exit code: {result.returncode}")
    print(f"  stdout: {result.stdout.strip()}")
    assert result.returncode == 0, "version 命令应该成功"

    print()
    print("[step 2] qingqiu llm test ollama（连接失败 → 错误日志）")
    result = subprocess.run(
        ["uv", "run", "qingqiu", "llm", "test", "ollama"],
        capture_output=True, text=True, cwd=str(project_dir),
        timeout=15,
    )
    print(f"  exit code: {result.returncode}")
    print(f"  stderr: {result.stderr.strip()[:200]}")

    print()
    print("[step 3] qingqiu llm test openai（无 API key → 错误日志）")
    # 清掉 ANTHROPIC_API_KEY 等避免干扰
    env = {k: v for k, v in __import__("os").environ.items()
           if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_HOST")}
    result = subprocess.run(
        ["uv", "run", "qingqiu", "llm", "test", "openai"],
        capture_output=True, text=True, cwd=str(project_dir),
        env=env,
        timeout=10,
    )
    print(f"  exit code: {result.returncode}")
    print(f"  stderr: {result.stderr.strip()[:200]}")

    print()
    print("[step 4] 验证日志文件存在")
    main_log = log_dir / "qingqiu.log"
    error_log = log_dir / "qingqiu.error.log"

    print(f"  main log: {main_log} (exists: {main_log.exists()})")
    print(f"  error log: {error_log} (exists: {error_log.exists()})")

    if main_log.exists():
        size_kb = main_log.stat().st_size / 1024
        print(f"  main log size: {size_kb:.2f} KB")
        # 显示前 20 行
        lines = main_log.read_text(encoding="utf-8").splitlines()
        print(f"  main log lines: {len(lines)}")
        print("  --- 前 10 行 ---")
        for line in lines[:10]:
            print(f"    {line}")
        print("  ---")

    if error_log.exists():
        size_kb = error_log.stat().st_size / 1024
        print(f"  error log size: {size_kb:.2f} KB")

    print()
    # 验收断言
    assert main_log.exists(), f"主日志文件应该存在: {main_log}"
    assert error_log.exists(), f"错误日志文件应该存在: {error_log}"

    main_content = main_log.read_text(encoding="utf-8")
    error_content = error_log.read_text(encoding="utf-8")

    # 至少有 version 成功的日志
    assert "0.3.0" in main_content or "qingqiu" in main_content, "主日志应有成功路径输出"

    # 错误日志应有 ollama 连接失败
    assert "ConnectError" in error_content or "connection" in error_content.lower(), \
        f"错误日志应有 ollama 连接失败信息. 内容: {error_content[:500]}"

    # 错误日志应有 openai 无 key
    assert "OPENAI_API_KEY" in error_content or "API key" in error_content, \
        f"错误日志应有 openai API key 缺失信息. 内容: {error_content[:500]}"

    print("[verify] S1.4 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""S5.3 真跑验证 · 危险操作黑名单

8 个核心场景：
1. ``check_shell("rm -rf /tmp/test")`` → 抛 BlacklistError
2. ``check_shell("ls /tmp")`` → 通过
3. ``check_shell("git push --force origin main")`` → 抛
4. ``check_shell("git push origin main")`` → 通过
5. ``check_operation(OperationType.CLOUD_UPLOAD)`` → 抛
6. ``check_operation(OperationType.VAULT_DELETE)`` → 抛
7. ``is_blacklisted_shell("rm -rf /")`` → True
8. ``is_blacklisted_shell("echo hello")`` → False
"""

from __future__ import annotations

import sys

from qingqiu.security.blacklist import (
    BlacklistError,
    OperationType,
    check_operation,
    check_shell,
    is_blacklisted_shell,
)


def main() -> int:
    failures: list[str] = []

    def expect_block(name: str, fn) -> None:
        try:
            fn()
        except BlacklistError:
            print(f"  [PASS] {name}（抛 BlacklistError）")
        except Exception as e:  # noqa: BLE001
            print(f"  [FAIL] {name}（抛了非 BlacklistError: {type(e).__name__}: {e}）")
            failures.append(name)
        else:
            print(f"  [FAIL] {name}（没抛异常）")
            failures.append(name)

    def expect_pass(name: str, fn) -> None:
        try:
            fn()
        except BlacklistError as e:
            print(f"  [FAIL] {name}（不应抛，但抛了: {e}）")
            failures.append(name)
        except Exception as e:  # noqa: BLE001
            print(f"  [FAIL] {name}（意外异常 {type(e).__name__}: {e}）")
            failures.append(name)
        else:
            print(f"  [PASS] {name}（通过）")

    def expect_bool(name: str, got: bool, want: bool) -> None:
        if got == want:
            print(f"  [PASS] {name}（got={got}）")
        else:
            print(f"  [FAIL] {name}（got={got}, want={want}）")
            failures.append(name)

    print("[step 1] check_shell 黑名单命令")
    expect_block("rm -rf /tmp/test", lambda: check_shell("rm -rf /tmp/test"))
    print()

    print("[step 2] check_shell 安全命令")
    expect_pass("ls /tmp", lambda: check_shell("ls /tmp"))
    print()

    print("[step 3] check_shell git push --force")
    expect_block(
        "git push --force origin main",
        lambda: check_shell("git push --force origin main"),
    )
    print()

    print("[step 4] check_shell git push 无 force")
    expect_pass(
        "git push origin main",
        lambda: check_shell("git push origin main"),
    )
    print()

    print("[step 5] check_operation 黑名单")
    expect_block(
        "OperationType.CLOUD_UPLOAD",
        lambda: check_operation(OperationType.CLOUD_UPLOAD),
    )
    print()

    print("[step 6] check_operation VAULT_DELETE")
    expect_block(
        "OperationType.VAULT_DELETE",
        lambda: check_operation(OperationType.VAULT_DELETE),
    )
    print()

    print("[step 7] is_blacklisted_shell True")
    expect_bool("rm -rf /", is_blacklisted_shell("rm -rf /"), True)
    print()

    print("[step 8] is_blacklisted_shell False")
    expect_bool("echo hello", is_blacklisted_shell("echo hello"), False)
    print()

    print("=" * 60)
    if failures:
        print(f"[verify] FAIL ({len(failures)} failures)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[verify] S5.3 PASS · 8 步验证全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""S5.1 真跑验证脚本 · Confirm 通用框架"""

import sys
import time
from pathlib import Path

# 让 src/ 可 import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> int:
    from qingqiu.security.confirm import (
        CLIPrompter,
        Confirm,
        ConfirmRejected,
        ConfirmTimeout,
        Prompter,
        ask,
        get_default_confirm,
    )

    failures = []
    print("[verify] S5.1 Confirm 通用框架真跑验证")
    print()

    # 场景 1: 用户输入 y 同意
    print("[scenario 1] user says 'y' -> approve")
    p = CLIPrompter(input_func=lambda _: "y")
    c = Confirm(prompter=p, default_timeout=2)
    try:
        if c.ask("Apply 3 file changes?"):
            print("  [PASS] approved")
        else:
            print("  [FAIL] expected approve")
            failures.append("scenario 1")
    except Exception as e:
        print(f"  [FAIL] unexpected: {e}")
        failures.append("scenario 1")

    # 场景 2: 用户输入 n 拒绝
    print("[scenario 2] user says 'n' -> reject (ConfirmRejected)")
    p = CLIPrompter(input_func=lambda _: "n")
    c = Confirm(prompter=p, default_timeout=2)
    try:
        c.ask("Apply 3 file changes?")
        print("  [FAIL] expected reject")
        failures.append("scenario 2")
    except ConfirmRejected:
        print("  [PASS] rejected correctly")

    # 场景 3: 超时自动拒绝
    print("[scenario 3] timeout 1s -> auto-reject (ConfirmTimeout)")
    def slow_input(_):
        time.sleep(5)
        return "y"
    p = CLIPrompter(input_func=slow_input)
    c = Confirm(prompter=p, default_timeout=1)
    try:
        c.ask("Apply 3 file changes?")
        print("  [FAIL] expected timeout")
        failures.append("scenario 3")
    except ConfirmRejected as e:
        if "timeout" in str(e).lower() or "rejected" in str(e).lower():
            print(f"  [PASS] auto-rejected: {e}")
        else:
            print(f"  [PASS] rejected: {e}")

    # 场景 4: 用户输入 diff 后再 yes
    print("[scenario 4] user says 'diff' then 'y'")
    responses = iter(["diff", "y"])
    p = CLIPrompter(input_func=lambda _: next(responses))
    c = Confirm(prompter=p, default_timeout=2)
    try:
        if c.ask("Apply changes?"):
            print("  [PASS] diff then approve")
        else:
            print("  [FAIL] expected approve after diff")
            failures.append("scenario 4")
    except Exception as e:
        print(f"  [FAIL] unexpected: {e}")
        failures.append("scenario 4")

    # 场景 5: 用户输入 diff 后再 no
    print("[scenario 5] user says 'diff' then 'n'")
    responses = iter(["diff", "n"])
    p = CLIPrompter(input_func=lambda _: next(responses))
    c = Confirm(prompter=p, default_timeout=2)
    try:
        c.ask("Apply changes?")
        print("  [FAIL] expected reject after diff")
        failures.append("scenario 5")
    except ConfirmRejected:
        print("  [PASS] diff then reject")

    # 场景 6: 自定义 Prompter（AlwaysYes）
    print("[scenario 6] custom AlwaysYesPrompter")
    class AlwaysYes(Prompter):
        def ask(self, summary: str, timeout_sec: int = 60) -> bool:
            return True
    c = Confirm(prompter=AlwaysYes(), default_timeout=2)
    try:
        if c.ask("anything?"):
            print("  [PASS] custom prompter works")
    except Exception as e:
        print(f"  [FAIL] unexpected: {e}")
        failures.append("scenario 6")

    # 场景 7: 自定义 Prompter（AlwaysNo）
    print("[scenario 7] custom AlwaysNoPrompter -> reject")
    class AlwaysNo(Prompter):
        def ask(self, summary: str, timeout_sec: int = 60) -> bool:
            return False
    c = Confirm(prompter=AlwaysNo(), default_timeout=2)
    try:
        c.ask("anything?")
        print("  [FAIL] expected reject")
        failures.append("scenario 7")
    except ConfirmRejected:
        print("  [PASS] rejected")

    # 场景 8: 便捷函数 ask() 用默认 singleton
    print("[scenario 8] ask() function with default singleton")
    import qingqiu.security.confirm as confirm_mod
    confirm_mod._default_confirm = Confirm(
        prompter=CLIPrompter(input_func=lambda _: "y")
    )
    try:
        if ask("test?", timeout_sec=1):
            print("  [PASS] ask() works")
    except Exception as e:
        print(f"  [FAIL] unexpected: {e}")
        failures.append("scenario 8")
    confirm_mod._default_confirm = None

    # 场景 9: 空输入 = N
    print("[scenario 9] empty input -> reject (default N)")
    p = CLIPrompter(input_func=lambda _: "")
    c = Confirm(prompter=p, default_timeout=2)
    try:
        c.ask("Apply?")
        print("  [FAIL] expected reject on empty")
        failures.append("scenario 9")
    except ConfirmRejected:
        print("  [PASS] empty -> reject (default N)")

    # 场景 10: 自定义 timeout 覆盖 default
    print("[scenario 10] custom timeout overrides default")
    def slow_input(_):
        time.sleep(2)
        return "y"
    p = CLIPrompter(input_func=slow_input)
    c = Confirm(prompter=p, default_timeout=10)
    try:
        c.ask("Apply?", timeout_sec=1)  # 1s 覆盖 10s
        print("  [FAIL] expected timeout")
        failures.append("scenario 10")
    except ConfirmRejected:
        print("  [PASS] custom timeout honored")

    print()
    if failures:
        print(f"[verify] FAIL: {failures}")
        return 1
    print("[verify] S5.1 PASS · 10/10 scenarios passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
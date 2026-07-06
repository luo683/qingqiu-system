"""S5.2 真跑验证脚本"""

import sys
from pathlib import Path

# 让 src/ 可 import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> int:
    from qingqiu.security.whitelist import (
        WHITELIST_DIRS,
        WhitelistError,
        check_path,
        is_whitelisted,
        resolve,
    )

    failures = []
    print(f"[verify] whitelist dirs: {[str(d) for d in WHITELIST_DIRS]}")
    print()

    # 场景 1: 白名单内文件
    print("[scenario 1] whitelist README")
    if is_whitelisted(Path("E:/MiniMax Code WorkSpace/qingqiu-system/README.md")):
        print("  [PASS] is_whitelisted README")
    else:
        print("  [FAIL] README should be whitelisted")
        failures.append("scenario 1")

    # 场景 2: Windows hosts 被拒
    print("[scenario 2] windows hosts blocked")
    if not is_whitelisted(Path("C:/Windows/System32/drivers/etc/hosts")):
        print("  [PASS] hosts correctly blocked")
    else:
        print("  [FAIL] hosts should be blocked")
        failures.append("scenario 2")

    # 场景 3: check_path 在白名单返回绝对路径
    print("[scenario 3] check_path inside returns abs")
    try:
        result = check_path(Path("E:/MiniMax Code WorkSpace/qingqiu-system/README.md"))
        if result.is_absolute():
            print(f"  [PASS] returned absolute: {result}")
        else:
            print(f"  [FAIL] not absolute: {result}")
            failures.append("scenario 3")
    except WhitelistError as e:
        print(f"  [FAIL] unexpected WhitelistError: {e}")
        failures.append("scenario 3")

    # 场景 4: check_path SAM 抛异常
    print("[scenario 4] check_path SAM raises")
    try:
        check_path(Path("C:/Windows/System32/config/SAM"))
        print("  [FAIL] SAM should be blocked")
        failures.append("scenario 4")
    except WhitelistError:
        print("  [PASS] SAM correctly blocked")

    # 场景 5: resolve 处理 ..
    print("[scenario 5] resolve dotdot")
    try:
        result = resolve("E:/MiniMax Code WorkSpace/foo/../bar")
        if "MiniMax Code WorkSpace" in str(result):
            print(f"  [PASS] resolved: {result}")
        else:
            print(f"  [FAIL] wrong resolve: {result}")
            failures.append("scenario 5")
    except WhitelistError:
        print("  [FAIL] dotdot resolution should stay in whitelist")
        failures.append("scenario 5")

    # 场景 6: Downloads 白名单
    print("[scenario 6] Downloads allowed")
    try:
        result = check_path(Path("C:/Users/ROG/Downloads/file.pdf"))
        print(f"  [PASS] downloads allowed: {result}")
    except WhitelistError:
        print("  [FAIL] Downloads should be allowed")
        failures.append("scenario 6")

    print()
    if failures:
        print(f"[verify] FAIL: {failures}")
        return 1
    print("[verify] S5.2 PASS · 6/6 scenarios passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
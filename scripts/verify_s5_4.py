"""S5.4 真跑验证脚本 · 私密识别 Detect（端到端）"""

import sys
import tempfile
from pathlib import Path

# 让 src/ 可 import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> int:
    from qingqiu.security.private_detect import (
        PrivateDetector,
        PrivateMatchType,
    )

    detector = PrivateDetector()
    failures: list[str] = []
    passed = 0

    def assert_match(label: str, hits, *, type_: str, pattern: str) -> None:
        nonlocal passed
        ok = any(
            m.match_type.value == type_ and (m.pattern == pattern or m.pattern.endswith(pattern))
            for m in hits
        )
        if ok:
            print(f"  [PASS] {label}")
            passed += 1
        else:
            print(f"  [FAIL] {label} · got types/patterns:")
            for m in hits:
                print(f"         - {m.match_type.value} pattern={m.pattern!r} value={m.matched_value!r}")
            failures.append(label)

    def assert_no_match(label: str, hits, *, pattern: str) -> None:
        nonlocal passed
        ok = not any(m.pattern == pattern for m in hits)
        if ok:
            print(f"  [PASS] {label}")
            passed += 1
        else:
            print(f"  [FAIL] {label} · unexpected {pattern}:")
            for m in hits:
                if m.pattern == pattern:
                    print(f"         - {m.match_type.value} value={m.matched_value!r}")
            failures.append(label)

    print(f"[verify] PrivateDetector · filename patterns={len(PrivateDetector.FILENAME_PATTERNS)}, "
          f"content patterns={len(PrivateDetector.CONTENT_PATTERNS)}, "
          f"private dirs={len(PrivateDetector.PRIVATE_DIRS)}")
    print()

    # 场景 1: 文件名模式命中
    print("[scenario 1] filename match: id_card.txt")
    hits = detector.detect_file(Path("C:/Users/ROG/id_card.txt"))
    assert_match("id_card.txt → FILENAME *id_card*", hits,
                 type_="filename", pattern="*id_card*")

    # 场景 2: 内容身份证命中（合法校验位）
    print("[scenario 2] content: valid id_card_18")
    hits = detector.detect_content("我的身份证是 11010519491231002X")
    assert_match("content id_card_18", hits,
                 type_="content_regex", pattern="id_card_18")

    # 场景 3: 内容手机号命中
    print("[scenario 3] content: cn_mobile")
    hits = detector.detect_content("call me at 13800138000")
    assert_match("content cn_mobile", hits,
                 type_="content_regex", pattern="cn_mobile")

    # 场景 4: 内容邮箱命中
    print("[scenario 4] content: email")
    hits = detector.detect_content("email: alice@example.com")
    assert_match("content email", hits,
                 type_="content_regex", pattern="email")

    # 场景 5: 私密目录命中
    print("[scenario 5] directory: ~/.ssh/")
    hits = detector.detect_file(Path("C:/Users/ROG/.ssh/id_rsa"))
    assert_match("~/.ssh/ → DIRECTORY", hits,
                 type_="directory", pattern=".ssh")

    # 场景 6: 普通路径不是私密目录
    print("[scenario 6] non-private path")
    if detector.is_private_path(Path("C:/Users/ROG/Documents/notes.md")) is False:
        print("  [PASS] Documents not private")
        passed += 1
    else:
        print("  [FAIL] Documents should not be private")
        failures.append("scenario 6")

    # 场景 7: 真实文件（创建 .env 写 AWS key）→ 文件名 + 内容双命中
    print("[scenario 7] real .env file with AWS key")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".env", delete=False, encoding="utf-8"
    ) as f:
        f.write("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n# deployment config\n")
        tmp_path = Path(f.name)
    try:
        hits = detector.detect_file(tmp_path)
        has_filename = any(
            m.match_type == PrivateMatchType.FILENAME for m in hits
        )
        has_aws = any(
            m.pattern == "aws_access_key" for m in hits
        )
        if has_filename and has_aws:
            print(f"  [PASS] .env detected (filename + aws_access_key)")
            passed += 1
        else:
            print(f"  [FAIL] missing filename or aws_access_key · hits:")
            for m in hits:
                print(f"         - {m.match_type.value} {m.pattern} {m.matched_value!r}")
            failures.append("scenario 7")
    finally:
        tmp_path.unlink(missing_ok=True)

    print()
    if failures:
        print(f"[verify] FAIL · {len(failures)} failures:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"[verify] S5.4 PASS · {passed}/7 scenarios passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
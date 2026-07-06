"""S5.5 真跑验证脚本 · 私密处理 Block + Redact (端到端)

Run: uv run python scripts/verify_s5_5.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# 让 src/ 可 import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> int:
    # 清除例外通道 env vars（避免外部环境干扰）
    for k in ("QINGQIU_INCLUDE_PRIVATE", "QINGQIU_REDACT_ONLY"):
        os.environ.pop(k, None)

    from qingqiu.security.sensitive import (
        BlockHandler,
        PrivateDetectResult,
        RedactHandler,
        REDACT_PATTERNS,
        SENSITIVE_TYPES,
        SensitiveBlockError,
        SensitiveDetector,
        SensitiveField,
        SensitiveType,
    )

    failures: list[str] = []
    passed = 0

    def expect(label: str, ok: bool, detail: str = "") -> None:
        nonlocal passed
        if ok:
            print(f"  [PASS] {label}")
            passed += 1
        else:
            print(f"  [FAIL] {label} {detail}")
            failures.append(label)

    print(f"[verify] SensitiveDetector · SENSITIVE_TYPES={len(SENSITIVE_TYPES)} · "
          f"REDACT_PATTERNS={len(REDACT_PATTERNS)}")
    print()

    detector = SensitiveDetector()
    block = BlockHandler(detector)
    redact = RedactHandler(detector)

    # 场景 1: check_text 检测合法身份证
    print("[scenario 1] check_text: 合法身份证")
    r = detector.check_text("我的身份证号 11010519491231002X")
    expect("id_card_18 命中", any(m.pattern == "id_card_18" for m in r.matches))
    expect("has_private=True", r.has_private)

    # 场景 2: classify + masked 正确
    print("[scenario 2] classify: 身份证 masked 格式")
    fields = detector.classify("身份证 11010519491231002X")
    id_cards = [f for f in fields if f.type == SensitiveType.ID_CARD]
    expect("ID_CARD 字段存在", len(id_cards) == 1)
    if id_cards:
        expect("masked == 110105****002X", id_cards[0].masked == "110105****002X",
               f"got {id_cards[0].masked!r}")

    # 场景 3: redact_text 替换多种敏感字段
    print("[scenario 3] redact_text: 替换 phone + email + id_card")
    src_text = "张三 13800138000 邮箱 rog@qq.com 身份证 11010519491231002X"
    out = detector.redact_text(src_text)
    expect("phone masked", "138****8000" in out)
    expect("email masked", "rog***@qq.com" in out)
    expect("id_card masked", "110105****002X" in out)
    expect("中文上下文保留", "张三" in out and "邮箱" in out)

    # 场景 4: BlockHandler 命中抛 SensitiveBlockError
    print("[scenario 4] BlockHandler: 命中 → SensitiveBlockError")
    try:
        block.check_text("身份证 11010519491231002X")
        expect("SensitiveBlockError 抛出", False, "no exception raised")
    except SensitiveBlockError as e:
        expect("SensitiveBlockError 抛出", True)
        expect("code == 1", e.code == 1, f"got {e.code}")

    # 场景 5: include_private 例外通道
    print("[scenario 5] include_private: QINGQIU_INCLUDE_PRIVATE=1 → 跳过 block")
    os.environ["QINGQIU_INCLUDE_PRIVATE"] = "1"
    try:
        try:
            block.check_text("身份证 11010519491231002X")
            expect("include_private 放行", True)
        except SensitiveBlockError:
            expect("include_private 放行", False, "should not raise")
    finally:
        os.environ.pop("QINGQIU_INCLUDE_PRIVATE", None)

    # 场景 6: redact_only 例外通道
    print("[scenario 6] redact_only: QINGQIU_REDACT_ONLY=1 → 跳过 block")
    os.environ["QINGQIU_REDACT_ONLY"] = "1"
    try:
        try:
            block.check_text("身份证 11010519491231002X")
            expect("redact_only 放行", True)
        except SensitiveBlockError:
            expect("redact_only 放行", False, "should not raise")
    finally:
        os.environ.pop("QINGQIU_REDACT_ONLY", None)

    # 场景 7: TTL 过期
    print("[scenario 7] include_private TTL: 过期时间戳 → 仍 block")
    os.environ["QINGQIU_INCLUDE_PRIVATE"] = "1;ts=2020-01-01T00:00:00"
    try:
        try:
            block.check_text("身份证 11010519491231002X")
            expect("TTL 过期应 block", False, "no exception raised")
        except SensitiveBlockError:
            expect("TTL 过期应 block", True)
    finally:
        os.environ.pop("QINGQIU_INCLUDE_PRIVATE", None)

    # 场景 8: 文件名命中（id_card.txt）
    print("[scenario 8] check_file: 文件名命中")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_id_card.txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("hello clean world")
        tmp_path = Path(f.name)
    try:
        r = detector.check_file(tmp_path)
        expect("filename 命中 id_card", any(
            m.match_type.value == "filename" and "id_card" in m.pattern
            for m in r.matches
        ))
    finally:
        tmp_path.unlink(missing_ok=True)

    # 场景 9: 中英文混合
    print("[scenario 9] 中文 + 英文混合识别")
    mixed = "Alice's phone is 13800138000 and 邮箱 alice@qq.com"
    r = detector.check_text(mixed)
    expect("phone + email 混合命中",
           any(m.pattern == "cn_mobile" for m in r.matches)
           and any(m.pattern == "email" for m in r.matches))

    # 场景 10: RedactHandler.redact_file
    print("[scenario 10] RedactHandler.redact_file")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("Email: alice@example.com")
        tmp_path = Path(f.name)
    try:
        redacted = redact.redact_file(tmp_path)
        expect("redact_file 返回字符串", isinstance(redacted, str))
        expect("redact_file 包含 masked", redacted is not None and "alice***@example.com" in redacted)
    finally:
        tmp_path.unlink(missing_ok=True)

    # 场景 11: 非法校验位身份证 → 退化为 bank_card
    print("[scenario 11] 非法校验位身份证 → bank_card")
    fields = detector.classify("fake id 110101199003078888")
    types = {f.type for f in fields}
    expect("无 ID_CARD", SensitiveType.ID_CARD not in types)
    expect("有 CARD", SensitiveType.CARD in types)

    # 场景 12: PrivateDetectResult 行为
    print("[scenario 12] PrivateDetectResult.has_private")
    empty = PrivateDetectResult(matches=[])
    full = PrivateDetectResult(matches=[
        # 用最小内容构造
    ])
    expect("empty.has_private=False", not empty.has_private)
    # 构建一个非空的
    from qingqiu.security.private_detect import PrivateMatch, PrivateMatchType
    full = PrivateDetectResult(matches=[
        PrivateMatch(PrivateMatchType.CONTENT_REGEX, "email", "a@b.com", "medium"),
    ])
    expect("full.has_private=True", full.has_private)
    expect("full.__len__==1", len(full) == 1)

    print()
    if failures:
        print(f"[verify] FAIL · {len(failures)} failures:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"[verify] S5.5 PASS · {passed}/N scenarios passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

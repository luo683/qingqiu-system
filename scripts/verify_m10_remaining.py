"""M10 剩余切片真跑验证脚本 · S10.2 + S10.3 + S10.5 + S10.6

Run: uv run python scripts/verify_m10_remaining.py

4 个验收场景（来自 task_prompt_M10_remaining.json §verify_scenarios）：
- M10-8:  用户说 '不写 emoji' → personality.yaml system_prompt 追加 '不写 emoji'
- M10-9:  vault feed → 抓所有 tag → 写入 L2 'auto_concepts: tag1,tag2,...'
- M10-10: 同一 preference 多次不同值 → 触发 conflict (记录到 L3)
- M10-11: growth.enabled=False → 所有 growth 函数返 None/empty

每个场景独立隔离（用 tmp_path / 临时 db），不会污染 ~/.qingqiu/memory/ 和
~/.qingqiu/personality.yaml。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# 让 src/ 可 import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> int:
    # 清除外部 env var，避免污染场景
    os.environ.pop("QINGQIU_GROWTH_ENABLED", None)

    from qingqiu.growth.conflict import ConflictDetector
    from qingqiu.growth.config import GrowthConfig
    from qingqiu.growth.preference import PreferenceLearner
    from qingqiu.growth.vault_feed import VaultFeeder
    from qingqiu.memory.l2 import L2UserMemory
    from qingqiu.memory.l3 import L3FactsMemory
    import yaml

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

    print("[verify] M10 剩余切片 · S10.2 + S10.3 + S10.5 + S10.6")
    print()

    # ── 场景 1: M10-8 preference learn ─────────────────
    print("[scenario 1] M10-8: 用户说 '不写 emoji' → personality.yaml system_prompt 追加 '不写 emoji'")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        personality_path = tmp_path / "personality.yaml"
        # 预存一份初始 personality
        personality_path.write_text(
            yaml.safe_dump(
                {
                    "name": "清秋",
                    "tone": "neutral",
                    "language": "zh-CN",
                    "system_prompt": "你是清秋，给 ROG 个人使用。\n风格：简洁、直接。",
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        gc = GrowthConfig(enabled=True)
        learner = PreferenceLearner(path=personality_path, growth=gc)

        result = learner.learn("不写 emoji")
        expect("learn() 返非空 prompt", result is not None)
        if result is not None:
            expect("prompt 含 '不写 emoji'", "不写 emoji" in result)
            expect("prompt 含 bullet 风格", "- 不写 emoji" in result)
            expect("prompt 保留原内容", "你是清秋" in result)

        # 重新读磁盘确认
        data = yaml.safe_load(personality_path.read_text(encoding="utf-8"))
        expect(
            "personality.yaml 持久化 '不写 emoji'",
            "不写 emoji" in str(data.get("system_prompt", "")),
            f"got {data}",
        )

        # 幂等：再学一次不重复
        learner.learn("不写 emoji")
        data2 = yaml.safe_load(personality_path.read_text(encoding="utf-8"))
        expect(
            "幂等：重复 learn 不重复追加",
            str(data2.get("system_prompt", "")).count("不写 emoji") == 1,
        )

        # 多 preference 累积
        learner.learn("回复简短")
        data3 = yaml.safe_load(personality_path.read_text(encoding="utf-8"))
        expect("第二条 preference '回复简短' 累积", "回复简短" in str(data3.get("system_prompt", "")))
    print()

    # ── 场景 2: M10-9 vault feed ─────────────────
    print("[scenario 2] M10-9: vault feed → 抓所有 tag → 写入 L2 'auto_concepts'")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        vault_root = tmp_path / "vault"
        vault_root.mkdir()

        # 准备 vault 内容：frontmatter + 正文 #tag
        (vault_root / "a.md").write_text(
            "---\ntags: [python, fastapi]\n---\n这是笔记 #python",
            encoding="utf-8",
        )
        (vault_root / "b.md").write_text(
            "---\ntags: [python, arch]\n---\n正文提到 #fastapi 和 #mvp",
            encoding="utf-8",
        )
        (vault_root / "sub").mkdir()
        (vault_root / "sub" / "c.md").write_text(
            "#security 隐私处理 #python",
            encoding="utf-8",
        )

        l2_path = tmp_path / "user.md"
        l2 = L2UserMemory(l2_path)
        gc = GrowthConfig(enabled=True)
        feeder = VaultFeeder(l2=l2, growth=gc)

        result = feeder.feed(vault_root)
        expect("feed() 返非空", result is not None)
        if result is not None:
            # 排序后写入：arch, fastapi, mvp, python, security
            expect("结果按字母排序", result == "arch,fastapi,mvp,python,security", f"got {result!r}")
            expect("含 'python'", "python" in result)
            expect("含 'fastapi'", "fastapi" in result)
            expect("含 'arch'", "arch" in result)
            expect("含 'mvp'", "mvp" in result)
            expect("含 'security' (from inline #tag)", "security" in result)

        # L2 持久化
        expect(
            "L2 写入 auto_concepts",
            l2.get("auto_concepts") == result,
        )
    print()

    # ── 场景 3: M10-10 conflict ─────────────────
    print("[scenario 3] M10-10: 同一 preference 多次不同值 → 触发 conflict (L3)")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        l3 = L3FactsMemory(tmp_path / "facts.sqlite")
        gc = GrowthConfig(enabled=True)
        detector = ConflictDetector(l3=l3, growth=gc)

        history = [
            ("emoji", "no"),
            ("emoji", "yes"),  # 触发 conflict
            ("tone", "formal"),
            ("tone", "casual"),  # 触发 conflict
            ("lang", "zh"),  # 单次 → 无冲突
        ]
        conflicts = detector.detect(history)
        expect("返回 2 个冲突 (emoji + tone)", len(conflicts) == 2, f"got {len(conflicts)}")

        # L3 写入验证
        expect("L3 conflict_emoji = no→yes", l3.get("conflict_emoji") == "no→yes")
        expect("L3 conflict_tone = formal→casual", l3.get("conflict_tone") == "formal→casual")
        expect("L3 无 conflict_lang (单值无冲突)", l3.get("conflict_lang") is None)

        # 返回结构
        keys = sorted(c["key"] for c in conflicts)
        expect("冲突 keys = [emoji, tone]", keys == ["emoji", "tone"])
        first = conflicts[0]
        expect("冲突项含 key/old/new/conflict_key", all(
            k in first for k in ("key", "old", "new", "conflict_key", "detected_at")
        ))
        expect("conflict_key 格式 = conflict_<key>", first["conflict_key"].startswith("conflict_"))
    print()

    # ── 场景 4: M10-11 growth.enabled=False ─────────────────
    print("[scenario 4] M10-11: growth.enabled=False → 所有 growth 函数返 None/empty")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir)
        personality_path = tmp_path / "personality.yaml"
        personality_path.write_text("system_prompt: 原 prompt\n", encoding="utf-8")
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        (vault_root / "a.md").write_text("---\ntags: [python]\n---", encoding="utf-8")

        l2 = L2UserMemory(tmp_path / "user.md")
        l3 = L3FactsMemory(tmp_path / "facts.sqlite")
        gc_disabled = GrowthConfig(enabled=False)

        # PreferenceLearner
        learner = PreferenceLearner(path=personality_path, growth=gc_disabled)
        result_pref = learner.learn("不写 emoji")
        expect("PreferenceLearner.learn() 返 None", result_pref is None)
        # 文件不应被修改
        expect(
            "personality.yaml 未被修改",
            personality_path.read_text(encoding="utf-8") == "system_prompt: 原 prompt\n",
        )

        # VaultFeeder
        feeder = VaultFeeder(l2=l2, growth=gc_disabled)
        result_vault = feeder.feed(vault_root)
        expect("VaultFeeder.feed() 返 None", result_vault is None)
        expect("L2 未被写入", l2.get("auto_concepts") is None)

        # ConflictDetector
        detector = ConflictDetector(l3=l3, growth=gc_disabled)
        result_conflict = detector.detect([("emoji", "no"), ("emoji", "yes")])
        expect("ConflictDetector.detect() 返 []", result_conflict == [])
        expect("L3 未被写入 conflict_*", l3.get("conflict_emoji") is None)

        # is_enabled() 一致性
        expect("PreferenceLearner.is_enabled() = False", learner.is_enabled() is False)
        expect("VaultFeeder.is_enabled() = False", feeder.is_enabled() is False)
        expect("ConflictDetector.is_enabled() = False", detector.is_enabled() is False)
    print()

    # ── 总结 ──────────────────────────────────────
    if failures:
        print(f"[verify] FAIL · {len(failures)} failures:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"[verify] M10 remaining PASS · {passed} assertions across 4 scenarios")
    return 0


if __name__ == "__main__":
    sys.exit(main())

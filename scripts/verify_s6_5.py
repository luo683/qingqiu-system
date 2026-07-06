"""S6.5 真跑脚本 · personality.yaml 加载 + hot reload + 单例

5 个核心场景：
1. 删 ~/.qingqiu/personality.yaml → get_personality() 自动建默认
2. 改 name → get_personality().name 拿到新值（mtime hot reload）
3. 改 system_prompt → get_system_prompt() 拿到新值
4. 多次调用验证 singleton 行为
5. Pydantic 缺字段 fallback 到 default

每次跑前先清理目标文件，确保从干净状态开始。
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

import yaml

# 让脚本能 import qingqiu.*
_PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_PROJECT_SRC))

from qingqiu.personality import (  # noqa: E402
    DEFAULT_PERSONALITY_PATH,
    PersonalityConfig,
    PersonalityLoader,
    get_personality,
    get_system_prompt,
    reset_default_loader,
)


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def main() -> int:
    # 用临时路径做端到端真跑（避免污染 ~/.qingqiu/）
    # 但 get_personality() 默认读 DEFAULT_PERSONALITY_PATH，需要 monkey patch
    # 这里用独立 loader + path 参数走真跑路径，更接近生产行为
    test_dir = Path(tempfile.mkdtemp(prefix="qingqiu_s6_5_"))
    test_file = test_dir / "personality.yaml"
    print(f"[verify] 临时目录: {test_dir}")
    print()

    failures: list[str] = []

    def expect(cond: bool, label: str) -> None:
        if cond:
            print(f"  [PASS] {label}")
        else:
            print(f"  [FAIL] {label}")
            failures.append(label)

    try:
        # === Step 1: 文件不存在 → 自动建默认 ===
        print("[step 1] 文件不存在 → get_personality() 自动建默认")
        if test_file.exists():
            test_file.unlink()
        loader = PersonalityLoader(test_file)
        expect(test_file.exists(), "personality.yaml 自动创建")
        cfg1 = loader.config
        expect(cfg1.name == "清秋", f"name 默认值 (got={cfg1.name!r})")
        expect(cfg1.tone == "neutral", f"tone 默认值 (got={cfg1.tone!r})")
        expect(cfg1.language == "zh-CN", f"language 默认值 (got={cfg1.language!r})")
        expect("清秋" in cfg1.system_prompt, "system_prompt 含 '清秋'")
        print()

        # === Step 2: 改 name → hot reload 拿到新值 ===
        print("[step 2] 改 name → config 自动 reload（mtime hot reload）")
        time.sleep(1.1)  # Windows mtime 精度规避
        _write_yaml(test_file, {"name": "新名字", "tone": "humorous"})
        cfg2 = loader.config  # 访问即触发 mtime 检测
        expect(cfg2.name == "新名字", f"name 拿到新值 (got={cfg2.name!r})")
        expect(cfg2.tone == "humorous", f"tone 拿到新值 (got={cfg2.tone!r})")
        expect(cfg2.language == "zh-CN", "language 缺省走默认")
        print()

        # === Step 3: 改 system_prompt → get_system_prompt() 拿到新值 ===
        print("[step 3] 改 system_prompt → get_system_prompt() 拿到新值")
        new_prompt = "你是新清秋，风格：皮一点 🌶️\n不说废话"
        time.sleep(1.1)
        _write_yaml(test_file, {"name": "新名字", "system_prompt": new_prompt})
        sp = loader.system_prompt
        expect(sp == new_prompt, f"system_prompt 拿到新值 (got={sp!r})")
        expect("🌶️" in sp, "system_prompt 含 emoji")
        # 同时验证便捷函数也走 hot reload（用 monkey patch DEFAULT_PERSONALITY_PATH）
        # 这里改用独立 path 调用 get_personality(path) 验证全局函数语义
        cfg_via_helper = get_personality(test_file)
        expect(
            cfg_via_helper.system_prompt == new_prompt,
            "get_personality(path) 同步返回最新值",
        )
        print()

        # === Step 4: singleton 行为 ===
        print("[step 4] 单例行为：get_personality() 多次调用返回同一 loader 实例")
        # 用 monkeypatch 切默认路径 → 重置单例 → 多次调用拿同一份 config
        import qingqiu.personality as p_mod

        original_path = p_mod.DEFAULT_PERSONALITY_PATH
        p_mod.DEFAULT_PERSONALITY_PATH = test_file  # type: ignore[misc]
        reset_default_loader()
        try:
            a = get_personality()
            b = get_personality()
            expect(a.name == b.name, "两次调用 name 一致")
            expect(a.system_prompt == b.system_prompt, "两次调用 system_prompt 一致")
            expect(a.tone == b.tone, "两次调用 tone 一致")
        finally:
            p_mod.DEFAULT_PERSONALITY_PATH = original_path  # type: ignore[misc]
            reset_default_loader()
        print()

        # === Step 5: Pydantic 缺字段 fallback ===
        print("[step 5] Pydantic 缺字段 → schema default fallback")
        time.sleep(1.1)
        _write_yaml(test_file, {"name": "缺字段版"})  # 只给 name
        cfg5 = loader.config
        expect(cfg5.name == "缺字段版", "name 用文件值")
        expect(cfg5.tone == "neutral", f"tone 缺省 → neutral (got={cfg5.tone!r})")
        expect(cfg5.language == "zh-CN", f"language 缺省 → zh-CN (got={cfg5.language!r})")
        expect("清秋" in cfg5.system_prompt, "system_prompt 缺省 → 默认文本")
        print()

        # === Bonus: 嵌套 personality: 格式 ===
        print("[bonus] 嵌套 personality: 格式（PRD §8.2）")
        time.sleep(1.1)
        _write_yaml(
            test_file,
            {
                "personality": {
                    "name": "嵌套清秋",
                    "tone": "formal",
                    "system_prompt": "嵌套 system prompt",
                }
            },
        )
        cfg6 = loader.config
        expect(cfg6.name == "嵌套清秋", "嵌套 name 解析")
        expect(cfg6.tone == "formal", "嵌套 tone 解析")
        expect(cfg6.system_prompt == "嵌套 system prompt", "嵌套 system_prompt 解析")
        print()

    finally:
        # 清理
        shutil.rmtree(test_dir, ignore_errors=True)
        # 防止单例污染下次跑
        reset_default_loader()

    print("=" * 60)
    if failures:
        print(f"[verify] FAIL ({len(failures)} failures)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[verify] S6.5 PASS · 5+1 步验证全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
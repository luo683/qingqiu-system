"""S2.2 真跑验证脚本 · Router 意图识别"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def main() -> int:
    from qingqiu.router import (
        ClassificationResult,
        Intent,
        IntentClassifier,
        RuleBasedClassifier,
    )

    failures = []
    print("[verify] S2.2 Router 意图识别真跑验证")
    print()

    # 10 指令真跑集（IMPLEMENTATION-PLAN §82 验收）
    TEST_CASES = [
        # (input, expected_intent, description)
        ("memory get user_name", Intent.MEMORY_GET, "memory get"),
        ("memory set user_name ROG", Intent.MEMORY_SET, "memory set"),
        ("memory list", Intent.MEMORY_LIST, "memory list"),
        ("memory delete foo", Intent.MEMORY_DELETE, "memory delete"),
        ("add a task: 修 S2.2", Intent.TASK_ADD, "task add English"),
        ("show task list", Intent.TASK_LIST, "task list English"),
        ("status", Intent.STATUS, "status"),
        ("config show", Intent.CONFIG_SHOW, "config show"),
        ("完成 t-abc12345", Intent.TASK_DONE, "task done Chinese"),
        ("新建任务 写文档", Intent.TASK_ADD, "task add Chinese"),
    ]

    print("[verify] 10 指令规则识别（rule only）")
    rule_classifier = RuleBasedClassifier()
    rule_matched = 0
    for text, expected, desc in TEST_CASES:
        r = rule_classifier.classify(text)
        if r is not None and r.intent == expected:
            print(f"  [PASS] {desc}: {text!r} -> {r.intent.value}")
            rule_matched += 1
        else:
            actual = r.intent.value if r else "None"
            print(f"  [FAIL] {desc}: {text!r} -> {actual} (expected {expected.value})")
            failures.append(f"rule_{desc}")
    print(f"  -> {rule_matched}/10 matched")
    print()

    # 场景 2: IntentClassifier 主类（无 LLM）
    print("[verify] IntentClassifier 主类（无 LLM · 规则 + fallback）")
    c = IntentClassifier(llm_provider=None, use_llm=False)
    classifier_matched = 0
    for text, expected, desc in TEST_CASES:
        r = c.classify(text)
        if r.intent == expected:
            classifier_matched += 1
    print(f"  -> {classifier_matched}/10 matched")
    if classifier_matched < 7:
        failures.append(f"classifier_main < 7/10 ({classifier_matched}/10)")
    print()

    # 场景 3: 无规则命中时 fallback 到 UNKNOWN
    print("[verify] 无规则命中 → UNKNOWN fallback")
    c = IntentClassifier(llm_provider=None, use_llm=False)
    r = c.classify("xyz abc def ghi")
    if r.intent == Intent.UNKNOWN and r.source == "fallback":
        print("  [PASS] fallback OK")
    else:
        print(f"  [FAIL] got {r.intent} / {r.source}")
        failures.append("fallback")
    print()

    # 场景 4: 中文 + 英文混合（lookbehind/ahead 验证）
    print("[verify] 中文 + 英文 lookbehind 边界")
    c = IntentClassifier(llm_provider=None, use_llm=False)
    cases = [
        ("新建任务 测试", Intent.TASK_ADD),
        ("看任务", Intent.TASK_LIST),  # 单纯"看任务"应匹配 task_list（不加"状态"避免 status_keyword 抢匹配）
        ("memory 测试 set", Intent.MEMORY_SET),
    ]
    for text, expected in cases:
        r = c.classify(text)
        status = "[PASS]" if r.intent == expected else "[FAIL]"
        print(f"  {status} {text!r} -> {r.intent.value} (expected {expected.value})")
        if r.intent != expected:
            failures.append(f"chinese_eng_mix_{text!r}")
    print()

    # 场景 5: Intent.from_str 容错
    print("[verify] Intent.from_str 容错")
    from qingqiu.router.intent import Intent
    tests = [
        ("ask", Intent.ASK),
        ("ASK", Intent.ASK),
        ("task_add", Intent.TASK_ADD),
        ("unknown", Intent.UNKNOWN),
        ("invalid", Intent.UNKNOWN),
        ("", Intent.UNKNOWN),
    ]
    for s, expected in tests:
        result = Intent.from_str(s)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"  {status} from_str({s!r}) -> {result.value}")
        if result != expected:
            failures.append(f"from_str_{s!r}")
    print()

    # 场景 6: Intent.cli_subcommand 映射
    print("[verify] Intent -> CLI 映射")
    mappings = [
        (Intent.TASK_ADD, ("task", "add")),
        (Intent.MEMORY_GET, ("memory", "get")),
        (Intent.ASK, ("ask", None)),
        (Intent.STATUS, ("status", None)),
    ]
    for intent, expected in mappings:
        result = intent.cli_subcommand
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"  {status} {intent.value} -> {result}")
        if result != expected:
            failures.append(f"cli_mapping_{intent.value}")
    print()

    # 场景 7: Confidence 字段
    print("[verify] ClassificationResult 字段")
    c = IntentClassifier(llm_provider=None, use_llm=False)
    r = c.classify("memory get foo")
    if r.intent == Intent.MEMORY_GET and r.confidence == 1.0 and r.source == "rule":
        print(f"  [PASS] {r}")
    else:
        print(f"  [FAIL] {r}")
        failures.append("classification_fields")
    print()

    # 场景 8: LLM JSON 解析（mock LLM）
    print("[verify] LLM JSON 解析（mock LLM）")
    from qingqiu.llm import LLMResponse

    class MockLLM:
        def __init__(self, content):
            self._content = content

        async def complete(self, messages, **kwargs):
            return LLMResponse(
                content=self._content,
                model="mock",
                usage={"input_tokens": 0, "output_tokens": 0},
            )

    # Test 1: clean JSON
    c = IntentClassifier(llm_provider=MockLLM('{"intent": "task_add", "confidence": 0.9, "reason": "test"}'), use_llm=True)
    r = c.classify("xyz unknown text")
    if r.intent == Intent.TASK_ADD and r.source == "llm":
        print(f"  [PASS] clean JSON parsed: {r.intent.value}")
    else:
        print(f"  [FAIL] got {r.intent} / {r.source}")
        failures.append("llm_clean_json")

    # Test 2: markdown fenced
    c = IntentClassifier(llm_provider=MockLLM('```json\n{"intent": "status", "confidence": 0.85}\n```'), use_llm=True)
    r = c.classify("xyz unknown text")
    if r.intent == Intent.STATUS:
        print(f"  [PASS] markdown fenced JSON parsed: {r.intent.value}")
    else:
        print(f"  [FAIL] got {r.intent}")
        failures.append("llm_markdown_fenced")

    # Test 3: invalid JSON
    c = IntentClassifier(llm_provider=MockLLM("not json"), use_llm=True)
    r = c.classify("xyz unknown text")
    if r.intent == Intent.UNKNOWN and r.source == "fallback":
        print(f"  [PASS] invalid JSON -> fallback: {r.intent.value}")
    else:
        print(f"  [FAIL] got {r.intent} / {r.source}")
        failures.append("llm_invalid_json")

    # Test 4: provider exception
    class FailingLLM:
        async def complete(self, *args, **kwargs):
            raise RuntimeError("network error")

    c = IntentClassifier(llm_provider=FailingLLM(), use_llm=True)
    r = c.classify("xyz unknown text")
    if r.intent == Intent.UNKNOWN and r.source == "fallback":
        print(f"  [PASS] provider exception -> fallback")
    else:
        print(f"  [FAIL] got {r.intent} / {r.source}")
        failures.append("llm_exception")
    print()

    # 场景 9: 空输入
    print("[verify] 空输入")
    c = IntentClassifier(llm_provider=None, use_llm=False)
    for empty in ["", "   ", None]:
        try:
            if empty is None:
                continue
            r = c.classify(empty)
            if r.intent == Intent.UNKNOWN and r.confidence == 0.0:
                print(f"  [PASS] classify({empty!r}) -> UNKNOWN")
            else:
                print(f"  [FAIL] got {r}")
                failures.append(f"empty_{empty!r}")
        except Exception as e:
            print(f"  [FAIL] raised: {e}")
            failures.append(f"empty_{empty!r}")
    print()

    # 场景 10: use_llm=False 不调 LLM
    print("[verify] use_llm=False 不调 LLM")
    class CalledLLM:
        def __init__(self):
            self.called = False

        async def complete(self, *args, **kwargs):
            self.called = True
            return None

    provider = CalledLLM()
    c = IntentClassifier(llm_provider=provider, use_llm=False)
    r = c.classify("xyz unknown text")
    if not provider.called:
        print(f"  [PASS] LLM not called, got {r.intent.value}")
    else:
        print(f"  [FAIL] LLM was called")
        failures.append("use_llm_false")
    print()

    # 收尾
    print("=" * 60)
    if failures:
        print(f"[verify] FAIL ({len(failures)} failures):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[verify] S2.2 PASS · 10 场景全过（10 指令 + 边界 + 容错 + LLM mock）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
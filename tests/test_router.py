"""S2.2 测试 · Router 意图识别"""

import pytest

from qingqiu.router import (
    ClassificationResult,
    Intent,
    IntentClassifier,
    LLMClassifier,
    RuleBasedClassifier,
)


# === Intent 枚举 ===

def test_intent_values():
    """Intent 枚举值"""
    assert Intent.ASK.value == "ask"
    assert Intent.TASK_ADD.value == "task_add"
    assert Intent.MEMORY_SET.value == "memory_set"


def test_intent_from_str():
    """字符串解析"""
    assert Intent.from_str("ask") == Intent.ASK
    assert Intent.from_str("ASK") == Intent.ASK
    assert Intent.from_str("invalid") == Intent.UNKNOWN
    assert Intent.from_str("") == Intent.UNKNOWN


def test_intent_cli_mapping():
    """Intent → CLI 映射"""
    assert Intent.TASK_ADD.cli_subcommand == ("task", "add")
    assert Intent.MEMORY_GET.cli_subcommand == ("memory", "get")
    assert Intent.ASK.cli_subcommand == ("ask", None)


# === RuleBasedClassifier ===

def test_rule_task_add():
    """task add 规则命中"""
    r = RuleBasedClassifier().classify("add a task: 修 bug")
    assert r is not None
    assert r.intent == Intent.TASK_ADD
    assert r.source == "rule"
    assert r.confidence == 1.0


def test_rule_task_add_chinese():
    r = RuleBasedClassifier().classify("新建任务 写文档")
    assert r is not None
    assert r.intent == Intent.TASK_ADD


def test_rule_task_list():
    r = RuleBasedClassifier().classify("show task list")
    assert r is not None
    assert r.intent == Intent.TASK_LIST


def test_rule_task_list_chinese():
    r = RuleBasedClassifier().classify("看任务列表")
    assert r is not None
    assert r.intent == Intent.TASK_LIST


def test_rule_task_done():
    r = RuleBasedClassifier().classify("完成 t-abc12345")
    assert r is not None
    assert r.intent == Intent.TASK_DONE


def test_rule_memory_get():
    r = RuleBasedClassifier().classify("memory get user_name")
    assert r is not None
    assert r.intent == Intent.MEMORY_GET


def test_rule_memory_set():
    r = RuleBasedClassifier().classify("memory set user_name ROG")
    assert r is not None
    assert r.intent == Intent.MEMORY_SET


def test_rule_memory_list():
    r = RuleBasedClassifier().classify("memory list")
    assert r is not None
    assert r.intent == Intent.MEMORY_LIST


def test_rule_status():
    r = RuleBasedClassifier().classify("status")
    assert r is not None
    assert r.intent == Intent.STATUS


def test_rule_config_show():
    r = RuleBasedClassifier().classify("config show")
    assert r is not None
    assert r.intent == Intent.CONFIG_SHOW


def test_rule_no_match():
    """无规则命中返回 None"""
    r = RuleBasedClassifier().classify("hello world")
    assert r is None


def test_rule_empty():
    r = RuleBasedClassifier().classify("")
    assert r is None


# === IntentClassifier 主类（无 LLM） ===

def test_classifier_rule_only():
    """无 LLM 时只用规则"""
    c = IntentClassifier(llm_provider=None, use_llm=False)
    r = c.classify("memory get user_name")
    assert r.intent == Intent.MEMORY_GET
    assert r.source == "rule"


def test_classifier_fallback_when_no_match():
    """无规则无 LLM → UNKNOWN"""
    c = IntentClassifier(llm_provider=None, use_llm=False)
    r = c.classify("xyz abc def")
    assert r.intent == Intent.UNKNOWN
    assert r.source == "fallback"


def test_classifier_empty_input():
    c = IntentClassifier(llm_provider=None, use_llm=False)
    r = c.classify("")
    assert r.intent == Intent.UNKNOWN
    assert r.confidence == 0.0


# === LLM 解析（mock LLM provider） ===

class MockLLMProvider:
    """Mock LLM provider 返回预设 JSON"""

    def __init__(self, response: str = ""):
        self._response = response

    async def complete(self, messages, **kwargs):
        from qingqiu.llm import LLMResponse
        return LLMResponse(
            content=self._response,
            model="mock",
            usage={"input_tokens": 0, "output_tokens": 0},
        )


def test_llm_classifier_parses_clean_json():
    """LLM 返回纯 JSON"""
    mock = MockLLMProvider('{"intent": "task_add", "confidence": 0.9, "reason": "user wants to add a task"}')
    c = LLMClassifier(llm_provider=mock)
    r = c.classify("I want to add a task to buy groceries")
    assert r is not None
    assert r.intent == Intent.TASK_ADD
    assert r.confidence == 0.9
    assert r.source == "llm"


def test_llm_classifier_parses_markdown_fenced_json():
    """LLM 返回 markdown fence 包裹的 JSON"""
    mock = MockLLMProvider('```json\n{"intent": "memory_get", "confidence": 0.8, "reason": "asking for memory"}\n```')
    c = LLMClassifier(llm_provider=mock)
    r = c.classify("what's my username")
    assert r is not None
    assert r.intent == Intent.MEMORY_GET


def test_llm_classifier_parses_unknown_intent():
    """LLM 返回 unknown"""
    mock = MockLLMProvider('{"intent": "unknown", "confidence": 0.3, "reason": "gibberish"}')
    c = LLMClassifier(llm_provider=mock)
    r = c.classify("asdfghjkl")
    assert r.intent == Intent.UNKNOWN


def test_llm_classifier_invalid_json_returns_none():
    """LLM 返回非 JSON → None"""
    mock = MockLLMProvider("I cannot classify this")
    c = LLMClassifier(llm_provider=mock)
    r = c.classify("asdf")
    assert r is None


def test_llm_classifier_provider_exception_returns_none():
    """LLM provider 抛异常 → None"""
    class FailingProvider:
        async def complete(self, *args, **kwargs):
            raise RuntimeError("LLM down")

    c = LLMClassifier(llm_provider=FailingProvider())
    r = c.classify("anything")
    assert r is None


# === IntentClassifier with mock LLM ===

def test_classifier_rule_match_skips_llm():
    """规则命中跳过 LLM"""
    mock = MockLLMProvider('{"intent": "task_add"}')  # 如果调用会返回 task_add
    c = IntentClassifier(llm_provider=mock, use_llm=True)
    r = c.classify("add a task: 修 bug")
    assert r.intent == Intent.TASK_ADD
    assert r.source == "rule"  # 不是 llm


def test_classifier_falls_back_to_llm_on_no_rule():
    """无规则命中 → 调 LLM"""
    mock = MockLLMProvider('{"intent": "status", "confidence": 0.7}')
    c = IntentClassifier(llm_provider=mock, use_llm=True)
    r = c.classify("how are things going")
    assert r.intent == Intent.STATUS
    assert r.source == "llm"


def test_classifier_fallback_when_llm_fails():
    """LLM 失败 → UNKNOWN fallback"""
    class FailingProvider:
        async def complete(self, *args, **kwargs):
            raise RuntimeError("network")

    c = IntentClassifier(llm_provider=FailingProvider(), use_llm=True)
    r = c.classify("something unrecognized")
    assert r.intent == Intent.UNKNOWN
    assert r.source == "fallback"


# === 10 指令真跑验证集（IMPLEMENTATION-PLAN §82 验收） ===

INTENT_TEST_CASES = [
    # (input, expected_intent)
    ("memory get user_name", Intent.MEMORY_GET),
    ("memory set user_name ROG", Intent.MEMORY_SET),
    ("memory list", Intent.MEMORY_LIST),
    ("memory delete foo", Intent.MEMORY_DELETE),
    ("add a task: 修 S2.2", Intent.TASK_ADD),
    ("show task list", Intent.TASK_LIST),
    ("status", Intent.STATUS),
    ("config show", Intent.CONFIG_SHOW),
    ("完成 t-abc12345", Intent.TASK_DONE),
    ("新建任务 写文档", Intent.TASK_ADD),
]


def test_10_intent_recognition_rule_only():
    """10 指令规则识别率（rule only）"""
    c = IntentClassifier(llm_provider=None, use_llm=False)
    matched = 0
    for text, expected in INTENT_TEST_CASES:
        r = c.classify(text)
        if r.intent == expected:
            matched += 1
    # 规则能识别大部分；测试至少有 7/10 = 70% 识别率
    assert matched >= 7, f"only {matched}/10 matched by rule"


def test_10_intent_recognition_with_llm_mock():
    """10 指令 LLM 识别（mock LLM 返回正确）"""
    # 这里我们 mock LLM 让它按预期返回
    class PerTextMockProvider:
        def __init__(self):
            self.calls = []

        async def complete(self, messages, **kwargs):
            from qingqiu.llm import LLMResponse
            user_msg = messages[0].content if messages else ""
            # 简单关键字匹配返回对应 intent
            intent_map = {
                "memory get": "memory_get",
                "memory set": "memory_set",
                "memory list": "memory_list",
                "memory delete": "memory_delete",
                "add a task": "task_add",
                "show task list": "task_list",
                "status": "status",
                "config show": "config_show",
                "完成": "task_done",
                "新建任务": "task_add",
            }
            for keyword, intent in intent_map.items():
                if keyword in user_msg:
                    return LLMResponse(
                        content=f'{{"intent": "{intent}", "confidence": 0.85, "reason": "matched {keyword}"}}',
                        model="mock",
                        usage={"input_tokens": 0, "output_tokens": 0},
                    )
            return LLMResponse(
                content='{"intent": "unknown", "confidence": 0.3}',
                model="mock",
                usage={"input_tokens": 0, "output_tokens": 0},
            )

    c = IntentClassifier(llm_provider=PerTextMockProvider(), use_llm=True)
    matched = 0
    for text, expected in INTENT_TEST_CASES:
        r = c.classify(text)
        if r.intent == expected:
            matched += 1
    # LLM 应该全部识别
    assert matched == 10, f"LLM mock: {matched}/10 matched"
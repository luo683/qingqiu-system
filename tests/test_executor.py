"""test_executor.py · S2.4 Executor 测试

测试 Executor 端到端：raw_text → Intent → 实体提取 → CLI handler 调用
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from qingqiu.cli.output import OutputFormatter
from qingqiu.cli.task import TaskStore
from qingqiu.router.executor import Executor
from qingqiu.router.intent import Intent


@pytest.fixture
def tmp_task_store(monkeypatch):
    """monkeypatch TaskStore 使用 tmp_path（避免污染 ~/.qingqiu/tasks.json）"""
    tmp = Path(tempfile.mkdtemp())
    original_init = TaskStore.__init__

    def patched_init(self, path=None):
        target = path or (tmp / "tasks.json")
        original_init(self, path=target)

    monkeypatch.setattr(TaskStore, "__init__", patched_init)
    return tmp


@pytest.fixture
def out() -> OutputFormatter:
    return OutputFormatter(json_mode=True, no_color=True)


@pytest.fixture
def tmp_mem(tmp_path: Path):
    """每个 test 用独立 memory dir 避免污染"""
    return tmp_path


@pytest.fixture
def executor(tmp_mem):
    """Executor + 临时 memory dir"""
    return Executor(llm_provider=None, use_llm=False)


# === 分类 + 实体提取 ===

def test_executor_classify_memory_get(executor):
    result = executor._classifier.classify("memory get user_name")
    assert result.intent == Intent.MEMORY_GET
    assert result.source == "rule"


def test_executor_classify_memory_set(executor):
    result = executor._classifier.classify("memory set user_name ROG")
    assert result.intent == Intent.MEMORY_SET


def test_executor_classify_task_add_chinese(executor):
    result = executor._classifier.classify("新建任务 写文档")
    assert result.intent == Intent.TASK_ADD


def test_executor_classify_task_list_chinese(executor):
    result = executor._classifier.classify("看任务")
    assert result.intent == Intent.TASK_LIST


def test_executor_classify_status(executor):
    result = executor._classifier.classify("status")
    assert result.intent == Intent.STATUS


# === 实体提取 ===

def test_extract_memory_get_key(executor):
    e = executor._extract_entities(Intent.MEMORY_GET, "memory get user_name")
    assert e["key"] == "user_name"


def test_extract_memory_set_key_value(executor):
    e = executor._extract_entities(
        Intent.MEMORY_SET, "memory set user_name ROG"
    )
    assert e["key"] == "user_name"
    assert e["value"] == "ROG"


def test_extract_task_add_title_chinese(executor):
    e = executor._extract_entities(Intent.TASK_ADD, "新建任务 修 S2.4 bug")
    assert "修" in e["description"][0]


def test_extract_task_add_title_english(executor):
    e = executor._extract_entities(Intent.TASK_ADD, "task add 写文档")
    assert "写文档" in e["description"][0]


def test_extract_task_done_id(executor):
    e = executor._extract_entities(Intent.TASK_DONE, "完成 t-abc12345")
    assert e["id"] == "t-abc12345"


# === 端到端：执行 memory get/set/list ===

def test_executor_memory_set_then_get(executor, out):
    rc1 = executor.execute("memory set user_name ROG", out)
    assert rc1 == 0
    rc2 = executor.execute("memory get user_name", out)
    assert rc2 == 0


def test_executor_memory_list(executor, out):
    executor.execute("memory set k1 v1", out)
    executor.execute("memory set k2 v2", out)
    rc = executor.execute("memory list", out)
    assert rc == 0


def test_executor_memory_delete(executor, out):
    executor.execute("memory set k1 v1", out)
    rc = executor.execute("memory delete k1", out)
    assert rc == 0


# === 端到端：执行 task add/list/done ===

def test_executor_task_add_then_list(executor, out):
    rc1 = executor.execute("新建任务 写文档", out)
    assert rc1 == 0
    rc2 = executor.execute("看任务", out)
    assert rc2 == 0


def test_executor_task_done(executor, out, tmp_task_store):
    """端到端 task add → done（用 tmp_task_store 隔离）"""
    rc1 = executor.execute("新建任务 写文档", out)
    assert rc1 == 0
    # 拿 ID
    store1 = TaskStore()
    tasks = store1.list()
    assert tasks, "expected at least one task"
    tid = tasks[0]["id"]
    rc2 = executor.execute(f"完成 {tid}", out)
    assert rc2 == 0
    # 重新 load 确认 done
    store2 = TaskStore()
    tasks_after = store2.list()
    assert tasks_after[0]["status"] == "done", f"task {tid} not done: {tasks_after}"


def test_executor_task_done_via_chinese(executor, out, tmp_task_store):
    """`完成 t-xxx` 中文触发 task_done"""
    rc1 = executor.execute("新建任务 写文档", out)
    assert rc1 == 0
    store = TaskStore()
    tid = store.list()[0]["id"]
    rc2 = executor.execute(f"完成 {tid}", out)
    assert rc2 == 0


# === UNKNOWN / 错误处理 ===

def test_executor_unknown_text(executor, out):
    rc = executor.execute("随便说点不知道什么", out)
    # UNKNOWN 路径返 1 但不抛异常
    assert rc == 1


def test_executor_missing_required_entity(executor, out):
    # memory get 没 key → 抛 ValueError → 返 1
    rc = executor.execute("memory get", out)
    assert rc == 1


# === run_ask 入口 ===

def test_run_ask_calls_executor():
    from qingqiu.router.executor import run_ask

    class A:
        prompt = ["memory", "set", "user_name", "ROG"]

    out = OutputFormatter(json_mode=True, no_color=True)
    rc = run_ask(A(), out, llm_provider=None)
    assert rc == 0


def test_run_ask_empty_prompt():
    from qingqiu.router.executor import run_ask

    class A:
        prompt = []

    out = OutputFormatter(json_mode=True, no_color=True)
    rc = run_ask(A(), out, llm_provider=None)
    assert rc == 1


# === handler 路由表 ===

def test_handler_table_completeness():
    from qingqiu.router.executor import Executor

    handlers = Executor._HANDLERS
    # 至少包含核心 6 个 intent
    for intent in [
        Intent.MEMORY_GET,
        Intent.MEMORY_SET,
        Intent.MEMORY_LIST,
        Intent.MEMORY_DELETE,
        Intent.TASK_ADD,
        Intent.TASK_LIST,
        Intent.STATUS,
    ]:
        assert intent in handlers, f"missing handler for {intent}"
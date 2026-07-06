"""router.executor · 意图执行器

S2.4 Executor（IMPLEMENTATION-PLAN §M2 · S2.4）

输入用户文本 → 路由到对应 CLI handler 执行。
复用现有 cli/* 模块的 handler 函数（不重新实现业务）。
"""

from __future__ import annotations

import asyncio
import re
import shlex
from dataclasses import dataclass, field
from typing import Any, Optional

from qingqiu.cli.confirm import run_confirm_ask, run_confirm_test
from qingqiu.cli.memory import run_memory_get, run_memory_list, run_memory_set
from qingqiu.cli.output import OutputFormatter
from qingqiu.cli.status import run_status
from qingqiu.cli.task import run_task_add, run_task_done, run_task_list, run_task_show
from qingqiu.llm import Message, get_provider
from qingqiu.router.classifier import ClassificationResult, IntentClassifier
from qingqiu.router.intent import Intent


@dataclass
class ExecutionResult:
    """执行结果"""

    intent: Intent
    exit_code: int
    classification: ClassificationResult
    entities: dict = field(default_factory=dict)
    note: str = ""


class Executor:
    """意图执行器

    用法：
        ex = Executor(llm_provider=None)
        result = ex.execute("memory get user_name", out)
    """

    def __init__(self, llm_provider=None, use_llm: bool = False):
        # 默认 use_llm=False：MVP 不强制要 LLM（规则足够覆盖 demo）
        self._classifier = IntentClassifier(llm_provider=llm_provider, use_llm=use_llm)

    # === 公共入口 ===

    def execute(self, text: str, out: OutputFormatter) -> int:
        """执行用户文本 → 返回 exit code"""
        result = self._classifier.classify(text)
        intent = result.intent

        if intent == Intent.UNKNOWN:
            return self._run_unknown(result, out)

        handler = self._HANDLERS.get(intent)
        if handler is None:
            return self._run_unsupported(result, out)

        try:
            entities = self._extract_entities(intent, text)
        except ValueError as e:
            out.error(str(e), code=1, hint="请提供必要参数")
            return 1

        # CLIError 由上层 main.py 捕获；其他异常本地兜底
        exit_code = handler(self, entities, out)

        if exit_code == 0:
            out.info(f"[router] intent={intent.value} source={result.source}")
        return exit_code

    # === 实体提取（极简） ===

    def _extract_entities(self, intent: Intent, text: str) -> dict:
        """从 raw_text 提取参数"""
        if intent == Intent.MEMORY_GET:
            key = self._extract_after(text, [r"memory\s+get", r"读(取)?", r"记忆\s*[:：]?\s*"])
            if not key:
                raise ValueError("memory get 需要 key")
            return {"key": key}

        if intent == Intent.MEMORY_SET:
            m = re.search(
                r"(?:memory\s+set|memory\s+写|记忆\s*[:：]?\s*(?:set|写|存|记下)|set\s+memory)\s+([^\s]+)\s+(.+)",
                text,
                re.IGNORECASE,
            )
            if m:
                return {"key": m.group(1), "value": m.group(2).strip()}
            # 兜底："key 是 value" 模式
            m2 = re.search(r"([^\s]+)\s*(?:=|是|为)\s*(.+)", text)
            if m2:
                return {"key": m2.group(1), "value": m2.group(2).strip()}
            raise ValueError("memory set 需要 key 和 value")

        if intent == Intent.MEMORY_LIST:
            return {}

        if intent == Intent.MEMORY_DELETE:
            key = self._extract_after(text, [r"memory\s+delete", r"删除记忆\s*", r"删\s*记忆\s*"])
            if not key:
                raise ValueError("memory delete 需要 key")
            return {"key": key}

        if intent == Intent.TASK_ADD:
            m = re.search(
                r"(?:task\s+add|新建任务|创建任务|添加任务|加任务|提醒我|记一下|加\s*任务)\s*(.+)",
                text,
                re.IGNORECASE,
            )
            if m:
                title = m.group(1).strip().strip("'\"")
                if title:
                    return {"description": [title]}  # 适配 cli/task.py args.description
            # 兜底：去掉前缀后整个当 title
            cleaned = re.sub(r"^(add|task|新建|创建|加|提醒|记一下)\s*", "", text, flags=re.IGNORECASE).strip()
            if cleaned:
                return {"description": [cleaned]}
            raise ValueError("task add 需要 title")

        if intent == Intent.TASK_LIST:
            return {}

        if intent == Intent.TASK_SHOW:
            tid = self._extract_task_id(text)
            if not tid:
                raise ValueError("task show 需要 task id (t-xxxx)")
            return {"id": tid}

        if intent == Intent.TASK_DONE:
            tid = self._extract_task_id(text)
            if not tid:
                raise ValueError("task done 需要 task id (t-xxxx)")
            return {"id": tid}

        if intent == Intent.STATUS:
            return {}

        if intent == Intent.CONFIG_SHOW:
            return {}

        if intent == Intent.CONFIG_PATH:
            return {}

        if intent == Intent.LLM_TEST:
            m = re.search(r"test\s+(\w+)", text, re.IGNORECASE)
            provider = m.group(1) if m else "default"
            return {"provider": provider}

        if intent == Intent.ASK:
            # 去掉前缀（清秋/qingqiu/帮我/...）
            cleaned = re.sub(r"^(qingqiu[,\s]*|清秋[,\s]*|帮我|请)", "", text).strip()
            return {"prompt": cleaned or text}

        return {}

    def _extract_after(self, text: str, patterns: list[str]) -> str:
        """提取 patterns 后面第一个 token"""
        for pat in patterns:
            m = re.search(pat + r"\s+([^\s]+)", text, re.IGNORECASE)
            if m:
                return m.group(1).strip("'\"")
        return ""

    def _extract_task_id(self, text: str) -> str:
        m = re.search(r"(t-[a-z0-9]+|t_[a-z0-9]+)", text, re.IGNORECASE)
        return m.group(1) if m else ""

    # === handler 路由 ===

    def _make_args(self, entities: dict) -> Any:
        """构造一个简单 namespace-like 对象（带 attribute 访问）"""

        class Args:
            pass

        a = Args()
        for k, v in entities.items():
            setattr(a, k, v)
        return a

    def _run_memory_get(self, entities: dict, out: OutputFormatter) -> int:
        return run_memory_get(self._make_args(entities), out)

    def _run_memory_set(self, entities: dict, out: OutputFormatter) -> int:
        return run_memory_set(self._make_args(entities), out)

    def _run_memory_list(self, entities: dict, out: OutputFormatter) -> int:
        return run_memory_list(self._make_args(entities), out)

    def _run_memory_delete(self, entities: dict, out: OutputFormatter) -> int:
        # delete handler 暂未在本切片导入，按 list 兜底
        from qingqiu.cli.memory import run_memory_delete

        return run_memory_delete(self._make_args(entities), out)

    def _run_task_add(self, entities: dict, out: OutputFormatter) -> int:
        return run_task_add(self._make_args(entities), out)

    def _run_task_list(self, entities: dict, out: OutputFormatter) -> int:
        return run_task_list(self._make_args(entities), out)

    def _run_task_show(self, entities: dict, out: OutputFormatter) -> int:
        from qingqiu.cli.task import run_task_show

        return run_task_show(self._make_args(entities), out)

    def _run_task_done(self, entities: dict, out: OutputFormatter) -> int:
        return run_task_done(self._make_args(entities), out)

    def _run_status(self, entities: dict, out: OutputFormatter) -> int:
        return run_status(self._make_args(entities), out)

    def _run_confirm_ask(self, entities: dict, out: OutputFormatter) -> int:
        return run_confirm_ask(self._make_args(entities), out)

    def _run_confirm_test(self, entities: dict, out: OutputFormatter) -> int:
        return run_confirm_test(self._make_args(entities), out)

    def _run_unknown(self, result: ClassificationResult, out: OutputFormatter) -> int:
        out.info(
            f"未识别意图（source={result.source}, reason={result.reason}）。"
            f"试试：'memory get user_name' / 'task add 写文档' / '看任务' / 'status'"
        )
        return 1

    def _run_unsupported(self, result: ClassificationResult, out: OutputFormatter) -> int:
        out.info(f"暂不支持: intent={result.intent.value}（MVP 范围外）")
        return 1

    # === handler 注册 ===

    _HANDLERS = {
        Intent.MEMORY_GET: _run_memory_get,
        Intent.MEMORY_SET: _run_memory_set,
        Intent.MEMORY_LIST: _run_memory_list,
        Intent.MEMORY_DELETE: _run_memory_delete,
        Intent.TASK_ADD: _run_task_add,
        Intent.TASK_LIST: _run_task_list,
        Intent.TASK_SHOW: _run_task_show,
        Intent.TASK_DONE: _run_task_done,
        Intent.STATUS: _run_status,
        Intent.CONFIG_SHOW: lambda self, e, o: 0,  # 占位
        Intent.CONFIG_PATH: lambda self, e, o: 0,  # 占位
        Intent.LLM_TEST: lambda self, e, o: 0,  # 占位
    }


def run_ask(args: Any, out: OutputFormatter, llm_provider=None) -> int:
    """`qingqiu ask "<text>"` — 自然语言入口

    接 Executor + IntentClassifier
    """
    prompt = getattr(args, "prompt", None) or []
    if isinstance(prompt, list):
        text = " ".join(prompt).strip()
    else:
        text = str(prompt).strip()
    if not text:
        out.error("ask 需要 prompt", code=1, hint="qingqiu ask \"memory get user_name\"")
        return 1

    executor = Executor(llm_provider=llm_provider, use_llm=False)
    return executor.execute(text, out)


# === P0-1 ASK → LLM 真实回答（v1.0 实装） ===

def _get_default_llm_provider():
    """从 ConfigManager 拿默认 LLM provider（失败返 None）"""
    try:
        from qingqiu.config.manager import ConfigManager

        cfg_mgr = ConfigManager()
        cfg_mgr.load()
        provider_name = cfg_mgr.config.llm.default
        provider_cfg = cfg_mgr.config.llm.providers.get(provider_name, {})
        return get_provider(provider_name, **provider_cfg)
    except Exception:
        return None


def ask_llm(prompt: str, out: OutputFormatter) -> int:
    """`qingqiu ask_llm "<question>"` — 直接调 LLM 回答问题（不走 router）"""
    provider = _get_default_llm_provider()
    if provider is None:
        out.error(
            "LLM provider 未配置或初始化失败",
            code=2,
            hint="qingqiu config show 看 llm.default；qingqiu llm test <provider> 测试",
        )
        return 2

    try:
        from qingqiu.config.manager import ConfigManager

        cfg_mgr = ConfigManager()
        cfg_mgr.load()
        system_prompt = cfg_mgr.config.personality.system_prompt
    except Exception:
        system_prompt = "你是清秋，给 ROG 个人使用。"

    try:
        async def _run():
            return await provider.complete(
                [
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=prompt),
                ],
                max_tokens=1024,
            )

        response = asyncio.run(_run())
        out.print({"answer": response.content, "model": response.model, "provider": response.provider}, title="ask_llm")
        return 0
    except Exception as e:
        out.error(f"LLM 调用失败: {type(e).__name__}: {e}", code=2)
        return 2
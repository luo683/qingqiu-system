"""router.classifier · 意图分类器（规则 + LLM 兜底）

S2.2 Router 意图识别：
- 规则模式优先（regex 匹配）— 快、可靠、零成本
- LLM 兜底（仅在规则不命中时调用）— 灵活、智能
- Fallback: Intent.UNKNOWN
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from qingqiu.router.intent import Intent


@dataclass
class ClassificationResult:
    """分类结果"""

    intent: Intent
    source: str  # "rule" / "llm" / "fallback"
    confidence: float  # 0.0-1.0
    raw_text: str  # 原始输入
    reason: str = ""  # 命中的规则名 / LLM 解释


class RuleBasedClassifier:
    """规则分类器（regex 模式）"""

    # (regex, intent, rule_name) - 按顺序匹配
    # 边界用 (?<![a-zA-Z0-9_]) + (?![a-zA-Z0-9_]) 实现（中文友好）
    # \b 在中文两侧不工作（中文不在 \w 里）
    B = r"(?<![a-zA-Z0-9_])"  # 左边界：前一个字符不是 word
    E = r"(?![a-zA-Z0-9_])"     # 右边界：后一个字符不是 word

    RULES: list[tuple[str, Intent, str]] = [
        # task 命令（两种顺序都支持：add→task / task→add）
        (rf"{B}(add|新建|创建|加|记一下|提醒我){E}.*?{B}(task|任务|待办|todo){E}", Intent.TASK_ADD, "task_add_zhfirst"),
        (rf"{B}(task|任务){E}.*?{B}(add|新建|创建|加){E}", Intent.TASK_ADD, "task_add_engfirst"),
        # task_list: 两种顺序都支持（"task list" / "看任务"）
        (rf"{B}(task|任务){E}.*?{B}(list|列表){E}", Intent.TASK_LIST, "task_list_eng"),
        (rf"{B}(看|显示|有什么|查){E}.*?{B}(task|任务){E}", Intent.TASK_LIST, "task_list_zh"),
        (rf"{B}(task|任务){E}.*?{B}(show|详情|看|是什么){E}.*?(t-|t_)", Intent.TASK_SHOW, "task_show_keyword"),
        (rf"{B}(完成|done|finished|搞定了){E}.*?(t-|t_)", Intent.TASK_DONE, "task_done_keyword"),
        (rf"{B}(archive|归档|删除任务){E}.*?(t-|t_)", Intent.TASK_ARCHIVE, "task_archive_keyword"),

        # memory 命令
        (rf"{B}(memory|记忆){E}.*?{B}(set|写|记下|记录|存|save){E}", Intent.MEMORY_SET, "memory_set_keyword"),
        (rf"{B}(memory|记忆){E}.*?{B}(get|读|是什么|recall|查){E}", Intent.MEMORY_GET, "memory_get_keyword"),
        (rf"{B}(memory|记忆){E}.*?{B}(list|列表|全部){E}", Intent.MEMORY_LIST, "memory_list_keyword"),
        (rf"{B}(memory|记忆){E}.*?{B}(delete|删|remove){E}", Intent.MEMORY_DELETE, "memory_delete_keyword"),
        (rf"{B}(search|搜|find|查){E}.*?{B}(memory|记忆){E}", Intent.MEMORY_SEARCH, "memory_search_keyword"),
        (rf"{B}(memory|记忆){E}.*?{B}(search|搜|find){E}", Intent.MEMORY_SEARCH, "memory_search_keyword"),

        # status / config
        (rf"{B}(status|状态|健康|health|check){E}", Intent.STATUS, "status_keyword"),
        (rf"{B}(config|配置){E}.*?{B}(show|显示|看){E}", Intent.CONFIG_SHOW, "config_show_keyword"),
        (rf"{B}(config|配置){E}.*?{B}(path|路径|在哪){E}", Intent.CONFIG_PATH, "config_path_keyword"),

        # llm test
        (rf"{B}(test|测试){E}.*?{B}(llm|provider|模型){E}", Intent.LLM_TEST, "llm_test_keyword"),

        # chat
        (rf"{B}(chat|聊天|对话|repl){E}", Intent.CHAT, "chat_keyword"),

        # ask
        (r"^(qingqiu[,\s]*|清秋[,\s]*)?(.{0,100}\?$|.{0,100}？$|.{0,100}什么|.{0,100}怎么|.{0,100}如何|.{0,100}为什么|.{0,100}帮我|.{0,100}解释|.{0,100}写一下)", Intent.ASK, "ask_question"),
    ]

    def classify(self, text: str) -> Optional[ClassificationResult]:
        """返回 None if 无规则命中"""
        t = text.strip()
        if not t:
            return None

        for pattern, intent, name in self.RULES:
            if re.search(pattern, t, re.IGNORECASE):
                return ClassificationResult(
                    intent=intent,
                    source="rule",
                    confidence=1.0,
                    raw_text=t,
                    reason=name,
                )
        return None


class LLMClassifier:
    """LLM 分类器（仅在规则不命中时调用）

    需要配置 LLM provider（S1.2 已实现 4 个 provider）。
    """

    # LLM system prompt
    SYSTEM_PROMPT = """你是清秋（qingqiu-system）的意图分类器。分析用户输入，返回一个 JSON。

可选意图（Intent）：
- ask: 单次提问（一般问题、解释、帮我做 X）
- chat: 进入交互对话模式
- task_list: 列出任务
- task_show: 看任务详情（需要 task ID）
- task_add: 新建任务
- task_done: 完成任务
- task_archive: 归档任务
- memory_get: 读取记忆
- memory_set: 写入记忆
- memory_list: 列出记忆
- memory_delete: 删除记忆
- memory_search: 搜索记忆
- status: 健康状态
- config_show: 显示配置
- config_path: 配置路径
- llm_test: 测试 LLM provider
- unknown: 无法识别

返回格式（必须是 valid JSON，无 markdown）：
{"intent": "<name>", "confidence": <0.0-1.0>, "reason": "<一句话解释>"}

只返回 JSON，不要其他内容。"""

    def __init__(self, llm_provider):
        """llm_provider: S1.2 的 LLMProvider 实例"""
        self._llm = llm_provider

    def classify(self, text: str) -> Optional[ClassificationResult]:
        """调用 LLM 分类；返回 None if 失败"""
        if self._llm is None:
            return None
        try:
            import asyncio
            from qingqiu.llm import Message

            async def _classify():
                resp = await self._llm.complete(
                    [Message(role="user", content=f"{self.SYSTEM_PROMPT}\n\n用户输入：{text}")],
                    max_tokens=200,
                )
                return resp.content

            content = asyncio.run(_classify())
            return self._parse(content, text)
        except Exception as e:
            return None

    def _parse(self, content: str, raw: str) -> Optional[ClassificationResult]:
        """解析 LLM 返回的 JSON"""
        # 提取 JSON（兼容 LLM 偶尔加 markdown ```json 包装）
        content = content.strip()
        if content.startswith("```"):
            # 去掉 markdown fence
            lines = content.split("\n")
            content = "\n".join(l for l in lines if not l.startswith("```"))

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # 尝试提取 {...}
            match = re.search(r'\{[^}]+\}', content)
            if not match:
                return None
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

        intent = Intent.from_str(data.get("intent", ""))
        confidence = float(data.get("confidence", 0.5))
        reason = str(data.get("reason", ""))
        return ClassificationResult(
            intent=intent,
            source="llm",
            confidence=min(max(confidence, 0.0), 1.0),
            raw_text=raw,
            reason=reason,
        )


class IntentClassifier:
    """主分类器：规则 + LLM 兜底

    流程：
    1. 规则匹配 → 命中即返回（confidence=1.0）
    2. 规则不命中 + LLM 可用 → LLM 分类
    3. 都不行 → UNKNOWN

    使用：
        classifier = IntentClassifier(llm_provider=get_provider("openai"))
        result = classifier.classify("memory get user_name")
        print(result.intent, result.source, result.confidence)
    """

    def __init__(self, llm_provider=None, use_llm: bool = True):
        self._rule = RuleBasedClassifier()
        self._llm = LLMClassifier(llm_provider) if use_llm and llm_provider else None
        self._use_llm = use_llm

    def classify(self, text: str) -> ClassificationResult:
        """主入口：分类意图"""
        if not text or not text.strip():
            return ClassificationResult(
                intent=Intent.UNKNOWN,
                source="fallback",
                confidence=0.0,
                raw_text=text or "",
                reason="empty input",
            )

        # 1. 规则优先
        rule_result = self._rule.classify(text)
        if rule_result is not None:
            return rule_result

        # 2. LLM 兜底
        if self._llm is not None:
            llm_result = self._llm.classify(text)
            if llm_result is not None:
                return llm_result

        # 3. Fallback
        return ClassificationResult(
            intent=Intent.UNKNOWN,
            source="fallback",
            confidence=0.0,
            raw_text=text,
            reason="no rule matched + no LLM",
        )
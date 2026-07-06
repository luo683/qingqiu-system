"""planner.dag · 任务拆解（P0-3 简化版）

简单 DAG：
- 输入：复杂任务文本
- 输出：Step 列表（按依赖顺序）
- 用 LLM 拆解（fallback：按简单规则拆"修 X" → [定位, 修, 验证]）

注：完整 DAG（依赖图 + 并行执行）留待后续切片。本切片只生成计划，不执行。
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field

from qingqiu.llm import Message


@dataclass
class Step:
    """单个步骤"""

    id: str
    title: str
    action: str  # "shell" | "read" | "edit" | "verify" | "llm"
    depends_on: list[str] = field(default_factory=list)
    detail: str = ""


@dataclass
class Plan:
    """任务计划"""

    task: str
    steps: list[Step]

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "steps": [
                {
                    "id": s.id,
                    "title": s.title,
                    "action": s.action,
                    "depends_on": s.depends_on,
                    "detail": s.detail,
                }
                for s in self.steps
            ],
        }


# 简化规则：复杂任务模板
_RULE_TEMPLATES = {
    r"(修|fix).*(bug|错误|失败)": [
        Step("1", "定位 bug 范围", "read", detail="读相关代码 + 找根因"),
        Step("2", "写修复 patch", "edit", depends_on=["1"], detail="最小变更修根因"),
        Step("3", "跑测试验证", "shell", depends_on=["2"], detail="pytest tests/"),
    ],
    r"(实现|implement|新增|加).*(功能|feature|切片|slice)": [
        Step("1", "设计接口", "llm", detail="确定输入/输出/边界"),
        Step("2", "写测试 (red)", "edit", depends_on=["1"], detail="先写失败测试"),
        Step("3", "实现 (green)", "edit", depends_on=["2"], detail="最小可工作代码"),
        Step("4", "重构", "edit", depends_on=["3"], detail="消除重复"),
        Step("5", "真跑验证", "shell", depends_on=["4"], detail="scripts/verify_*.py"),
    ],
    r"(优化|optimize|加速|performance)": [
        Step("1", "基线测量", "shell", detail="跑 bench 记耗时"),
        Step("2", "找瓶颈", "read", depends_on=["1"], detail="profile / 看热路径"),
        Step("3", "优化实施", "edit", depends_on=["2"], detail="cache / 算法 / 并行"),
        Step("4", "对比验证", "shell", depends_on=["3"], detail="再跑 bench 对比"),
    ],
}


def plan_with_rules(task: str) -> Plan | None:
    """规则匹配生成计划（无 LLM 调用）"""
    for pattern, steps in _RULE_TEMPLATES.items():
        if re.search(pattern, task, re.IGNORECASE):
            return Plan(task=task, steps=list(steps))
    return None


async def plan_with_llm(task: str, provider) -> Plan | None:
    """LLM 拆解（fallback）"""
    system = (
        "你是清秋的任务规划器。把用户任务拆成 3-5 步计划，每步含 id/title/action/depends_on/detail。\n"
        "action 取值: shell / read / edit / verify / llm\n"
        "返回 JSON: {\"steps\": [{...}, ...]}\n"
        "只返回 JSON，无 markdown 包装。"
    )
    try:
        resp = await provider.complete(
            [
                Message(role="system", content=system),
                Message(role="user", content=f"任务：{task}"),
            ],
            max_tokens=800,
            json_mode=True,
        )
        content = resp.content.strip()
        # 兼容 markdown 包装
        if content.startswith("```"):
            content = "\n".join(l for l in content.split("\n") if not l.startswith("```"))
        data = json.loads(content)
        steps = []
        for i, s in enumerate(data.get("steps", []), 1):
            steps.append(
                Step(
                    id=str(s.get("id", i)),
                    title=s.get("title", f"step {i}"),
                    action=s.get("action", "llm"),
                    depends_on=s.get("depends_on", []),
                    detail=s.get("detail", ""),
                )
            )
        return Plan(task=task, steps=steps)
    except Exception:
        return None


def plan(task: str, provider=None) -> Plan | None:
    """主入口：先规则后 LLM"""
    rule_plan = plan_with_rules(task)
    if rule_plan:
        return rule_plan
    if provider is None:
        return None
    try:
        return asyncio.run(plan_with_llm(task, provider))
    except Exception:
        return None
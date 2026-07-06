"""qingqiu.router · 意图路由（S2.2）

LLM 优先 + 规则兜底
"""

from qingqiu.router.classifier import (
    ClassificationResult,
    IntentClassifier,
    LLMClassifier,
    RuleBasedClassifier,
)
from qingqiu.router.intent import Intent

__all__ = [
    "Intent",
    "IntentClassifier",
    "ClassificationResult",
    "RuleBasedClassifier",
    "LLMClassifier",
]
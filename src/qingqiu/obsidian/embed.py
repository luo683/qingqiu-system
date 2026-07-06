"""obsidian.embed · M8.4 简单嵌入（hash-based 32-dim）

PRD §M8 · S8.4 简化版：deterministic hash 向量
"""

from __future__ import annotations

import hashlib
import re

_DIM = 32


def _tokenize(text: str) -> list[str]:
    """tokenize：中文按字符 + 英文按单词"""
    return re.findall(r"[\w]+|.", text, re.UNICODE)


def embed(text: str, dim: int = _DIM) -> list[float]:
    """text → 32-dim 0/1 向量（每个 token 的 hash 取 dim bits）

    Deterministic: 相同 text → 相同 vector
    """
    if not text:
        return [0.0] * dim
    vec = [0.0] * dim
    for token in _tokenize(text.lower()):
        if not token.strip():
            continue
        h = hashlib.md5(token.encode("utf-8")).hexdigest()
        # 每个 token 投到 dim 个 bit 位置
        for i in range(dim):
            if int(h[i % len(h)], 16) % 2:
                vec[i] += 1.0
    # 归一化
    n = sum(vec) or 1.0
    return [v / n for v in vec]


def cosine_sim(a: list[float], b: list[float]) -> float:
    """cosine similarity"""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
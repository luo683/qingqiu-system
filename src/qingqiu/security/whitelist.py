"""security.whitelist · 目录白名单（S5.2 切片）

PRD §6.1：4 个标准白名单目录
- E:\\MiniMax Code WorkSpace\\
- C:\\Users\\ROG\\Downloads\\
- C:\\Users\\ROG\\Desktop\\
- C:\\Users\\ROG\\Documents\\

黑名单应被拒：
- C:\\Windows\\ · C:\\Program Files\\ · C:\\Users\\ROG\\AppData\\
- 其他非白名单目录

接口：
- is_whitelisted(path) → bool
- check_path(path, op="read") → Path（规范化后的绝对路径；不在白名单抛 WhitelistError）
- resolve(path) → Path（便捷 = check_path）
"""

from __future__ import annotations

from pathlib import Path

from qingqiu.cli.errors import CLIError


class WhitelistError(CLIError):
    """路径不在白名单时抛（exit code = 2 · 系统错）"""

    code = 2


WHITELIST_DIRS: list[Path] = [
    Path("E:/MiniMax Code WorkSpace"),
    Path("C:/Users/ROG/Downloads"),
    Path("C:/Users/ROG/Desktop"),
    Path("C:/Users/ROG/Documents"),
]


def _normalize(path: Path) -> Path:
    """规范化：expanduser + resolve（处理 .. 反向 + 相对路径）"""
    return path.expanduser().resolve()


def _is_under(child: Path, parent: Path) -> bool:
    """检查 child 是否在 parent 下（含等于）

    注意：必须用 resolve 后的绝对路径，避免 "E:/Code" 前缀匹配 "E:/CodeXxx"
    """
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def is_whitelisted(path: Path) -> bool:
    """检查 path 是否在任一白名单目录下（含祖先）

    必须先 resolve 才能正确处理：
    - 相对路径
    - .. 反向
    - 前缀相似攻击（如 E:\\CodeXxx vs E:\\Code）
    """
    p = _normalize(path)
    for wl_dir in WHITELIST_DIRS:
        if _is_under(p, _normalize(wl_dir)):
            return True
    return False


def check_path(path: Path, op: str = "read") -> Path:
    """白名单检查 + 路径解析

    Args:
        path: 要检查的路径
        op: 操作类型 ("read" / "write" / "delete")，目前规则相同
    Returns:
        规范化后的绝对路径
    Raises:
        WhitelistError: 不在白名单
        ValueError: op 不合法
    """
    if op not in ("read", "write", "delete"):
        raise ValueError(f"invalid op: {op!r}, expected 'read'/'write'/'delete'")
    p = _normalize(path)
    if not is_whitelisted(p):
        raise WhitelistError(
            f"path not in whitelist: {path}",
            hint="只允许访问 4 个标准白名单目录（MiniMax Code WorkSpace / Downloads / Desktop / Documents）",
        )
    return p


def resolve(path: str | Path) -> Path:
    """便捷函数 = check_path(Path(path), op='read')"""
    return check_path(Path(path))
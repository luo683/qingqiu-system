"""L1 · 项目级记忆（Markdown · 每项目一文件）

存储位置：~/.qingqiu/memory/projects/<name>.md
格式：`key = value`（每行一对，`#` 开头是注释，空行忽略）
atomic write（写 .tmp + rename，避免崩溃时损坏文件）
"""

from __future__ import annotations

from pathlib import Path


class L1ProjectMemory:
    """L1 · 项目级 Markdown 记忆"""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict[str, str] = {}
        self._load()

    @property
    def name(self) -> str:
        return "L1"

    @property
    def path(self) -> Path:
        """项目记忆文件路径"""
        return self._path

    def _load(self) -> None:
        """从文件加载到内存 dict"""
        if not self._path.exists():
            return
        for raw_line in self._path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            self._data[key.strip()] = value.strip()

    def _save(self) -> None:
        """atomic write：写 .tmp → rename"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        lines = [f"# {self._path.stem} · 项目记忆", ""]
        for key, value in self._data.items():
            lines.append(f"{key} = {value}")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp.replace(self._path)

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> bool:
        if key not in self._data:
            return False
        del self._data[key]
        self._save()
        return True

    def list_keys(self) -> list[str]:
        return list(self._data.keys())

    def reload(self) -> None:
        """从文件重新加载（外部修改后用）"""
        self._data.clear()
        self._load()
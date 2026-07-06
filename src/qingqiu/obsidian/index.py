"""obsidian.index · S8.2 watchdog 增量索引 (复制自 M8 worktree)"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    Observer = None  # type: ignore
    FileSystemEventHandler = object  # type: ignore


class _Handler(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(self, callback: Callable[[Path, str], None]) -> None:
        super().__init__()
        self._cb = callback

    def on_created(self, event):  # type: ignore[no-untyped-def]
        if not event.is_directory and event.src_path.endswith(".md"):
            self._cb(Path(event.src_path), "created")

    def on_modified(self, event):  # type: ignore[no-untyped-def]
        if not event.is_directory and event.src_path.endswith(".md"):
            self._cb(Path(event.src_path), "modified")

    def on_deleted(self, event):  # type: ignore[no-untyped-def]
        if not event.is_directory and event.src_path.endswith(".md"):
            self._cb(Path(event.src_path), "deleted")


class Index:
    """增量索引"""

    def __init__(self) -> None:
        self._observer = None  # type: ignore[var-annotated]
        self._events: list[tuple[Path, str]] = []

    def start_watch(self, root: Path, callback: Callable[[Path, str], None] | None = None) -> None:
        if Observer is None:
            raise ImportError("watchdog 未装：uv add watchdog")
        if callback is None:
            callback = self._record
        handler = _Handler(callback)
        self._observer = Observer()
        self._observer.schedule(handler, str(root), recursive=True)
        self._observer.start()

    def stop_watch(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None

    def _record(self, path: Path, op: str) -> None:
        self._events.append((path, op))

    def get_changed(self) -> list[tuple[Path, str]]:
        ev = list(self._events)
        self._events.clear()
        return ev
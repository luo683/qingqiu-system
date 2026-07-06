"""daemon.server · HTTP daemon（P0-4 简化版）

FastAPI HTTP server · 4 个端点：
- GET  /health          → {"status": "ok"}
- POST /ask             → {"text": "..."} → Executor.execute
- GET  /status          → daemon/llm/memory
- POST /memory          → {"key": "...", "value": "...", "layer": "L3"}

直接复用 Executor + ConfigManager + Memory
"""

from __future__ import annotations

from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as e:
    raise ImportError("daemon 需要 fastapi + uvicorn：uv add fastapi uvicorn") from e

from qingqiu.cli.output import OutputFormatter
from qingqiu.router.executor import Executor


class AskRequest(BaseModel):
    text: str


class MemorySetRequest(BaseModel):
    key: str
    value: str
    layer: str = "L3"


def create_app() -> FastAPI:
    app = FastAPI(title="qingqiu daemon", version="0.3.0")
    executor = Executor(llm_provider=None, use_llm=False)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": "0.3.0"}

    @app.post("/ask")
    def ask(req: AskRequest) -> dict[str, Any]:
        out = OutputFormatter(json_mode=True, no_color=True)
        rc = executor.execute(req.text, out)
        return {"exit_code": rc, "text": req.text}

    @app.get("/status")
    def status() -> dict[str, Any]:
        from qingqiu.cli.status import run_status

        class Args:
            pass

        out = OutputFormatter(json_mode=True, no_color=True)
        run_status(Args(), out)
        return {"status": "ok"}

    @app.post("/memory")
    def memory_set(req: MemorySetRequest) -> dict[str, Any]:
        from qingqiu.cli.memory import run_memory_set

        class Args:
            pass

        a = Args()
        a.key = req.key
        a.value = req.value
        a.layer = req.layer
        out = OutputFormatter(json_mode=True, no_color=True)
        try:
            run_memory_set(a, out)
            return {"status": "ok", "key": req.key, "layer": req.layer}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    return app


def main() -> int:
    """daemon 启动入口：uvicorn"""
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=7788, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
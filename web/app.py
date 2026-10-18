"""FastAPI Web 界面：提交任务，实时观察多智能体编排过程。

启动方式（在项目根目录）：
    .venv/Scripts/python.exe -m uvicorn web.app:app --reload
然后浏览器打开 http://127.0.0.1:8000
"""
import asyncio
import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 保证从任意工作目录启动都能导入项目根目录下的 graph / agents
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents import WORKER_PROMPTS  # noqa: E402
from graph import MAX_TOOL_ROUNDS, TASK_ROUTES, build_graph  # noqa: E402

load_dotenv(ROOT / ".env")


def _argv_option(flag: str) -> str | None:
    """从命令行参数中取值，兼容 `--port 8000` 与 `--port=8000`。"""
    argv = sys.argv
    for i, arg in enumerate(argv):
        if arg == flag and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(f"{flag}="):
            return arg.split("=", 1)[1]
    return None


def _access_url() -> str:
    """推导实际访问地址：优先环境变量（run.py 设置），其次 uvicorn 命令行参数。"""
    host = os.getenv("APP_HOST") or _argv_option("--host") or "127.0.0.1"
    port = os.getenv("APP_PORT") or _argv_option("--port") or "8000"
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    return f"http://{host}:{port}"


@asynccontextmanager
async def lifespan(_: FastAPI):
    print("=" * 46)
    print("  多智能体编排演示")
    print(f"  访问地址: {_access_url()}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 46, flush=True)
    yield


app = FastAPI(title="Multi-Agent Orchestration Demo", lifespan=lifespan)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 图本身无状态，进程内复用一个实例即可
GRAPH = build_graph()

# 进行中的运行：run_id -> 事件队列
RUNS: dict[str, asyncio.Queue] = {}


class RunRequest(BaseModel):
    task: str


def _next_node(node: str, delta: dict, tool_rounds: int) -> str | None:
    """根据刚结束的节点推导下一个节点，用于前端高亮当前步骤。"""
    if node == "supervisor":
        task_type = delta.get("task_type", "unknown")
        return TASK_ROUTES.get(task_type, "unknown")
    if node == "tool_agent":
        messages = delta.get("messages") or []
        last = messages[-1] if messages else None
        has_tool_calls = bool(getattr(last, "tool_calls", None))
        if has_tool_calls and tool_rounds < MAX_TOOL_ROUNDS:
            return "tools"
        return "aggregate"
    if node == "tools":
        return "tool_agent"
    if node in WORKER_PROMPTS or node == "unknown":
        return "aggregate"
    return None


def _serialize_delta(node: str, delta: dict, tool_rounds: int) -> dict:
    """把 LangChain 消息对象转成前端可消费的纯 JSON。"""
    if node == "tool_agent":
        messages = delta.get("messages") or []
        last = messages[-1] if messages else None
        if last is None:
            return {}
        calls = [
            {"name": call.get("name"), "args": call.get("args") or {}}
            for call in (getattr(last, "tool_calls", None) or [])
        ]
        return {"content": str(last.content or ""), "tool_calls": calls}

    if node == "tools":
        results = []
        for message in delta.get("messages") or []:
            content = str(message.content or "")
            if len(content) > 1200:
                content = content[:1200] + "…"
            results.append({
                "name": getattr(message, "name", "") or "",
                "content": content,
            })
        return {
            "tool_results": results,
            "tool_rounds": tool_rounds,
        }

    return delta


async def _execute_run(task: str, queue: asyncio.Queue) -> None:
    """后台执行一次编排，把每个节点的进度写入队列。"""
    state = {
        "task": task,
        "task_type": "",
        "result": "",
        "messages": [],
    }
    tool_rounds = 0
    try:
        await queue.put({"type": "run_started", "task": task})
        await queue.put({"type": "node_start", "node": "supervisor"})

        async for update in GRAPH.astream(state, stream_mode="updates"):
            for node, delta in update.items():
                delta = delta or {}
                state.update(delta)
                if node == "tools":
                    tool_rounds += 1
                await queue.put({
                    "type": "node_end",
                    "node": node,
                    "data": _serialize_delta(node, delta, tool_rounds),
                })
                nxt = _next_node(node, delta, tool_rounds)
                if nxt:
                    await queue.put({"type": "node_start", "node": nxt})

        await queue.put({
            "type": "done",
            "task_type": state.get("task_type", ""),
            "result": state.get("result", ""),
        })
    except Exception as exc:  # 把后端异常转成事件，让前端能展示
        await queue.put({"type": "error", "message": str(exc)})


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def _event_stream(run_id: str):
    queue = RUNS.get(run_id)
    if queue is None:
        yield _sse({"type": "error", "message": "运行不存在或已结束"})
        return
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
                continue
            yield _sse(event)
            if event["type"] in ("done", "error"):
                break
    finally:
        RUNS.pop(run_id, None)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/runs")
async def create_run(req: RunRequest):
    task = req.task.strip()
    if not task:
        raise HTTPException(status_code=400, detail="任务不能为空")
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise HTTPException(
            status_code=400,
            detail="未配置 DEEPSEEK_API_KEY，请在 .env 中设置后重启服务",
        )

    run_id = uuid.uuid4().hex
    queue: asyncio.Queue = asyncio.Queue()
    RUNS[run_id] = queue
    asyncio.create_task(_execute_run(task, queue))
    return {"run_id": run_id}


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str) -> StreamingResponse:
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="运行不存在或已结束")
    return StreamingResponse(
        _event_stream(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

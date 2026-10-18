"""LangGraph 图定义：supervisor 路由 -> 专职 worker 执行 -> aggregate 汇总。

整张图的走向：

    START -> supervisor --(按 task_type 条件路由)--> translate / summarize / write / unknown
                          \_____________________________> aggregate -> END
"""
from langgraph.graph import StateGraph, START, END

from state import State
from agents import build_llm, WORKER_PROMPTS


SUPERVISOR_PROMPT = (
    "你是任务分类器，判断用户请求属于以下哪一类，只输出类别单词"
    "（translate / summarize / write / unknown），不要输出任何其他内容：\n"
    "- translate：需要翻译\n"
    "- summarize：需要总结 / 提炼要点\n"
    "- write：需要撰写、扩写、创作内容\n"
    "- unknown：以上都不是"
)

UNKNOWN_REPLY = "抱歉，我目前只能处理翻译、总结、撰写这三类任务，无法处理你提交的请求。"


def _supervisor(state: State) -> dict:
    """主管节点：用 LLM 把用户请求归类，写入 task_type。"""
    llm = build_llm()
    reply = llm.invoke(f"{SUPERVISOR_PROMPT}\n\n用户请求：{state['task']}")
    task_type = str(reply.content).strip().lower()
    if task_type not in WORKER_PROMPTS:
        task_type = "unknown"
    return {"task_type": task_type}


def _make_worker(name: str):
    """工厂函数：为某个 worker 生成对应的节点函数。"""

    def worker(state: State) -> dict:
        llm = build_llm()
        reply = llm.invoke(f"{WORKER_PROMPTS[name]}\n\n内容：{state['task']}")
        return {"result": str(reply.content).strip()}

    return worker


def _unknown(state: State) -> dict:
    """无法识别的任务：直接返回明确提示，不调用 LLM。"""
    return {"result": UNKNOWN_REPLY}


def _aggregate(state: State) -> dict:
    print(">>> aggregate reached")
    """汇总节点：当前是单 worker 场景，直接透传结果；将来多 worker 在此拼接。"""
    return {"result": state["result"]}


def _router(state: State) -> str:
    """条件路由：根据 supervisor 给出的 task_type 决定下一步去哪个节点。"""
    task_type = state.get("task_type", "unknown")
    return task_type if task_type in WORKER_PROMPTS else "unknown"


def build_graph():
    """把各节点和边组装成一张可运行的图。"""
    builder = StateGraph(State)

    builder.add_node("supervisor", _supervisor)
    for name in WORKER_PROMPTS:
        builder.add_node(name, _make_worker(name))
    builder.add_node("unknown", _unknown)
    builder.add_node("aggregate", _aggregate)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        _router,
        {**{name: name for name in WORKER_PROMPTS}, "unknown": "unknown"},
    )
    for name in WORKER_PROMPTS:
        builder.add_edge(name, "aggregate")
    builder.add_edge("unknown", "aggregate")
    builder.add_edge("aggregate", END)

    return builder.compile()

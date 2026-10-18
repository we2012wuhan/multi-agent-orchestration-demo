"""LangGraph 图定义：supervisor 路由 -> worker / 工具循环 -> aggregate 汇总。

整张图的走向：

    START -> supervisor --(按 task_type 条件路由)--> translate / summarize / write
                                                   --> tool_agent <-> tools（多轮循环）
                                                   --> unknown
                          以上分支最终都汇入 --> aggregate -> END

工具调用采用「原生 function calling」：tool_agent 把工具 schema 交给 DeepSeek，
模型决定是否调用 web_search；只要回复里还有 tool_calls，就继续走 tools 节点，
直到模型给出最终答案或达到 MAX_TOOL_ROUNDS 上限。
"""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from state import State
from agents import build_llm, WORKER_PROMPTS
from tools import web_search

MAX_TOOL_ROUNDS = 6
TOOLS = [web_search]

SUPERVISOR_PROMPT = (
    "你是任务分类器，判断用户请求属于以下哪一类，只输出类别单词"
    "（translate / summarize / write / search / unknown），不要输出任何其他内容：\n"
    "- translate：需要翻译\n"
    "- summarize：需要总结 / 提炼要点\n"
    "- write：需要撰写、扩写、创作内容\n"
    "- search：需要联网搜索、查询实时或外部信息（新闻、人物、价格、事件等）\n"
    "- unknown：以上都不是"
)

TOOL_AGENT_PROMPT = (
    "你是一名联网检索助手，负责回答需要外部或最新信息的请求。\n"
    "工作方式：\n"
    "1. 需要事实信息时调用 web_search 工具，可以多轮检索、逐步细化查询；\n"
    "2. 不要编造搜索结果；信息不足时如实说明；\n"
    "3. 用中文条理清晰地回答，并在末尾列出参考来源（标题 + 链接）。"
)

UNKNOWN_REPLY = (
    "抱歉，我目前只能处理翻译、总结、撰写、联网搜索这几类任务，"
    "无法处理你提交的请求。"
)

# task_type -> 下一跳节点。supervisor 的 LLM 输出会按这张表归一化。
TASK_ROUTES = {
    **{name: name for name in WORKER_PROMPTS},
    "search": "tool_agent",
    "unknown": "unknown",
}


def _supervisor(state: State) -> dict:
    """主管节点：用 LLM 把用户请求归类，写入 task_type。"""
    llm = build_llm()
    reply = llm.invoke(f"{SUPERVISOR_PROMPT}\n\n用户请求：{state['task']}")
    task_type = str(reply.content).strip().lower()
    if task_type not in TASK_ROUTES:
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


def _make_tool_agent(tools: list):
    """工具智能体：把工具 schema 绑定给 LLM，由模型决定是否调用工具。

    每轮把「system prompt + 完整对话历史」交给模型；
    模型若返回 tool_calls，就由 tools 节点执行，循环继续。
    """

    def tool_agent(state: State) -> dict:
        llm = build_llm().bind_tools(tools)
        history = list(state.get("messages") or [])
        updates = []
        if not history:
            human = HumanMessage(content=state["task"])
            history = [human]
            updates.append(human)

        reply = llm.invoke([SystemMessage(content=TOOL_AGENT_PROMPT), *history])
        updates.append(reply)
        return {"messages": updates}

    return tool_agent


def _tool_call_rounds(state: State) -> int:
    """工具轮数 = 消息历史里「带 tool_calls 的 AI 消息」条数。

    一轮可以同时调用多个工具，因此不能用 ToolMessage 条数来计数。
    """
    return sum(
        1 for message in state.get("messages") or []
        if isinstance(message, AIMessage) and getattr(message, "tool_calls", None)
    )


def _aggregate(state: State) -> dict:
    """汇总节点：工具路径取最后一条 AI 消息，其余路径透传 worker 结果。"""
    print(">>> aggregate reached")
    messages = state.get("messages") or []
    if messages:
        last = messages[-1]
        if getattr(last, "tool_calls", None):
            return {
                "result": (
                    f"已达到工具调用上限（{MAX_TOOL_ROUNDS} 轮），"
                    "未能得到最终答案，请缩小问题范围后重试。"
                )
            }
        content = str(last.content).strip()
        if content:
            return {"result": content}
        return {"result": "工具调用已完成，但模型没有返回可展示的内容。"}
    return {"result": state.get("result", "")}


def _router(state: State) -> str:
    """条件路由：根据 supervisor 给出的 task_type 决定下一步去哪个节点。"""
    task_type = state.get("task_type", "unknown")
    return task_type if task_type in TASK_ROUTES else "unknown"


def _after_tool_agent(state: State) -> str:
    """工具智能体之后：还有 tool_calls 且未超上限就去执行工具，否则汇总。"""
    messages = state.get("messages") or []
    last = messages[-1] if messages else None
    has_tool_calls = bool(getattr(last, "tool_calls", None))
    if has_tool_calls and _tool_call_rounds(state) <= MAX_TOOL_ROUNDS:
        return "tools"
    return "aggregate"


def build_graph(tools: list | None = None):
    """把各节点和边组装成一张可运行的图。

    tools 参数仅供测试注入假工具；默认使用真实工具列表。
    """
    tool_list = list(tools) if tools is not None else TOOLS

    builder = StateGraph(State)

    builder.add_node("supervisor", _supervisor)
    for name in WORKER_PROMPTS:
        builder.add_node(name, _make_worker(name))
    builder.add_node("unknown", _unknown)
    builder.add_node("tool_agent", _make_tool_agent(tool_list))
    builder.add_node("tools", ToolNode(tool_list))
    builder.add_node("aggregate", _aggregate)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", _router, TASK_ROUTES)
    for name in WORKER_PROMPTS:
        builder.add_edge(name, "aggregate")
    builder.add_edge("unknown", "aggregate")
    builder.add_conditional_edges(
        "tool_agent",
        _after_tool_agent,
        {"tools": "tools", "aggregate": "aggregate"},
    )
    builder.add_edge("tools", "tool_agent")
    builder.add_edge("aggregate", END)

    return builder.compile()

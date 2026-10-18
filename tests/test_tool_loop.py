"""工具调用循环测试：假 LLM + 假工具，验证 tool_agent <-> tools 多轮循环。"""
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

import graph as graph_module


@tool
def fake_search(query: str) -> str:
    """返回固定的搜索结果。"""
    return f"关于「{query}」的搜索结果：LangGraph 是一个编排框架。"


class FakeLLM:
    def __init__(self, handler):
        self._handler = handler

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages):
        return self._handler(messages)


def _install_fake_llm(monkeypatch, tool_handler):
    """supervisor 的输入是字符串，tool_agent 的输入是消息列表，据此区分。"""

    def fake_build_llm():
        def handler(messages):
            if isinstance(messages, str):
                return AIMessage(content="search")
            return tool_handler(messages)

        return FakeLLM(handler)

    monkeypatch.setattr(graph_module, "build_llm", fake_build_llm)


def _initial_state():
    return {
        "task": "搜索 LangGraph",
        "task_type": "",
        "result": "",
        "messages": [],
    }


def _tool_call(query="LangGraph"):
    return AIMessage(
        content="",
        tool_calls=[{
            "name": "fake_search",
            "args": {"query": query},
            "id": "call_1",
            "type": "tool_call",
        }],
    )


def test_tool_loop_runs_tool_then_answers(monkeypatch):
    replies = {"count": 0}

    def tool_handler(_messages):
        replies["count"] += 1
        if replies["count"] == 1:
            return _tool_call()
        return AIMessage(content="最终答案：LangGraph 是一个编排框架。")

    _install_fake_llm(monkeypatch, tool_handler)
    graph = graph_module.build_graph(tools=[fake_search])

    nodes = [
        next(iter(update))
        for update in graph.stream(_initial_state(), stream_mode="updates")
    ]
    assert nodes == ["supervisor", "tool_agent", "tools", "tool_agent", "aggregate"]

    replies["count"] = 0  # 重跑一次，收集最终 state
    final = graph.invoke(_initial_state())
    assert final["task_type"] == "search"
    assert final["result"] == "最终答案：LangGraph 是一个编排框架。"
    # Human + AI(tool_calls) + Tool + AI(final)
    assert len(final["messages"]) == 4
    assert sum(isinstance(m, ToolMessage) for m in final["messages"]) == 1


def test_tool_loop_stops_at_max_rounds(monkeypatch):
    _install_fake_llm(monkeypatch, lambda _messages: _tool_call())
    monkeypatch.setattr(graph_module, "MAX_TOOL_ROUNDS", 2)
    graph = graph_module.build_graph(tools=[fake_search])

    nodes = [
        next(iter(update))
        for update in graph.stream(_initial_state(), stream_mode="updates")
    ]
    assert nodes == [
        "supervisor",
        "tool_agent", "tools",
        "tool_agent", "tools",
        "tool_agent",
        "aggregate",
    ]

    final = graph.invoke(_initial_state())
    assert sum(isinstance(m, ToolMessage) for m in final["messages"]) == 2
    assert "上限" in final["result"]

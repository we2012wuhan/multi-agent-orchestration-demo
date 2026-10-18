"""图状态（State）：在整张图里流转的共享数据。

LangGraph 的每个节点（node）接收并返回这个 state 的「部分更新」，
框架会自动合并，节点之间就靠它传递数据。

`messages` 使用 add_messages reducer：节点返回新消息列表时，框架会自动
追加到已有消息后面，而不是覆盖。工具调用循环依赖这一点保留完整对话。
"""
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class State(TypedDict):
    task: str        # 用户原始请求
    task_type: str   # supervisor 分类：translate / summarize / write / search / unknown
    result: str      # 最终汇总结果
    messages: Annotated[list[AnyMessage], add_messages]  # 工具调用的对话历史

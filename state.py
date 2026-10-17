"""图状态（State）：在整张图里流转的共享数据。

LangGraph 的每个节点（node）接收并返回这个 state 的「部分更新」，
框架会自动合并，节点之间就靠它传递数据。
"""
from typing import TypedDict


class State(TypedDict):
    task: str        # 用户原始请求
    task_type: str   # supervisor 分类出的任务类型：translate / summarize / write / unknown
    result: str      # 最终汇总结果

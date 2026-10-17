"""LLM 构造与专职 worker 的定义。

这里用 langchain-openai 的 ChatOpenAI 指向 DeepSeek（OpenAI 兼容接口）。
换通义 / GLM / Kimi 等任何 OpenAI 兼容服务，只需改 base_url 和 model。
"""
import os

from langchain_openai import ChatOpenAI

DEFAULT_BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"


def build_llm() -> ChatOpenAI:
    """构造一个指向 DeepSeek 的 LLM 实例。"""
    return ChatOpenAI(
        base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        model=MODEL,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        temperature=0,  # 0 = 更稳定，适合分类 / 翻译这类确定型任务
    )


# 每个专职 worker 的「人设」（system prompt）。
# 新增 worker = 在这里加一行 + 在 graph.py 里加一个节点。
WORKER_PROMPTS = {
    "translate": "你是一名专业翻译，把用户给出的内容翻译成英文，只输出译文本身，不要解释。",
    "summarize": "你是一名编辑，用简洁的中文总结用户给出的内容要点，只输出总结，不要解释。",
    "write": "你是一名文案写手，根据用户要求撰写 / 扩写内容，只输出成稿，不要解释。",
}

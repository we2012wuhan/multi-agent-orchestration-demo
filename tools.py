"""工具：阿里云信息查询服务（IQS）Web Search。

IQS 是阿里云百炼体系下的联网搜索接口：

    POST https://cloud-iqs.aliyuncs.com/search/unified
    Authorization: Bearer <IQS_API_KEY>

工具内部负责：

- 读取 IQS_API_KEY（缺失时返回可读错误，而不是抛异常打断整张图）
- 调用统一搜索接口（默认 LiteAdvanced 引擎）
- 把 pageItems 整理成紧凑文本，附带标题 / 链接 / 日期 / 摘要
"""
import os
from datetime import datetime
from typing import Literal

import httpx
from langchain_core.tools import tool

DEFAULT_BASE_URL = "https://cloud-iqs.aliyuncs.com/search/unified"
DEFAULT_ENGINE_TYPE = "LiteAdvanced"
MAX_RESULTS = 5
MAX_RESULT_CHARS = 6000
MAX_SNIPPET_CHARS = 400

TimeRange = Literal["NoLimit", "OneDay", "OneWeek", "OneMonth", "OneYear"]

_ERROR_HINTS = {
    400: "请求参数错误",
    401: "API Key 无效或未授权",
    403: "无访问权限或额度不足",
    429: "请求过于频繁或额度不足",
}


def _format_publish_time(value) -> str:
    """IQS 的 publishTime 是毫秒时间戳，也兼容字符串。"""
    if value in (None, "", 0):
        return ""
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000).strftime("%Y-%m-%d")
        except (OSError, ValueError, OverflowError):
            return ""
    return str(value)[:10]


def _format_item(index: int, item: dict) -> str:
    title = (item.get("title") or "无标题").strip()
    url = (item.get("link") or item.get("url") or "").strip()
    site = (item.get("hostname") or "").strip()
    date = _format_publish_time(item.get("publishTime") or item.get("publishedTime"))
    snippet = (
        item.get("summary") or item.get("snippet") or item.get("mainText") or ""
    ).strip()
    if len(snippet) > MAX_SNIPPET_CHARS:
        snippet = snippet[:MAX_SNIPPET_CHARS] + "…"

    heading = f"{index}. {title}" + (f"（{site}）" if site else "")
    lines = [heading]
    if url:
        lines.append(f"   链接：{url}")
    if date:
        lines.append(f"   日期：{date}")
    if snippet:
        lines.append(f"   摘要：{snippet}")
    return "\n".join(lines)


def _extract_results(body: dict) -> list[dict]:
    """兼容扁平返回与 {data: {pageItems: ...}} 包装。"""
    candidates = [body.get("pageItems")]
    data = body.get("data")
    if isinstance(data, dict):
        candidates.append(data.get("pageItems"))
    for candidate in candidates:
        if isinstance(candidate, list):
            return candidate
    return []


@tool
def web_search(query: str, time_range: TimeRange = "NoLimit") -> str:
    """搜索互联网获取公开信息。query 为搜索词；time_range 控制时效范围。"""
    api_key = os.getenv("IQS_API_KEY")
    if not api_key:
        return "搜索失败：未配置 IQS_API_KEY，请在 .env 中设置后重试。"

    url = os.getenv("IQS_BASE_URL", DEFAULT_BASE_URL)
    engine_type = os.getenv("IQS_ENGINE_TYPE", DEFAULT_ENGINE_TYPE)
    payload = {
        "query": query,
        "engineType": engine_type,
        "contents": {
            "mainText": False,
            "markdownText": False,
            "summary": False,
            "rerankScore": False,
        },
        "advancedParams": {"numResults": MAX_RESULTS},
        "timeRange": time_range,
    }
    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    except httpx.HTTPError as exc:
        return f"搜索失败：请求 IQS 接口时出错（{type(exc).__name__}）。"

    if resp.status_code != 200:
        hint = _ERROR_HINTS.get(resp.status_code, "请稍后重试")
        return f"搜索失败：IQS 接口返回 HTTP {resp.status_code}（{hint}）。"

    try:
        body = resp.json()
    except ValueError:
        return "搜索失败：IQS 接口返回了无法解析的响应。"

    code = body.get("code")
    if code not in (None, 0, 200, "0", "200"):
        message = body.get("message") or "未知错误"
        return f"搜索失败：IQS 接口返回错误 {code}（{message}）。"

    items = _extract_results(body)
    if not items:
        return f"未找到与「{query}」相关的搜索结果。"

    text = "\n\n".join(
        _format_item(index, item) for index, item in enumerate(items, 1)
    )
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + "\n…（结果已截断）"
    return f"搜索「{query}」得到 {len(items)} 条结果：\n\n{text}"

"""阿里云 IQS 搜索工具测试：mock HTTP，不调用真实 API、不消耗额度。"""
import tools as tools_module


class FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("invalid json")
        return self._body


def test_web_search_formats_results(monkeypatch):
    monkeypatch.setenv("IQS_API_KEY", "test-key")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json
        return FakeResponse(200, {
            "requestId": "req-1",
            "pageItems": [{
                "title": "LangGraph 官方文档",
                "link": "https://example.com/langgraph",
                "snippet": "摘要内容",
                "publishTime": 1759310400000,
                "hostname": "example.com",
            }],
        })

    monkeypatch.setattr(tools_module.httpx, "post", fake_post)
    result = tools_module.web_search.invoke({
        "query": "LangGraph",
        "time_range": "OneWeek",
    })

    assert "LangGraph 官方文档" in result
    assert "https://example.com/langgraph" in result
    assert "2025-10-01" in result
    assert "摘要内容" in result
    assert "example.com" in result

    assert captured["url"] == tools_module.DEFAULT_BASE_URL
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["payload"]["query"] == "LangGraph"
    assert captured["payload"]["timeRange"] == "OneWeek"
    assert captured["payload"]["engineType"] == tools_module.DEFAULT_ENGINE_TYPE
    assert captured["payload"]["advancedParams"]["numResults"] == tools_module.MAX_RESULTS


def test_web_search_missing_key(monkeypatch):
    monkeypatch.delenv("IQS_API_KEY", raising=False)
    result = tools_module.web_search.invoke({"query": "随便搜搜"})
    assert "IQS_API_KEY" in result


def test_web_search_quota_error(monkeypatch):
    monkeypatch.setenv("IQS_API_KEY", "test-key")
    monkeypatch.setattr(
        tools_module.httpx, "post", lambda *a, **k: FakeResponse(429)
    )
    result = tools_module.web_search.invoke({"query": "随便搜搜"})
    assert "429" in result
    assert "额度" in result


def test_web_search_no_results(monkeypatch):
    monkeypatch.setenv("IQS_API_KEY", "test-key")
    monkeypatch.setattr(
        tools_module.httpx,
        "post",
        lambda *a, **k: FakeResponse(200, {"requestId": "req-2", "pageItems": []}),
    )
    result = tools_module.web_search.invoke({"query": "不存在的词"})
    assert "未找到" in result

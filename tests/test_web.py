"""Web 接口测试：不调用真实 DeepSeek，用假模型验证流式事件。"""
import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

import graph as graph_module
import web.app as web_app


@pytest.fixture
def client():
    with TestClient(web_app.app) as c:
        yield c


def _install_fake_graph(monkeypatch, responses):
    """把图里的 LLM 换成按顺序返回固定文本的假模型。"""
    fake = FakeListChatModel(responses=responses)
    monkeypatch.setattr(graph_module, "build_llm", lambda: fake)
    monkeypatch.setattr(web_app, "GRAPH", graph_module.build_graph())


def _collect_events(client, run_id):
    events = []
    with client.stream("GET", f"/api/runs/{run_id}/stream") as stream:
        for line in stream.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    return events


def test_index_serves_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "多智能体编排演示" in resp.text


def test_missing_key_rejected(client, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    resp = client.post("/api/runs", json={"task": "翻译：你好"})
    assert resp.status_code == 400
    assert "DEEPSEEK_API_KEY" in resp.json()["detail"]


def test_empty_task_rejected(client, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    resp = client.post("/api/runs", json={"task": "   "})
    assert resp.status_code == 400


def test_stream_unknown_run_returns_404(client):
    resp = client.get("/api/runs/not-exist/stream")
    assert resp.status_code == 404


def test_translate_run_streams_events(client, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    _install_fake_graph(monkeypatch, ["translate", "Hello world"])

    resp = client.post("/api/runs", json={"task": "翻译：你好世界"})
    assert resp.status_code == 200

    events = _collect_events(client, resp.json()["run_id"])
    done = next(e for e in events if e["type"] == "done")
    assert done["task_type"] == "translate"
    assert done["result"] == "Hello world"

    node_order = [e["node"] for e in events if e["type"] == "node_end"]
    assert node_order == ["supervisor", "translate", "aggregate"]
    starts = [e["node"] for e in events if e["type"] == "node_start"]
    assert starts == ["supervisor", "translate", "aggregate"]


def test_unknown_task_skips_worker(client, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    _install_fake_graph(monkeypatch, ["unknown"])

    resp = client.post("/api/runs", json={"task": "帮我算 1+1"})
    assert resp.status_code == 200

    events = _collect_events(client, resp.json()["run_id"])
    done = next(e for e in events if e["type"] == "done")
    assert done["task_type"] == "unknown"
    assert "无法处理" in done["result"]

    node_order = [e["node"] for e in events if e["type"] == "node_end"]
    assert node_order == ["supervisor", "unknown", "aggregate"]

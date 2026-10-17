# multi-agent-orchestration-demo

一个用于**学习和测试多智能体调度 / LLM 智能体编排**的最小可运行 demo。

用 [LangGraph](https://github.com/langchain-ai/langgraph) 搭建一张编排图：主管 agent 接收自然语言任务，判断类型后路由给对应的专职 worker agent，worker 执行后统一汇总返回。

```
START -> supervisor --+--> translate --+
                      +--> summarize --+--> aggregate -> END
                      +--> write ------+
                      +--> unknown ----+
```

- `supervisor`：用 LLM 把任务归类为 translate / summarize / write / unknown
- `translate` / `summarize` / `write`：三个专职 worker，各自带独立 system prompt
- `unknown`：无法识别类型时返回明确提示，不调用 LLM
- `aggregate`：汇总结果（当前为单 worker 直通，后续多 worker 场景在此拼接）

## 快速开始

```bash
# 1. 创建虚拟环境并安装依赖（Windows）
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

# 2. 配置 API Key：复制模板并填入你的 DeepSeek 密钥
cp .env.example .env
# 编辑 .env，把 DEEPSEEK_API_KEY 换成真实值

# 3. 运行
.venv/Scripts/python.exe main.py                      # 默认翻译示例
.venv/Scripts/python.exe main.py "你的任务内容"         # 自定义任务
```

## 项目结构

| 文件 | 作用 |
|---|---|
| `main.py` | 入口：加载 `.env`、调用图、打印结果 |
| `graph.py` | 编排图定义：节点、条件边、路由 |
| `agents.py` | DeepSeek LLM 构造与 worker system prompt |
| `state.py` | 图共享状态 `State`（`task` / `task_type` / `result`） |
| `.env.example` | 配置模板（真实 `.env` 不入库） |

## 换 LLM 供应商

`agents.py` 用 `ChatOpenAI` 指向 DeepSeek 的 OpenAI 兼容接口。换通义 / GLM / Kimi 等任何兼容服务，只需修改 `.env` 里的 `DEEPSEEK_BASE_URL` 和 `agents.py` 中的 `MODEL` 常量。

## 规划文档

本项目使用 [OpenSpec](https://github.com/Fission-AI/OpenSpec) 做 spec-driven 开发，规划文档位于：

- `openspec/changes/multi-agent-orchestration-demo/` — 当前变更（proposal / design / specs / tasks）

## 范围

本 demo 只覆盖「主管路由 → 单 worker 执行 → 汇总」的最小闭环。并发执行、优先级队列、重试与超时、多轮循环路由、checkpoint 等进阶调度策略属于后续迭代范围。

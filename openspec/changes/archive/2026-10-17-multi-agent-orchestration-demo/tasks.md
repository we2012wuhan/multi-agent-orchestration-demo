# Tasks

## 1. 项目骨架与依赖

- [x] 1.1 创建模块目录结构（`state.py` / `graph.py` / `agents.py` / `main.py`），验证四个文件均存在
- [x] 1.2 编写 `requirements.txt`（`langgraph`、`langchain-openai`、`langchain-core`、`python-dotenv`）并安装，验证 `pip install -r requirements.txt` 成功且 `python -c "import langgraph"` 无报错
- [x] 1.3 编写 `.env.example`（含 `DEEPSEEK_API_KEY` 与 `DEEPSEEK_BASE_URL`）和 `.gitignore`（忽略 `.env` 与 `.venv`），验证 `.env.example` 含 `DEEPSEEK_API_KEY` 字段且 `.gitignore` 含 `.env`

## 2. 核心编排实现

- [x] 2.1 实现 `state.py` 的 State schema（`task` / `task_type` / `result` 字段），验证 `python -c "from state import State"` 导入无误
- [x] 2.2 实现 `agents.py`：用 `ChatOpenAI(base_url=..., model="deepseek-chat")` 构造 LLM，并实现 translate / summarize / write 三个 worker，验证能成功实例化 LLM 与三个 worker
- [x] 2.3 实现 `graph.py`：supervisor 节点（归类 task_type）+ 条件边路由到对应 worker + aggregate 汇总节点，验证 `graph.compile()` 不抛错
- [x] 2.4 实现 `main.py` 入口：用 `python-dotenv` 读取 `.env`、构造并调用图、打印结果，验证缺少 `DEEPSEEK_API_KEY` 时给出清晰报错

## 3. 端到端验证

- [x] 3.1 运行翻译类示例任务，验证返回翻译后的结果（对应 specs 的「翻译任务路由」场景）
- [x] 3.2 运行总结类示例任务，验证返回总结结果（对应 specs 的「总结任务路由」场景）
- [x] 3.3 运行一个无法识别类型的任务，验证返回「无法处理该类型」的明确提示（对应 specs 的「未知类型」场景）

## Workflow follow-up

- 实现并验证通过后，运行 `/openspec-archive-change`（或让我归档），把 `agent-orchestration` 能力同步进 `openspec/specs/`。

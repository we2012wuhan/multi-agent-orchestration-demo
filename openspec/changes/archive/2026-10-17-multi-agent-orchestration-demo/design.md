# Design

## Context

全新项目（当前无代码），Python 技术栈，已初始化 OpenSpec 根目录。动机见 proposal.md - Why。约束：这是学习/测试项目，第一版只求「最小可运行」，重点是看清主管→worker 的编排链路，而非生产级的健壮性或性能。

## Goals / Non-Goals

**Goals:**
- 用 LangGraph 跑通一条「主管路由 → worker 执行 → 汇总返回」的最小闭环。
- 用 DeepSeek API 驱动智能体，无需自建 LLM 服务。
- 结构清晰、易读，方便作为后续扩展调度策略的起点。

**Non-Goals:**
- 不做并发/并行执行、优先级队列、重试与超时、动态多轮路由等进阶调度。
- 不做结果持久化、checkpoint、流式输出、Web/API 服务。
- 不做多智能体之间自由对话（那是 AutoGen 的强项，不是本 demo 目标）。

## Decisions

**1. 用 LangGraph 的 `StateGraph` + 条件边实现「主管路由」**
- 一个共享的 `State`（TypedDict，含 `task`、`task_type`、`result`）贯穿整张图。
- `supervisor` 节点调用 LLM 把任务归类（translate / summarize / write），写回 `task_type`。
- 用 `add_conditional_edges` 根据 `task_type` 路由到对应 worker；worker 执行后回到 `aggregate` 节点汇总，再 `END`。
- 备选：固定线性流水线（writer→translator）—— 简单，但体现不出「调度/路由」；备选：AutoGen 群聊 —— 交互丰富但封装过重、不利于看底层机制。选 LangGraph 图编排最贴合「学习调度」目标。

**2. 用 `langchain-openai` 的 `ChatOpenAI` 指向 DeepSeek**
- DeepSeek 是 OpenAI 兼容接口，直接 `ChatOpenAI(base_url="https://api.deepseek.com", model="deepseek-chat", api_key=...)`。
- 好处：只学一个通用「把 ChatOpenAI 指向任意兼容服务」的套路，后续换通义/GLM/Kimi 零改动。
- 备选：`langchain-deepseek` 的 `ChatDeepSeek` —— 官方封装、更省事，但多一层抽象；本 demo 用前者以贴近通用实践，`.env` 里留 `DEEPSEEK_BASE_URL` 便于切换。

**3. 三个专职 worker：translate / summarize / write**
- 每个 worker 是图中的一个独立节点，内部各自构造带 system prompt 的 LLM 调用，职责单一、易于逐个替换或增加。
- worker 数量固定为 3，覆盖「路由」演示所需的最少类型；新增类型 = 新增一个节点 + 一条条件边。

**4. 配置与目录结构**
- API Key 从 `.env` 读取（`python-dotenv`），提供 `.env.example` 作模板，`.env` 不提交。
- 单入口脚本 + 拆分模块：`main.py`（入口/示例）、`graph.py`（图与节点定义）、`state.py`（State schema）、`agents.py`（worker 实现），避免把所有东西堆在一个文件。

## Risks / Trade-offs

- **[DeepSeek 调用有网络延迟与成本]** → demo 默认单次路由、少轮调用；示例任务保持短小。
- **[API Key 泄露风险]** → `.env` 加入 `.gitignore`，只提交 `.env.example`。
- **[LangGraph / langchain 版本迭代快，API 可能变动]** → `requirements.txt` 固定主版本；把「跑通」作为第一验收标准，遇到 breaking change 以能运行为准调整。
- **[模型名可能随 DeepSeek 调整]** → 模型名集中在 `agents.py` 一处，改一个常量即可。

## Open Questions

- 是否后续引入流式输出与多轮「主管再次决策」的循环路由 —— 不影响本 demo 的规格与任务拆解，可在下个 change 再定。

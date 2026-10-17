# Proposal

## Why

这是一个学习/测试性质的项目，目标是搞懂「多智能体调度 / LLM 智能体编排」的核心机制。目前项目还是空壳（无代码、无规格），需要一个最小可运行的 demo 把「主管 agent 拆解并分派任务 → 子 agent 执行 → 汇总结果」这条最基础的编排链路跑通，作为后续叠加更复杂调度策略（优先级、并发、重试、动态路由等）的地基。

## What Changes

- 搭建一个 Python 项目骨架，使用 **LangGraph** + **DeepSeek API** 驱动智能体。
- 实现一个主管 agent + 多个专职 worker agent 的编排图：主管接收自然语言任务、判断类型并路由到对应 worker，worker 执行后由主管汇总返回。
- 提供可运行的入口脚本、`.env` 配置（`DEEPSEEK_API_KEY`）与示例输入，保证「开箱即跑」。
- 落地依赖清单（`requirements.txt`）与最小目录结构。

## Capabilities

### New Capabilities

- `agent-orchestration`: 系统接收自然语言任务，由主管 agent 路由到专职 worker agent 执行，并汇总结果返回。这是本项目长期要持续演进的核心能力（后续的调度策略、并发控制、故障处理都归它管）。

### Modified Capabilities

<!-- 无现有能力被修改 -->

## Impact

- **新增依赖**：`langgraph`、`langchain-deepseek`（或 `langchain-openai` + DeepSeek base_url）、`langchain-core`、`python-dotenv`。
- **新增文件**：图定义、worker/supervisor 节点、入口脚本、`requirements.txt`、`.env.example`。
- **运行前提**：需要有效的 `DEEPSEEK_API_KEY`。
- **不影响现有代码**：项目当前无既有实现，纯增量。

# multi-agent-orchestration-demo

一个用于**学习和测试多智能体调度 / LLM 智能体编排**的最小可运行 demo。

用 [LangGraph](https://github.com/langchain-ai/langgraph) 搭建一张编排图：主管 agent 接收自然语言任务，判断类型后路由给对应的专职 worker agent，worker 执行后统一汇总返回。

```
START -> supervisor --+--> translate --+
                      +--> summarize --+
                      +--> write ------+
                      +--> unknown ----+--> aggregate -> END
                      +--> tool_agent <-> tools（多轮工具循环）
```

- `supervisor`：用 LLM 把任务归类为 translate / summarize / write / search / unknown
- `translate` / `summarize` / `write`：三个专职 worker，各自带独立 system prompt
- `tool_agent`：工具智能体，通过原生 function calling 调用阿里云 IQS 联网搜索
- `tools`：执行工具调用；只要模型还在请求工具，就回到 `tool_agent` 继续循环
- `unknown`：无法识别类型时返回明确提示，不调用 LLM
- `aggregate`：汇总结果（工具路径取模型最终回答，其余路径透传 worker 结果）

## 快速开始

```bash
# 1. 创建虚拟环境并安装依赖（Windows）
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

# 2. 配置 API Key：复制模板并填入你的密钥
cp .env.example .env
# 编辑 .env：
#   DEEPSEEK_API_KEY  必填，主管分类与各 worker 使用
#   IQS_API_KEY       联网搜索任务需要（阿里云信息查询服务 IQS 控制台）

# 3. 运行（命令行）
.venv/Scripts/python.exe main.py                      # 默认翻译示例
.venv/Scripts/python.exe main.py "你的任务内容"         # 自定义任务

# 4. 运行（网页版）
.venv/Scripts/python.exe run.py            # 启动后控制台会打印访问地址
# 默认访问 http://127.0.0.1:8000
# 可选：--port 8080 指定端口；--reload 开发模式自动重启
```

## 网页版

页面提供：

- **任务输入**：手动输入，或点击示例按钮快速填充
- **实时执行流程**：随执行进度高亮当前节点（supervisor → worker → aggregate）
- **执行记录**：按时间顺序展示每一步的分类结果与输出
- **最终结果**：展示路由到的任务类型和汇总结果

后端是 FastAPI，通过 SSE 把 LangGraph 每个节点的执行进度实时推送给前端；前端为无构建步骤的原生 HTML/CSS/JS。联网搜索任务会展示每一轮的工具调用参数、执行结果和轮次，最终回答中的链接可直接点击。

## 工具调用（联网搜索）

- 搜索服务：[阿里云信息查询服务 IQS](https://help.aliyun.com/zh/document_detail/2870227.html)，`POST https://cloud-iqs.aliyuncs.com/search/unified`
- 鉴权：IQS 控制台「凭证管理」创建的 API Key，请求头 `Authorization: Bearer <IQS_API_KEY>`
- 引擎：默认 `LiteAdvanced`，可通过 `IQS_ENGINE_TYPE` 切换 `GenericAdvanced` / `Generic` / `Deep`
- 调用方式：DeepSeek **原生 function calling**（`bind_tools`）+ LangGraph `ToolNode`
- 循环策略：模型可以多轮检索（一轮可并行发起多个查询），最多 **6 轮**，超过后返回明确提示
- 容错：未配置 key、鉴权失败（401）、额度或限流（429）、网络错误都会转成工具结果交还给模型说明，不会中断整张图
- 测试：`tests/test_tools.py` 与 `tests/test_tool_loop.py` 全部使用 mock，不消耗真实额度

> 若 IQS 返回 401 / 429，依次检查 `IQS_API_KEY` 是否正确、账户是否有可用额度或是否触发限流。

运行测试（使用假模型，不调用真实 API、不消耗额度）：

```bash
.venv/Scripts/python.exe -m pytest -q
```

## 查看图结构

```bash
.venv/Scripts/python.exe show_graph.py             # 终端 ASCII 图
.venv/Scripts/python.exe show_graph.py --mermaid   # 输出 Mermaid 文本（可粘贴到 mermaid.live）
.venv/Scripts/python.exe show_graph.py --png       # 导出 graph.png（需要联网）
```

## 项目结构

| 文件 | 作用 |
|---|---|
| `main.py` | 入口：加载 `.env`、调用图、打印结果 |
| `graph.py` | 编排图定义：节点、条件边、路由 |
| `agents.py` | DeepSeek LLM 构造与 worker system prompt |
| `tools.py` | 阿里云 IQS 联网搜索工具（原生 function calling 的工具定义） |
| `state.py` | 图共享状态 `State`（`task` / `task_type` / `result` / `messages`） |
| `web/app.py` | FastAPI 应用：运行任务、SSE 流式推送、托管前端 |
| `web/static/` | 网页前端（HTML / CSS / JS） |
| `tests/` | Web 接口测试（使用假模型） |
| `.env.example` | 配置模板（真实 `.env` 不入库） |

## 换 LLM 供应商

`agents.py` 用 `ChatOpenAI` 指向 DeepSeek 的 OpenAI 兼容接口。换通义 / GLM / Kimi 等任何兼容服务，只需修改 `.env` 里的 `DEEPSEEK_BASE_URL` 和 `agents.py` 中的 `MODEL` 常量。

## 规划文档

本项目使用 [OpenSpec](https://github.com/Fission-AI/OpenSpec) 做 spec-driven 开发，规划文档位于：

- `openspec/changes/archive/2026-10-17-multi-agent-orchestration-demo/` — 已归档变更（proposal / design / specs / tasks）
- `openspec/specs/agent-orchestration/spec.md` — 已同步的能力规范

## 范围

本 demo 覆盖「主管路由 → 单 worker / 工具智能体执行 → 汇总」的最小闭环，包含原生 function calling 与多轮工具循环。并发执行、优先级队列、重试与超时、多 worker 并行汇总、checkpoint 等进阶调度策略属于后续迭代范围。

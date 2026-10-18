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

后端是 FastAPI，通过 SSE 把 LangGraph 每个节点的执行进度实时推送给前端；前端为无构建步骤的原生 HTML/CSS/JS。

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
| `state.py` | 图共享状态 `State`（`task` / `task_type` / `result`） |
| `web/app.py` | FastAPI 应用：运行任务、SSE 流式推送、托管前端 |
| `web/static/` | 网页前端（HTML / CSS / JS） |
| `tests/` | Web 接口测试（使用假模型） |
| `.env.example` | 配置模板（真实 `.env` 不入库） |

## 换 LLM 供应商

`agents.py` 用 `ChatOpenAI` 指向 DeepSeek 的 OpenAI 兼容接口。换通义 / GLM / Kimi 等任何兼容服务，只需修改 `.env` 里的 `DEEPSEEK_BASE_URL` 和 `agents.py` 中的 `MODEL` 常量。

## 规划文档

本项目使用 [OpenSpec](https://github.com/Fission-AI/OpenSpec) 做 spec-driven 开发，规划文档位于：

- `openspec/changes/multi-agent-orchestration-demo/` — 当前变更（proposal / design / specs / tasks）

## 范围

本 demo 只覆盖「主管路由 → 单 worker 执行 → 汇总」的最小闭环。并发执行、优先级队列、重试与超时、多轮循环路由、checkpoint 等进阶调度策略属于后续迭代范围。

const NODE_LABELS = {
  supervisor: "主管分类",
  translate: "翻译",
  summarize: "总结",
  write: "撰写",
  unknown: "未知类型",
  aggregate: "汇总",
};

const taskEl = document.getElementById("task");
const runBtn = document.getElementById("run");
const timelineEl = document.getElementById("timeline");
const resultEl = document.getElementById("result");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("form-error");
const flowNodes = Array.from(document.querySelectorAll(".flow-node[data-node]"));

let source = null;
let finished = false;

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.className = `status ${cls}`;
}

function resetUI() {
  finished = false;
  if (source) {
    source.close();
    source = null;
  }
  timelineEl.innerHTML = "";
  resultEl.className = "result empty";
  resultEl.textContent = "运行中…";
  errorEl.classList.add("hidden");
  flowNodes.forEach((n) => n.classList.remove("active", "done"));
  runBtn.disabled = true;
  setStatus("运行中", "running");
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.classList.remove("hidden");
}

function addTimeline(kind, title, detail) {
  const li = document.createElement("li");
  li.className = kind;
  const time = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  li.innerHTML = `<span class="time">${time}</span><span class="title"></span><span class="detail"></span>`;
  li.querySelector(".title").textContent = title;
  li.querySelector(".detail").textContent = detail || "";
  timelineEl.appendChild(li);
  timelineEl.scrollTop = timelineEl.scrollHeight;
}

function nodeEl(name) {
  return flowNodes.find((n) => n.dataset.node === name);
}

function activateNode(name) {
  const el = nodeEl(name);
  if (!el) return;
  el.classList.remove("done");
  el.classList.add("active");
}

function finishNode(name) {
  const el = nodeEl(name);
  if (!el) return;
  el.classList.remove("active");
  el.classList.add("done");
}

function handleEvent(ev) {
  switch (ev.type) {
    case "run_started":
      addTimeline("", "任务已提交", ev.task);
      break;
    case "node_start":
      activateNode(ev.node);
      addTimeline("start", `进入 ${ev.node}`, NODE_LABELS[ev.node] || "");
      break;
    case "node_end": {
      finishNode(ev.node);
      if (ev.node === "supervisor") {
        addTimeline("end", "主管分类", `task_type = ${ev.data.task_type}`);
      } else if (ev.node === "unknown") {
        addTimeline("end", "兜底提示", ev.data.result || "");
      } else if (ev.node !== "aggregate" && ev.data.result) {
        addTimeline("end", `${ev.node} 输出`, ev.data.result);
      }
      break;
    }
    case "done":
      finished = true;
      if (source) {
        source.close();
        source = null;
      }
      resultEl.className = "result";
      resultEl.innerHTML = `<span class="route"></span><div class="body"></div>`;
      resultEl.querySelector(".route").textContent = `路由：${ev.task_type}`;
      resultEl.querySelector(".body").textContent = ev.result;
      addTimeline("done", "执行完成", `task_type = ${ev.task_type}`);
      setStatus("完成", "done");
      runBtn.disabled = false;
      break;
    case "error":
      finished = true;
      if (source) {
        source.close();
        source = null;
      }
      addTimeline("error", "执行出错", ev.message);
      resultEl.className = "result empty";
      resultEl.textContent = `执行失败：${ev.message}`;
      setStatus("出错", "error");
      runBtn.disabled = false;
      break;
    default:
      break;
  }
}

async function run() {
  const task = taskEl.value.trim();
  if (!task) {
    showError("请先输入任务内容");
    return;
  }
  resetUI();

  let runId;
  try {
    const resp = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "请求失败");
    }
    runId = data.run_id;
  } catch (err) {
    addTimeline("error", "提交失败", err.message);
    resultEl.className = "result empty";
    resultEl.textContent = "提交失败，请检查配置后重试。";
    showError(err.message);
    setStatus("出错", "error");
    runBtn.disabled = false;
    return;
  }

  source = new EventSource(`/api/runs/${runId}/stream`);
  source.onmessage = (event) => {
    try {
      handleEvent(JSON.parse(event.data));
    } catch (err) {
      console.error("无法解析事件", event.data, err);
    }
  };
  source.onerror = () => {
    if (finished) return;
    finished = true;
    if (source) {
      source.close();
      source = null;
    }
    addTimeline("error", "连接中断", "与服务器的流式连接已断开");
    resultEl.className = "result empty";
    resultEl.textContent = "连接中断，请重试。";
    setStatus("出错", "error");
    runBtn.disabled = false;
  };
}

runBtn.addEventListener("click", run);

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    taskEl.value = chip.dataset.task;
    taskEl.focus();
  });
});

taskEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    run();
  }
});

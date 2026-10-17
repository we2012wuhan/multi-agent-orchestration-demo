"""入口：加载配置、构造图、跑一个任务。

用法：
    python main.py                              # 跑默认的翻译示例
    python main.py "总结这段内容的要点：..."       # 跑你自己给的任务
"""
import os
import sys

from dotenv import load_dotenv

from graph import build_graph

DEFAULT_TASK = "把下面这句话翻译成英文：今天天气很好，我们一起去公园散步吧。"


def main() -> None:
    load_dotenv()  # 把 .env 里的配置读进环境变量

    # 缺失 API Key 时快速失败，给出清晰提示（对应 specs 的「缺失 Key」场景）
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("错误：未检测到 DEEPSEEK_API_KEY。")
        print("请在项目根目录创建 .env 文件（参考 .env.example），")
        print("写入 DEEPSEEK_API_KEY=你的密钥 后重新运行。")
        sys.exit(1)

    task = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK
    graph = build_graph()

    final = graph.invoke({"task": task, "task_type": "", "result": ""})
    print(f"任务类型：{final['task_type']}")
    print(f"结果：{final['result']}")


if __name__ == "__main__":
    main()

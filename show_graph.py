"""查看 LangGraph 编排图结构。

用法：
    python show_graph.py                 # 终端 ASCII 图（需要 grandalf）
    python show_graph.py --mermaid       # 输出 Mermaid 文本（可粘贴到 mermaid.live）
    python show_graph.py --png           # 导出 PNG 到 graph.png（需要联网）
    python show_graph.py --png out.png   # 导出到指定路径
"""
import argparse

from graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="查看多智能体编排图结构")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--mermaid", action="store_true", help="输出 Mermaid 文本")
    group.add_argument(
        "--png",
        nargs="?",
        const="graph.png",
        metavar="PATH",
        help="导出 PNG（默认 graph.png，需要联网）",
    )
    args = parser.parse_args()

    graph = build_graph().get_graph()

    if args.mermaid:
        print(graph.draw_mermaid())
    elif args.png:
        with open(args.png, "wb") as f:
            f.write(graph.draw_mermaid_png())
        print(f"已生成 {args.png}")
    else:
        print(graph.draw_ascii())


if __name__ == "__main__":
    main()

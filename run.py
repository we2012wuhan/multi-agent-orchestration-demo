"""启动 Web 服务。

用法：
    python run.py                 # http://127.0.0.1:8000
    python run.py --port 8080     # 自定义端口
    python run.py --reload        # 开发模式：改代码自动重启
"""
import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="启动多智能体编排演示 Web 服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    parser.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    parser.add_argument("--reload", action="store_true", help="开发模式，代码变更自动重启")
    args = parser.parse_args()

    # 让 app.py 的启动横幅能拿到真实地址（包括 reload 子进程）
    os.environ["APP_HOST"] = args.host
    os.environ["APP_PORT"] = str(args.port)

    uvicorn.run("web.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()

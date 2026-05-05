#!/usr/bin/env python3
"""
Savage Worlds Star Wars Character Builder.
Default: Tkinter wizard. Use ``python main.py --web`` for the local FastAPI builder.
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Star Wars SWADE character builder")
    parser.add_argument(
        "--web",
        action="store_true",
        help="Run the local FastAPI web UI (http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address for --web (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for --web (default: 8000)",
    )
    args = parser.parse_args()

    if args.web:
        import uvicorn

        uvicorn.run("web_api:app", host=args.host, port=args.port, reload=False)
        return

    from gui import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()

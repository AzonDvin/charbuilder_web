#!/usr/bin/env python3
"""
Savage Worlds Star Wars Character Builder — web UI.
Run:  python main.py
Then open http://127.0.0.1:8000 in your browser.
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Star Wars SWADE character builder")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on file changes")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run("web_api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()

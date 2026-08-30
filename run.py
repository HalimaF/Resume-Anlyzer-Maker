#!/usr/bin/env python3
"""Start the whole app with one command.

Runs the Flask API and a static server for the frontend together, then opens a
browser. Ctrl+C stops both.

    python run.py                # http://localhost:5500
    python run.py --no-browser   # do not open a browser
    python run.py --api-port 5001 --web-port 8080
"""

import argparse
import functools
import http.server
import socket
import socketserver
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Static handler that does not spam the console with one line per asset."""

    def log_message(self, *_args):
        pass

    def end_headers(self):
        # The pages are edited constantly during development; never serve stale.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return probe.connect_ex(("127.0.0.1", port)) != 0


def serve_frontend(port: int) -> None:
    handler = functools.partial(QuietHandler, directory=str(FRONTEND))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), handler) as server:
        server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Career Desk app locally.")
    parser.add_argument("--api-port", type=int, default=5000)
    parser.add_argument("--web-port", type=int, default=5500)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    for label, port in (("API", args.api_port), ("web", args.web_port)):
        if not port_is_free(port):
            print(f"Port {port} is already in use, so the {label} server cannot start.")
            print(f"Stop whatever is using it, or pass --{'api' if label == 'API' else 'web'}-port <other>.")
            return 1

    sys.path.insert(0, str(BACKEND))
    try:
        from app import create_app
    except ImportError as exc:
        print(f"Could not import the backend: {exc}")
        print("Install the dependencies first:  pip install -r backend/requirements.txt")
        return 1

    threading.Thread(target=serve_frontend, args=(args.web_port,), daemon=True).start()

    url = f"http://localhost:{args.web_port}/index.html"
    print("Career Desk")
    print(f"  App  {url}")
    print(f"  API  http://localhost:{args.api_port}/api/health")
    print("  Ctrl+C to stop\n")

    if not args.no_browser:
        # Delay so the browser does not race the servers to the first request.
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    app = create_app()
    try:
        # The reloader would re-run this file and start a second static server.
        app.run(host="127.0.0.1", port=args.api_port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

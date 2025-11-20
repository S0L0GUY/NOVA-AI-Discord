"""Small runner for the NOVA Discord bot.

This file validates required environment variables, starts a tiny
HTTP health endpoint so the service binds a port for platform
health-checks, then starts the Discord bot defined in
`discord_bot.py`.
"""

import sys
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import config
from discord_bot import bot


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    # Silence default logging to keep logs clean
    def log_message(self, format, *args):
        return


def _start_health_server(port: int) -> None:
    try:
        server = HTTPServer(("", port), _HealthHandler)
        print(f"Health server listening on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"Health server failed to start on port {port}: {e}")


if __name__ == "__main__":
    token = config.DISCORD_TOKEN
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your Discord token.")
        sys.exit(1)

    if not config.GENAI_API_KEY:
        print("Error: GENAI_API_KEY not found in environment variables!")
        print("Please create a .env file with your GenAI API key.")
        sys.exit(1)

    # Start a small background HTTP server so the process binds a port.
    # Platform health checks will use `PORT` (common) or `WEB_PORT`,
    # defaulting to 8080 if neither is provided.
    try:
        port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))
    except ValueError:
        port = 8080

    thread = threading.Thread(
        target=_start_health_server, args=(port,), daemon=True
    )
    thread.start()

    bot.run(token)

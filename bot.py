"""Small runner for the NOVA Discord bot.

This file validates required environment variables, starts a tiny
HTTP health endpoint so the service binds a port for platform
health-checks, then starts the Discord bot defined in
`discord_bot.py`.
"""

import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import constants
from discord_bot import bot
from logger import get_logger

logger = get_logger(__name__)


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


def _start_health_server(server_port: int) -> None:
    """Start the health check HTTP server."""
    try:
        logger.info(f"Starting health server on port {server_port}")
        server = HTTPServer(("", server_port), _HealthHandler)
        logger.info(f"✓ Health server listening on port {server_port}")
        server.serve_forever()
    except OSError as e:
        logger.error(
            f"Failed to start health server on port {server_port}: {e}", exc_info=True
        )
    except Exception as e:
        logger.error(f"Unexpected error in health server: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("NOVA Discord Bot Starting")
        logger.info("=" * 60)

        # Validate required environment variables
        token = constants.Secrets.DISCORD_TOKEN
        if not token:
            logger.error("Error: DISCORD_TOKEN not found in environment variables!")
            logger.error("Please create a .env file with your Discord token.")
            print("Error: DISCORD_TOKEN not found in environment variables!")
            print("Please create a .env file with your Discord token.")
            sys.exit(1)
        logger.info("✓ Discord token configured")

        if not constants.Secrets.GENAI_API_KEY:
            logger.error("Error: GENAI_API_KEY not found in environment variables!")
            logger.error("Please create a .env file with your GenAI API key.")
            print("Error: GENAI_API_KEY not found in environment variables!")
            print("Please create a .env file with your GenAI API key.")
            sys.exit(1)
        logger.info("✓ GenAI API key configured")

        # Start a small background HTTP server so the process binds a port.
        # Platform health checks will use `PORT` (common) or `WEB_PORT`,
        # defaulting to 8080 if neither is provided.
        try:
            port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))
        except ValueError:
            port = 8080
            logger.warning(f"Invalid port configuration, using default: {port}")

        logger.info(f"Starting health server thread on port {port}")
        thread = threading.Thread(
            target=_start_health_server, args=(port,), daemon=True
        )
        thread.start()
        logger.debug("Health server thread started")

        logger.info("Starting Discord bot...")
        bot.run(token)

    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Critical error starting bot: {e}", exc_info=True)
        print(f"Critical error: {e}")
        sys.exit(1)

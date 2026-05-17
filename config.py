"""Startup configuration validator for the NOVA Discord bot.

Call `validate_all()` once at the top of bot.py's __main__ block,
before any network or Discord client initialisation. It checks every
required and optional setting, logs a clear diagnosis for each
problem found, and raises ``ConfigValidationError`` (a subclass of
``SystemExit``) so the process exits with code 1 and a concise
setup-guide if anything is wrong.

Usage
-----
    # bot.py
    from config import validate_all
    ...
    if __name__ == "__main__":
        validate_all()          # exits here if config is broken
        bot.run(constants.Secrets.DISCORD_TOKEN)

Public API
----------
    validate_all()              – run every check; raise on first fatal failure
    validate_secrets()          – check DISCORD_TOKEN + GENAI_API_KEY
    validate_llm_config()       – check numeric/boolean LLM knobs
    validate_file_paths()       – check text_files/ assets exist and are readable
    validate_port_config()      – check PORT / WEB_PORT
    check_discord_token_format  – lightweight regex on the token string
    check_genai_key_format      – lightweight regex on the API key string
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import constants
from logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class ConfigValidationError(SystemExit):
    """Raised when one or more required configuration values are missing or
    invalid.  Inherits from SystemExit so an uncaught raise still terminates
    the process, but callers can catch it explicitly to customise teardown."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        # code=1 signals an error exit to the OS / service manager
        super().__init__(1)


# ---------------------------------------------------------------------------
# Result collector
# ---------------------------------------------------------------------------

@dataclass
class _ValidationResult:
    """Accumulates warnings and fatal errors across all checks."""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def warn(self, msg: str) -> None:
        logger.warning(f"  ⚠  {msg}")
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        logger.error(f"  ✗  {msg}")
        self.errors.append(msg)

    def ok(self, msg: str) -> None:
        logger.info(f"  ✓  {msg}")

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


# ---------------------------------------------------------------------------
# Format-level checks (pure functions, no side-effects)
# ---------------------------------------------------------------------------

# Discord bot tokens look like:  MTExxx.Gyyyyy.zzzzzzz
# Three base64url segments separated by dots; the first decodes to a user-id.
_DISCORD_TOKEN_RE = re.compile(
    r'^[A-Za-z0-9_-]{20,30}'   # user-id segment (base64url)
    r'\.[A-Za-z0-9_-]{6,8}'    # timestamp segment
    r'\.[A-Za-z0-9_-]{27,}$'   # HMAC segment
)

# Google AI (Gemini) API keys: "AIza" followed by 35 base64url chars
_GENAI_KEY_RE = re.compile(r'^AIza[0-9A-Za-z_-]{35}$')


def check_discord_token_format(token: str) -> bool:
    """Return True if *token* looks like a valid Discord bot token.

    This is a structural check only — it does **not** make a network
    request.  A token that passes here might still be revoked or belong
    to a different application.
    """
    return bool(_DISCORD_TOKEN_RE.match(token))


def check_genai_key_format(key: str) -> bool:
    """Return True if *key* looks like a Google AI API key."""
    return bool(_GENAI_KEY_RE.match(key))


# ---------------------------------------------------------------------------
# Individual validator functions
# ---------------------------------------------------------------------------

def validate_secrets(result: _ValidationResult) -> None:
    """Validate DISCORD_TOKEN and GENAI_API_KEY."""

    # --- DISCORD_TOKEN ---
    token = constants.Secrets.DISCORD_TOKEN
    if not token:
        result.error(
            "DISCORD_TOKEN is not set.\n"
            "    How to fix: add  DISCORD_TOKEN=<your-token>  to your .env file.\n"
            "    Get a token at: https://discord.com/developers/applications"
        )
    elif not token.strip():
        result.error("DISCORD_TOKEN is set but contains only whitespace.")
    elif not check_discord_token_format(token.strip()):
        # Warn rather than hard-fail: token formats can change; we don't want
        # to break the bot on a format update from Discord's side.
        result.warn(
            "DISCORD_TOKEN does not match the expected format "
            "(MTxxxx.Gyyyyy.zzzzz).  The bot will attempt to start anyway, "
            "but the token may be invalid or copied incorrectly."
        )
    else:
        result.ok("DISCORD_TOKEN is present and format looks valid")

    # --- GENAI_API_KEY ---
    key = constants.Secrets.GENAI_API_KEY
    if not key:
        result.error(
            "GENAI_API_KEY is not set.\n"
            "    How to fix: add  GENAI_API_KEY=<your-key>  to your .env file.\n"
            "    Get a key at: https://aistudio.google.com/app/apikey"
        )
    elif not key.strip():
        result.error("GENAI_API_KEY is set but contains only whitespace.")
    elif not check_genai_key_format(key.strip()):
        result.warn(
            "GENAI_API_KEY does not match the expected Google AI key format "
            "(AIza + 35 chars).  The bot will attempt to start anyway, "
            "but the key may be invalid or belong to a different service."
        )
    else:
        result.ok("GENAI_API_KEY is present and format looks valid")


def validate_llm_config(result: _ValidationResult) -> None:
    """Validate numeric and boolean LLM configuration values."""

    # MAX_HISTORY_MESSAGES – must be a positive integer
    try:
        mhm = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
        if mhm <= 0:
            result.error(
                f"MAX_HISTORY_MESSAGES must be a positive integer, got {mhm!r}.\n"
                "    How to fix: set a value ≥ 1, e.g.  MAX_HISTORY_MESSAGES=20"
            )
        elif mhm > 500:
            result.warn(
                f"MAX_HISTORY_MESSAGES={mhm} is very large and may produce "
                "enormous prompts.  Consider a value ≤ 100."
            )
        else:
            result.ok(f"MAX_HISTORY_MESSAGES = {mhm}")
    except ValueError:
        result.error(
            f"MAX_HISTORY_MESSAGES={os.getenv('MAX_HISTORY_MESSAGES')!r} is not "
            "a valid integer.\n"
            "    How to fix: provide a plain integer, e.g.  MAX_HISTORY_MESSAGES=20"
        )

    # HISTORY_MAX_CHARS – must be a positive integer
    try:
        hmc = int(os.getenv("HISTORY_MAX_CHARS", "3000"))
        if hmc <= 0:
            result.error(
                f"HISTORY_MAX_CHARS must be a positive integer, got {hmc!r}.\n"
                "    How to fix: set a value ≥ 1, e.g.  HISTORY_MAX_CHARS=3000"
            )
        else:
            result.ok(f"HISTORY_MAX_CHARS = {hmc}")
    except ValueError:
        result.error(
            f"HISTORY_MAX_CHARS={os.getenv('HISTORY_MAX_CHARS')!r} is not "
            "a valid integer.\n"
            "    How to fix: provide a plain integer, e.g.  HISTORY_MAX_CHARS=3000"
        )

    # ENABLE_IMAGE_ANALYSIS – must resolve to a recognisable boolean string
    raw_eia = os.getenv("ENABLE_IMAGE_ANALYSIS", "true").strip().lower()
    if raw_eia not in {"true", "false", "1", "0", "yes", "no"}:
        result.warn(
            f"ENABLE_IMAGE_ANALYSIS={os.getenv('ENABLE_IMAGE_ANALYSIS')!r} is not "
            "a recognised boolean value.  Expected: true/false/1/0/yes/no.  "
            "Defaulting to True."
        )
    else:
        result.ok(f"ENABLE_IMAGE_ANALYSIS = {raw_eia}")


def validate_file_paths(result: _ValidationResult) -> None:
    """Check that required text asset files exist and are readable."""

    files_to_check = {
        "System prompt (prompt.txt)": constants.FilePaths.SYSTEM_PROMPT_FILE,
        "Help text (help_text.txt)": constants.FilePaths.HELP_PROMPT_FILE,
    }

    for label, path_str in files_to_check.items():
        p = Path(path_str)
        if not p.exists():
            result.error(
                f"{label} not found at: {path_str}\n"
                f"    How to fix: create the file at that path, or check that\n"
                f"    text_files/ is present relative to the project root."
            )
        elif not p.is_file():
            result.error(
                f"{label} path exists but is not a file: {path_str}"
            )
        elif not os.access(path_str, os.R_OK):
            result.error(
                f"{label} exists but is not readable: {path_str}\n"
                f"    How to fix: run  chmod 644 {path_str}"
            )
        elif p.stat().st_size == 0:
            result.warn(
                f"{label} at {path_str} is empty.  "
                "The bot will start, but behaviour may be unexpected."
            )
        else:
            result.ok(f"{label} found and readable ({p.stat().st_size} bytes)")


def validate_port_config(result: _ValidationResult) -> None:
    """Validate PORT / WEB_PORT health-server configuration."""

    raw_port = os.getenv("PORT") or os.getenv("WEB_PORT")
    if raw_port is None:
        result.ok("PORT / WEB_PORT not set — health server will use default 8080")
        return

    try:
        port = int(raw_port)
    except ValueError:
        result.error(
            f"PORT/WEB_PORT={raw_port!r} is not a valid integer.\n"
            "    How to fix: provide a plain integer, e.g.  PORT=8080"
        )
        return

    if not (1 <= port <= 65535):
        result.error(
            f"PORT/WEB_PORT={port} is outside the valid range 1–65535."
        )
    elif port < 1024:
        result.warn(
            f"PORT/WEB_PORT={port} is a privileged port (< 1024).  "
            "The process may need root/CAP_NET_BIND_SERVICE to bind it."
        )
    else:
        result.ok(f"Health server port = {port}")


# ---------------------------------------------------------------------------
# Live reachability probes  (optional — skipped if libraries not available)
# ---------------------------------------------------------------------------

def _probe_discord_token(token: str, result: _ValidationResult) -> None:
    """Make a lightweight HTTP call to Discord's /users/@me endpoint to
    verify the token is accepted.  Skipped if ``requests`` is not installed."""
    try:
        import requests as _req
    except ImportError:
        result.warn(
            "requests library not found — skipping live Discord token probe.\n"
            "    Install it with:  pip install requests"
        )
        return

    try:
        resp = _req.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bot {token}"},
            timeout=8,
        )
        if resp.status_code == 200:
            username = resp.json().get("username", "<unknown>")
            result.ok(f"Discord token is valid — bot account: {username}")
        elif resp.status_code == 401:
            result.error(
                "Discord returned 401 Unauthorized for DISCORD_TOKEN.\n"
                "    The token has likely been revoked or was copied incorrectly.\n"
                "    Regenerate it at: https://discord.com/developers/applications"
            )
        elif resp.status_code == 429:
            result.warn(
                "Discord returned 429 Too Many Requests during token probe — "
                "token may be valid but the probe was rate-limited.  "
                "Bot will attempt to start anyway."
            )
        else:
            result.warn(
                f"Discord token probe returned unexpected status {resp.status_code}.  "
                "Bot will attempt to start anyway."
            )
    except _req.exceptions.Timeout:
        result.warn(
            "Discord token probe timed out (8 s).  "
            "Check your network connection.  Bot will attempt to start anyway."
        )
    except _req.exceptions.ConnectionError:
        result.warn(
            "Could not reach discord.com during token probe.  "
            "Check your network connection.  Bot will attempt to start anyway."
        )
    except Exception as exc:
        result.warn(f"Discord token probe failed unexpectedly: {exc}")


def _probe_genai_key(key: str, result: _ValidationResult) -> None:
    """Call the Gemini models.list endpoint to verify the API key grants access.
    Skipped if ``google-genai`` is not installed."""
    try:
        import google.genai as genai
    except ImportError:
        result.warn(
            "google-genai library not found — skipping live Gemini API probe.\n"
            "    Install it with:  pip install google-genai"
        )
        return

    try:
        client = genai.Client(api_key=key)
        # list_models() is the cheapest authenticated call available
        models = list(client.models.list())
        result.ok(f"Gemini API key is valid — {len(models)} model(s) accessible")
    except Exception as exc:
        msg = str(exc).lower()
        if "api_key_invalid" in msg or "invalid api key" in msg or "401" in msg:
            result.error(
                "Gemini API returned an authentication error for GENAI_API_KEY.\n"
                "    The key may be invalid or have insufficient permissions.\n"
                "    Check it at: https://aistudio.google.com/app/apikey"
            )
        elif "quota" in msg or "429" in msg:
            result.warn(
                "Gemini API probe hit a quota limit — key appears valid but is "
                "rate-limited.  Bot will attempt to start anyway."
            )
        else:
            result.warn(
                f"Gemini API probe failed: {exc}.  "
                "Bot will attempt to start anyway."
            )


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

_SETUP_GUIDE = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NOVA Bot — required configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create a .env file in the project root with at minimum:

    DISCORD_TOKEN=<your-discord-bot-token>
    GENAI_API_KEY=<your-google-ai-api-key>

Optional settings (defaults shown):

    MAX_HISTORY_MESSAGES=20      # prior messages fetched per response
    HISTORY_MAX_CHARS=3000       # max total chars of history in prompt
    ENABLE_IMAGE_ANALYSIS=true   # enable image recognition
    PORT=8080                    # health-check server port

Where to get credentials:
  Discord token  → https://discord.com/developers/applications
  Gemini API key → https://aistudio.google.com/app/apikey

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def validate_all(*, probe_network: bool = True) -> None:
    """Run all configuration checks.

    Parameters
    ----------
    probe_network:
        When True (default), make lightweight live HTTP calls to
        verify the Discord token and Gemini API key are actually
        accepted by the remote services.  Pass False in unit tests
        or air-gapped environments.

    Raises
    ------
    ConfigValidationError
        If any *fatal* error is found.  Warnings do not raise.
    """
    logger.info("─" * 60)
    logger.info("NOVA configuration validation")
    logger.info("─" * 60)

    result = _ValidationResult()

    logger.info("Checking secrets …")
    validate_secrets(result)

    logger.info("Checking LLM configuration …")
    validate_llm_config(result)

    logger.info("Checking asset file paths …")
    validate_file_paths(result)

    logger.info("Checking port configuration …")
    validate_port_config(result)

    # Live network probes — only run if no fatal errors so far (no point
    # hitting the network with a token we already know is empty).
    if probe_network and not result.has_errors:
        logger.info("Probing Discord API …")
        token = constants.Secrets.DISCORD_TOKEN
        if token and token.strip():
            _probe_discord_token(token.strip(), result)

        logger.info("Probing Gemini API …")
        key = constants.Secrets.GENAI_API_KEY
        if key and key.strip():
            _probe_genai_key(key.strip(), result)

    logger.info("─" * 60)

    if result.warnings:
        logger.warning(f"{len(result.warnings)} warning(s) — see above")

    if result.has_errors:
        logger.error(f"{len(result.errors)} fatal error(s) found — cannot start")
        # Print the setup guide to stdout so it's visible even when the
        # logger is writing to a file.
        print(_SETUP_GUIDE, file=sys.stderr)
        for i, err in enumerate(result.errors, 1):
            print(f"  [{i}] {err}", file=sys.stderr)
        print(file=sys.stderr)
        raise ConfigValidationError(result.errors)

    logger.info("All configuration checks passed ✓")
    logger.info("─" * 60)
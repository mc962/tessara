"""Logging configuration for Tessera.

Chooses between two output formats automatically:
- JSON  (non-TTY / production): one JSON object per line, structured fields
- Console (TTY / development): aligned human-readable text with ANSI color

Override auto-detection with LOG_FORMAT=json|console.
Control verbosity with LOG_LEVEL (default: INFO).
"""

import json
import logging
import logging.config
import os
import re
import sys
import traceback
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Sensitive data scrubbing
# ---------------------------------------------------------------------------

# Matches the entire credentials block in a URL: scheme://user:password@host
# Uses a greedy [^/\s]+ so passwords containing @ (e.g. p@ssw0rd) are fully
# consumed up to the last @ before the host, then replaces the whole block.
# Only fires when @ is present — bare hostnames are unaffected.
_URL_CRED_RE = re.compile(
    r"([\w+\-.]+://)([^/\s]+@)",
    re.IGNORECASE,
)


def _scrub(value: str) -> str:
    return _URL_CRED_RE.sub(r"\1***@", value)


class _ScrubFilter(logging.Filter):
    """Redact credentials from log records before they reach any handler.

    Applies to the formatted message and any string-valued extras so that
    connection URLs with embedded passwords never appear in output.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Scrub the message (resolve % args first so we can scan the full string)
        if isinstance(record.msg, str):
            record.msg = _scrub(record.msg % record.args if record.args else record.msg)
            record.args = None

        # Scrub string extras
        for key, val in record.__dict__.items():
            if isinstance(val, str) and key not in {
                "name",
                "levelname",
                "pathname",
                "filename",
                "module",
                "funcName",
            }:
                record.__dict__[key] = _scrub(val)

        return True


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


class _JSONFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Standard LogRecord fields — exclude from the extras pass-through
        _STANDARD_FIELDS = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "taskName",
            "exc_info",
            "exc_text",
            "stack_info",
        }
        for key, val in record.__dict__.items():
            if key not in _STANDARD_FIELDS:
                payload[key] = val

        return json.dumps(payload, default=str)


_LEVEL_COLORS = {
    "DEBUG": "\033[36m",  # cyan
    "INFO": "\033[32m",  # green
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",  # red
    "CRITICAL": "\033[35m",  # magenta
}
_RESET = "\033[0m"


class _ConsoleFormatter(logging.Formatter):
    """Aligned, color-coded plain-text format for interactive use."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%H:%M:%S"
        )
        color = _LEVEL_COLORS.get(record.levelname, "")
        level = f"{color}{record.levelname:<8}{_RESET}"
        # Trim logger name to last two components to keep lines short
        parts = record.name.split(".")
        name = ".".join(parts[-2:]) if len(parts) > 2 else record.name
        line = f"{ts} {level} {name:<40} {record.getMessage()}"
        if record.exc_info:
            line += (
                "\n" + "".join(traceback.format_exception(*record.exc_info)).rstrip()
            )
        return line


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def configure_logging() -> None:
    """Apply logging configuration. Call once at process startup, before imports that log."""

    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Auto-detect format: JSON for non-TTY (systemd/file), console for TTY
    log_format = os.environ.get("LOG_FORMAT", "").lower()
    if log_format not in ("json", "console"):
        log_format = "console" if sys.stderr.isatty() else "json"

    formatter = _JSONFormatter() if log_format == "json" else _ConsoleFormatter()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    handler.addFilter(_ScrubFilter())

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers = [handler]

    # Suppress chatty third-party loggers
    _quiet = [
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "sqlalchemy.orm",
        "httpcore",
        "apscheduler.executors",
        "apscheduler.scheduler",
        "multipart",
        "passlib",
    ]
    for name in _quiet:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Uvicorn manages its own handlers — prevent double-emission by stopping
    # propagation on its loggers rather than removing its handlers.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).propagate = False

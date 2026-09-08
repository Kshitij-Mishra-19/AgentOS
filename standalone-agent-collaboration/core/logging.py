"""Structured logging helpers.

The rest of the codebase should call :func:`get_logger` rather than
``logging.getLogger`` directly so that log records consistently carry
``task_id`` / ``correlation_id`` context and render in a single
predictable format.

Configuration (level, format) is driven by ``config/collaboration.yaml``
via :func:`configure_logging`, which the orchestrator/CLI call once at
startup. Individual modules only need :func:`get_logger`.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

_CONFIGURED = False

_DEFAULT_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)


def configure_logging(level: str = "INFO", *, stream: Any = None) -> None:
    """Configure the root logger once. Safe to call multiple times."""
    global _CONFIGURED
    root = logging.getLogger("standalone_agents")
    root.setLevel(level.upper())

    if not root.handlers:
        # Logs go to stderr by default so stdout stays clean for structured
        # program output (e.g. `python -m app ... --json`).
        handler = logging.StreamHandler(stream or sys.stderr)
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
        root.addHandler(handler)
        root.propagate = False

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under the ``standalone_agents`` root."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(f"standalone_agents.{name}")


def log_context(
    logger: logging.Logger,
    level: str,
    event: str,
    *,
    task_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    **extra: Any,
) -> None:
    """Emit a structured log line with consistent key=value context.

    Example output:
        2026-09-08 12:00:00 | INFO | standalone_agents.orchestrator | event=plan_generated task_id=abc123 correlation_id=xyz subtasks=3
    """
    parts = [f"event={event}"]
    if task_id:
        parts.append(f"task_id={task_id}")
    if correlation_id:
        parts.append(f"correlation_id={correlation_id}")
    for key, value in extra.items():
        parts.append(f"{key}={value}")
    message = " ".join(parts)
    getattr(logger, level.lower())(message)

"""COS structured logging system.

Usage:
    from cos.core.logging import get_logger
    logger = get_logger("cos.memory")
    logger.info("Indexed document", extra={"trace_id": "inv-001", "cost": 0.002})
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler


class JsonFormatter(logging.Formatter):
    """JSON lines formatter for structured log files."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        # Optional structured fields
        for field in ("trace_id", "cost", "investigation_id", "workflow_id", "tokens", "duration_ms"):
            val = getattr(record, field, None)
            if val is not None:
                entry[field] = val
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])
        return json.dumps(entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        trace = getattr(record, "trace_id", None)
        cost = getattr(record, "cost", None)
        suffix = ""
        if trace:
            suffix += f" [{trace}]"
        if cost:
            suffix += f" (${cost:.4f})"
        return f"{ts} {record.levelname:>7s} {record.name}: {record.getMessage()}{suffix}"


_initialized = False


def _ensure_log_dir() -> Path:
    """Create log directory from config."""
    from cos.core.config import settings
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _setup_root_logger():
    """Configure root COS logger with console + file handlers."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    from cos.core.config import settings

    root = logging.getLogger("cos")
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Console handler (human-readable)
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(ConsoleFormatter())
    root.addHandler(console)

    # File handler (JSON lines, daily rotation)
    try:
        log_dir = _ensure_log_dir()
        log_file = log_dir / "cos.log"
        file_handler = TimedRotatingFileHandler(
            str(log_file), when="midnight", backupCount=30, encoding="utf-8"
        )
        file_handler.setFormatter(JsonFormatter())
        root.addHandler(file_handler)
    except Exception:
        # If file logging fails (permissions, etc.), continue with console only
        pass


def get_logger(name: str) -> logging.Logger:
    """Get a COS logger. Name should be dotted path like 'cos.core.config'."""
    _setup_root_logger()
    return logging.getLogger(name)

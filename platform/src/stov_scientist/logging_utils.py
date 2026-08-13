"""Structured logging (spec §75).

JSON-line structured logs carrying at least: campaign_id, thread_id, node,
worker, artifact_id, simulation_run_id, error_type. Secrets are NEVER
logged. Plain formatter for interactive terminals; JSON when
STOV_LOG_JSON=1 (default for non-TTY/server runs).
"""

from __future__ import annotations

import json
import logging
import os
import sys

_FIELDS = (
    "campaign_id",
    "thread_id",
    "node",
    "worker",
    "artifact_id",
    "simulation_run_id",
    "error_type",
    "event",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _FIELDS:
            value = getattr(record, field, None)
            if value:
                payload[field] = value
        if record.exc_info and record.exc_info[0] is not None:
            payload["error_type"] = record.exc_info[0].__name__
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    use_json = os.environ.get("STOV_LOG_JSON", "0") == "1" or not sys.stderr.isatty()
    handler.setFormatter(JsonFormatter() if use_json else logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))
    logger.addHandler(handler)
    logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    return logger


def bind(record: logging.LogRecord, **fields: str) -> logging.LogRecord:
    """Attach structured fields to a log record (never secret material)."""
    for key, value in fields.items():
        if key in _FIELDS and value:
            setattr(record, key, value)
    return record

"""Structured request logging with conservative secret redaction."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_MARKERS = (
    "authorization",
    "token",
    "secret",
    "private_key",
    "seed",
    "mnemonic",
    "password",
    "otp",
    "card",
    "cvv",
    "email_content",
)


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): (
                "[REDACTED]"
                if any(marker in str(key).lower() for marker in SENSITIVE_MARKERS)
                else redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact(item) for item in value]
    return value


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, **redact(fields)}
    logger.info(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))

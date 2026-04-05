from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any


def configure_logging(service_name: str) -> None:
    root = logging.getLogger()
    if getattr(root, '_raiya_configured', False):
        return
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload: dict[str, Any] = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': service_name,
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
            }
            if hasattr(record, 'request_id'):
                payload['request_id'] = getattr(record, 'request_id')
            if record.exc_info:
                payload['exc_info'] = self.formatException(record.exc_info)
            return json.dumps(payload, default=str)

    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root._raiya_configured = True  # type: ignore[attr-defined]


def get_logger(name: str, service_name: str = 'raiya-resume-core') -> logging.Logger:
    configure_logging(service_name)
    return logging.getLogger(name)


def new_request_id() -> str:
    return uuid.uuid4().hex

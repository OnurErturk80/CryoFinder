"""Eklemeli (append-only) değişiklik kaydı: her satır bir JSON olayı."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class ChangeLog:
    def __init__(self, path: Path, context: dict | None = None):
        self.path = path
        self.context = context or {}

    def record(self, event: str, **fields) -> None:
        entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event,
                 **self.context, **fields}
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

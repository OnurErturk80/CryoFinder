"""Yazmadan önce OneDrive'daki Yedekler klasörüne tarihli kopya."""
from __future__ import annotations

import posixpath
from datetime import datetime

from . import onedrive


class BackupError(RuntimeError):
    pass


def backup_name(name: str, now: datetime) -> str:
    stem, ext = posixpath.splitext(name)
    return f"{stem}_yedek_{now.strftime('%Y-%m-%d_%H%M%S')}{ext}"


class Backuper:
    """Oturum başına en fazla bir yedek alır; başarısızsa yazmayı engeller."""

    def __init__(self, client, folder: str, source_name: str, get_bytes, now=datetime.now):
        self.c, self.folder, self.source_name = client, folder, source_name
        self._get_bytes, self._now = get_bytes, now
        self.result: dict | None = None

    def ensure(self) -> dict:
        if self.result:
            return self.result
        data = self._get_bytes()
        try:
            onedrive.ensure_folder(self.c, self.folder)
            name = backup_name(self.source_name, self._now())
            item = onedrive.upload_new(self.c, self.folder, name, data)
            check = onedrive.get_item(self.c, item["id"])
            if check.get("size") != len(data):
                raise BackupError("Yedek boyutu kaynakla uyuşmuyor.")
        except BackupError:
            raise
        except Exception as e:
            raise BackupError(f"Yedek alınamadı, YAZMA YAPILMADI: {e}") from e
        self.result = {"path": f"{self.folder}/{name}", "id": item["id"], "sha256": onedrive.sha256(data)}
        return self.result

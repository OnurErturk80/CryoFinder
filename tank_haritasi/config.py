from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_GUID = re.compile(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")


class ConfigError(RuntimeError):
    pass


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Config:
    client_id: str
    test_path: str
    prod_path: str | None
    backup_folder: str
    changelog_path: Path
    token_cache_path: Path

    def target_path(self, production: bool) -> str:
        if not production:
            return self.test_path
        if not self.prod_path:
            raise ConfigError("--production için .env içinde ONEDRIVE_PROD_PATH tanımlı olmalı.")
        return self.prod_path


def load_config(env_file: Path | None = None) -> Config:
    _load_env_file(env_file or ROOT / ".env")
    client_id = os.environ.get("AZURE_CLIENT_ID", "").strip().strip("<>\"' ")   # <...> ya da tırnakla yapıştırılsa da çalışsın
    if not _GUID.match(client_id):
        raise ConfigError("AZURE_CLIENT_ID eksik/geçersiz. .env.example dosyasını .env olarak kopyalayıp doldurun.")
    return Config(
        client_id=client_id,
        test_path=os.environ.get("ONEDRIVE_TEST_PATH", "TANK_HARITASI_TEST.xlsx").strip("/"),
        prod_path=(os.environ.get("ONEDRIVE_PROD_PATH") or "").strip("/") or None,
        backup_folder=os.environ.get("ONEDRIVE_BACKUP_FOLDER", "Yedekler").strip("/"),
        changelog_path=ROOT / "degisiklik_kaydi.jsonl",
        token_cache_path=ROOT / ".token_cache.json",
    )

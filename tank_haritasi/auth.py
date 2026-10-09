"""MSAL: kişisel Microsoft hesabı (consumers), etkileşimli tarayıcı girişi, delegated izin."""
from __future__ import annotations

import os

import msal

from .config import Config

AUTHORITY = "https://login.microsoftonline.com/consumers"
# Yalnızca bu kullanıcının kendi OneDrive'ı için okuma/yazma. (offline_access'i MSAL kendisi ekler.)
SCOPES = ["Files.ReadWrite"]


class AuthError(RuntimeError):
    pass


class TokenProvider:
    def __init__(self, cfg: Config):
        self._path = cfg.token_cache_path
        self._cache = msal.SerializableTokenCache()
        if self._path.exists():
            self._cache.deserialize(self._path.read_text(encoding="utf-8"))
        self._app = msal.PublicClientApplication(cfg.client_id, authority=AUTHORITY, token_cache=self._cache)
        self.username: str | None = None

    def _save(self) -> None:
        if not self._cache.has_state_changed:
            return
        # Önbellek refresh token içerir: yalnızca sahibi okuyabilsin (0600).
        fd = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(self._cache.serialize())

    def token(self) -> str:
        result = None
        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(SCOPES, account=accounts[0])
        if not result:
            result = self._app.acquire_token_interactive(SCOPES, prompt="select_account")
        self._save()
        if "access_token" not in result:
            raise AuthError(result.get("error_description") or str(result))
        claims = result.get("id_token_claims") or {}
        self.username = claims.get("preferred_username") or claims.get("email") or self.username
        return result["access_token"]

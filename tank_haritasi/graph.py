"""İnce Microsoft Graph istemcisi.

GÜVENLİK: Bu istemci DELETE (ve başka hiçbir yıkıcı) HTTP metodunu bilmez. İzinli metodlar
sabit bir listedir; DELETE çağrısı denemesi bile istisna fırlatır. Silme işlevi programda yoktur.
"""
from __future__ import annotations

import time
from typing import Callable

import requests

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH"})


class ForbiddenOperation(RuntimeError):
    pass


class GraphError(RuntimeError):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"Graph {status} {code}: {message}")
        self.status, self.code, self.message = status, code, message


def _error_from(resp) -> GraphError:
    try:
        err = resp.json().get("error", {})
        return GraphError(resp.status_code, err.get("code", "?"), err.get("message", resp.text[:200]))
    except Exception:
        return GraphError(resp.status_code, "?", (resp.text or "")[:200])


class GraphClient:
    def __init__(self, token_provider: Callable[[], str], session=None, sleep=time.sleep):
        self._token = token_provider
        self._s = session or requests.Session()
        self._sleep = sleep

    def request(self, method, path, *, params=None, headers=None, json=None, data=None):
        method = method.upper()
        if method not in ALLOWED_METHODS:
            raise ForbiddenOperation(f"{method} yasak: bu araçta silme/yıkıcı işlem yoktur.")
        url = path if path.startswith("https://") else GRAPH_ROOT + path
        if not url.startswith(GRAPH_ROOT + "/"):
            raise ValueError("Yalnızca Microsoft Graph adreslerine istek atılabilir.")
        for attempt in range(5):
            h = {"Authorization": f"Bearer {self._token()}", **(headers or {})}
            r = self._s.request(method, url, params=params, headers=h, json=json, data=data, timeout=60)
            if r.status_code in (429, 503, 504) and attempt < 4:
                self._sleep(float(r.headers.get("Retry-After", 2**attempt)))
                continue
            break
        if r.status_code >= 400:
            raise _error_from(r)
        return r

    def put_upload_chunk(self, upload_url: str, data: bytes, content_range: str):
        """Yükleme oturumu parçası. Bu adres önceden imzalıdır; Authorization gönderilmez."""
        r = self._s.request(
            "PUT", upload_url, data=data, timeout=120,
            headers={"Content-Range": content_range, "Content-Length": str(len(data))},
        )
        if r.status_code >= 400:
            raise _error_from(r)
        return r

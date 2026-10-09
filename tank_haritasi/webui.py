"""Yerel tarayıcı arayüzü. Yalnızca 127.0.0.1'e bağlanır; oturum anahtarı, Host/Origin denetimi ve
JSON-only POST ile başka web sitelerinin (CSRF / DNS rebinding) bu arayüzü kullanması engellenir."""
from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .page import PAGE
from .service import EditService

MAX_BODY = 64 * 1024


def make_server(service: EditService, log_path, port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    token = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        server_version = "TankHaritasi"

        def log_message(self, *a):  # konsola hücre içeriği sızmasın
            pass

        # -- yardımcılar
        def _hosts(self):
            p = self.server.server_address[1]
            return {f"127.0.0.1:{p}", f"localhost:{p}"}

        def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; img-src 'self' data:")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

        def _guard(self, api: bool) -> bool:
            if self.headers.get("Host") not in self._hosts():
                self._json({"ok": False, "message": "Geçersiz Host"}, 403); return False
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://{h}" for h in self._hosts()}:
                self._json({"ok": False, "message": "Geçersiz Origin"}, 403); return False
            if api and not secrets.compare_digest(self.headers.get("X-Session-Token", ""), token):
                self._json({"ok": False, "message": "Oturum anahtarı geçersiz"}, 403); return False
            return True

        # -- yönlendirme
        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/":
                if self._guard(False):
                    self._send(200, PAGE.replace("__TOKEN__", token).encode("utf-8"), "text/html; charset=utf-8")
                return
            if not url.path.startswith("/api/") or not self._guard(True):
                if not url.path.startswith("/api/"):
                    self._json({"ok": False, "message": "yok"}, 404)
                return
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                if url.path == "/api/state":
                    self._json(service.state())
                elif url.path == "/api/sheet":
                    self._json(service.sheet_view(q["name"], int(q.get("row0", 1)), int(q.get("rows", 50)),
                                                  q.get("fresh") == "1"))
                elif url.path == "/api/search":
                    self._json({"hits": service.search(q.get("q", ""))})
                elif url.path == "/api/map":
                    self._json(service.map_view(int(q["tank"])))
                elif url.path == "/api/reg/options":
                    self._json(service.reg_options())
                elif url.path == "/api/log":
                    self._json({"lines": service.recent_log(log_path)})
                else:
                    self._json({"ok": False, "message": "yok"}, 404)
            except Exception as e:  # noqa: BLE001
                self._json({"ok": False, "message": str(e)}, 400)

        def do_POST(self):
            url = urlparse(self.path)
            if not self._guard(True):
                return
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                self._json({"ok": False, "message": "JSON bekleniyor"}, 415); return
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                self._json({"ok": False, "message": "çok büyük"}, 413); return
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
                if url.path == "/api/propose":
                    self._json(service.propose(body["sheet"], body["cell"], body.get("value", "")))
                elif url.path == "/api/apply":
                    self._json(service.apply(body["id"]))
                elif url.path == "/api/reg/suggest":
                    self._json(service.reg_suggest(int(body["tank"]), int(body["n"]), str(body.get("kat", "otomatik"))))
                elif url.path == "/api/reg/preview":
                    self._json(service.reg_preview(str(body["plan_id"]), str(body["straw_type"]),
                                                   list(body["straws"]), dict(body["patient"])))
                elif url.path == "/api/reg/apply":
                    self._json(service.reg_apply(str(body["id"])))
                elif url.path == "/api/shutdown":
                    self._json({"ok": True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                elif url.path == "/api/map/slot":
                    self._json(service.map_slot(str(body["id"])))
                elif url.path == "/api/map/find":
                    self._json(service.map_find(str(body.get("q", "")), body.get("tank")))
                elif url.path == "/api/rem/search":
                    self._json(service.rem_search(str(body.get("q", ""))))
                elif url.path == "/api/rem/preview":
                    self._json(service.rem_preview(list(body["items"])))
                elif url.path == "/api/rem/apply":
                    self._json(service.rem_apply(str(body["id"])))
                elif url.path == "/api/decline":
                    self._json(service.decline(body["id"]))
                elif url.path == "/api/commit/prepare":
                    self._json(service.prepare_commit())
                elif url.path == "/api/commit":
                    self._json(service.commit())
                else:
                    self._json({"ok": False, "message": "yok"}, 404)
            except Exception as e:  # noqa: BLE001
                self._json({"ok": False, "message": str(e)}, 400)

    try:
        srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:                       # tercih edilen port doluysa (ör. program zaten açık) boş bir port seç
        if not port:
            raise
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    return srv, token


def serve_in_thread(srv) -> threading.Thread:
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return t

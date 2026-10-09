"""Arayüzün kullandığı iş mantığı. CLI ile aynı güvenlik kuralları: onay, yedek, kayıt, silme yok."""
from __future__ import annotations

import secrets
import threading
import time

from openpyxl.utils.cell import get_column_letter

from .backup import BackupError
from .editor import Change, apply_change, evaluate, log_evaluation
from .sheetutil import CELL_RE

CACHE_TTL = 20.0


class EditService:
    def __init__(self, backend, backuper, log, file_label: str, production: bool = False):
        self.backend, self.backuper, self.log = backend, backuper, log
        self.file_label, self.production = file_label, production
        self.lock = threading.RLock()
        self.pending: dict[str, tuple[Change, object]] = {}
        self.staged: list[Change] = []
        self._cache: dict[str, tuple[float, dict]] = {}
        self._backup_logged = False

    # ---- okuma
    def _cells(self, sheet: str, fresh: bool = False) -> dict:
        hit = self._cache.get(sheet)
        if hit and not fresh and time.time() - hit[0] < CACHE_TTL:
            return hit[1]
        cells = self.backend.dump(sheet, text=True)
        self._cache[sheet] = (time.time(), cells)
        return cells

    def state(self) -> dict:
        with self.lock:
            return {"file": self.file_label, "mode": self.backend.name, "production": self.production,
                    "sheets": self.backend.sheet_names(), "staged": len(self.staged),
                    "needs_commit": self.backend.needs_commit,
                    "backup": self.backuper.result["path"] if self.backuper.result else None}

    def sheet_view(self, sheet: str, row0: int = 1, nrows: int = 50, fresh: bool = False) -> dict:
        with self.lock:
            cells = self._cells(sheet, fresh)
            max_row = max((r for r, _ in cells), default=1)
            max_col = max((c for _, c in cells), default=1)
            row0 = max(1, min(row0, max_row))
            rows = [[str(cells.get((r, c), "")) for c in range(1, max_col + 1)]
                    for r in range(row0, min(row0 + nrows, max_row + 1))]
            return {"sheet": sheet, "row0": row0, "max_row": max_row, "max_col": max_col,
                    "cols": [get_column_letter(c) for c in range(1, max_col + 1)], "rows": rows}

    def search(self, query: str, limit: int = 200) -> list[dict]:
        needle = query.strip().lower()
        if len(needle) < 2:
            return []
        hits: list[dict] = []
        with self.lock:
            for name in self.backend.sheet_names():
                for (r, c), v in sorted(self._cells(name).items()):
                    if needle in str(v).lower():
                        hits.append({"sheet": name, "cell": f"{get_column_letter(c)}{r}", "row": r, "value": str(v)})
                        if len(hits) >= limit:
                            return hits
        return hits

    # ---- yazma: öner → (kullanıcı onayı) → uygula
    def propose(self, sheet: str, cell: str, value: str) -> dict:
        cell = cell.strip().upper()
        if not CELL_RE.match(cell):
            return {"ok": False, "message": "Geçersiz hücre adresi."}
        ch = Change(sheet, cell, value)
        with self.lock:
            ev = evaluate(self.backend, ch)
            if ev["kind"] != "ok":
                log_evaluation(self.log, ch, ev)
                return {"ok": False, "message": ev["message"]}
            pid = secrets.token_urlsafe(9)
            self.pending[pid] = (ch, ev["old"])
            return {"ok": True, "id": pid, "sheet": sheet, "cell": cell,
                    "old": "" if ev["old"] is None else str(ev["old"]), "new": value}

    def decline(self, pid: str) -> dict:
        with self.lock:
            item = self.pending.pop(pid, None)
            if item:
                ch, old = item
                self.log.record("declined", sheet=ch.sheet, cell=ch.cell, old=old, new=ch.new_value)
        return {"ok": True}

    def apply(self, pid: str) -> dict:
        """Kullanıcı arayüzde 'Onayla'ya bastığında çağrılır. Tek kullanımlık kimlik."""
        with self.lock:
            item = self.pending.pop(pid, None)
            if not item:
                return {"ok": False, "message": "Bu öneri artık geçerli değil; yeniden başlatın."}
            ch, old = item
            ev = evaluate(self.backend, ch)
            if ev["kind"] != "ok" or ev["old"] != old:
                return {"ok": False, "message": "Hücre siz incelerken değişmiş. Yeniden gözden geçirin."}
            try:
                info = self.backuper.ensure()
            except BackupError as e:
                return {"ok": False, "message": str(e)}
            if not self._backup_logged:
                self.log.record("backup", **info)
                self._backup_logged = True
            try:
                apply_change(self.backend, ch, old, self.log)
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "message": f"Yazılamadı: {e}"}
            if self.backend.needs_commit:
                self.staged.append(ch)
            self._cache.pop(ch.sheet, None)
            return {"ok": True, "backup": info["path"], "staged": len(self.staged),
                    "message": "Hazırlandı; 'OneDrive'a yükle' ile tamamlayın." if self.backend.needs_commit
                    else "Uygulandı."}

    # ---- yalnızca bellek modu
    def prepare_commit(self) -> dict:
        with self.lock:
            if not self.backend.needs_commit or not self.staged:
                return {"ok": False, "message": "Yüklenecek değişiklik yok."}
            new_bytes = self.backend.serialize()
            problems, lost = self.backend.verify(new_bytes)
            return {"ok": not problems and not lost, "count": len(self.staged), "problems": problems,
                    "lost": lost, "etag": self.backend.meta["eTag"],
                    "changes": [f"{c.sheet}!{c.cell}" for c in self.staged]}

    def commit(self) -> dict:
        from .onedrive import ConflictError, sha256
        with self.lock:
            prep = self.prepare_commit()
            if not prep["ok"]:
                self.log.record("aborted", reason="verification", details=prep.get("problems") or prep.get("lost"))
                return {"ok": False, "message": "Doğrulama başarısız; yüklenmedi: " +
                        "; ".join((prep.get("problems") or []) + (prep.get("lost") or []))}
            new_bytes = self.backend.serialize()
            try:
                item = self.backend.commit(new_bytes)
            except ConflictError as e:
                self.log.record("conflict", error=str(e))
                return {"ok": False, "message": str(e)}
            self.log.record("committed", changes=len(self.staged), new_etag=item.get("eTag"),
                            sha256=sha256(new_bytes), backup=self.backuper.result["path"])
            self.staged.clear()
            self.backend.meta = {**self.backend.meta, "eTag": item.get("eTag", self.backend.meta["eTag"])}
            self.backend.original = new_bytes  # sonraki karşılaştırmalar yeni dosyayı esas alsın
            self._cache.clear()
            return {"ok": True, "message": "Yüklendi ve doğrulandı. Sayfayı yeniden açın."}

    def recent_log(self, path, n: int = 15) -> list[str]:
        try:
            return path.read_text(encoding="utf-8").splitlines()[-n:]
        except FileNotFoundError:
            return []

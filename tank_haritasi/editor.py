"""Değişiklik akışı: her değişiklik için tek tek onay, yedek, kayıt."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .sheetutil import CELL_RE


@dataclass(frozen=True)
class Change:
    sheet: str
    cell: str
    new_value: str


def parse_change(spec: str) -> Change:
    """'Sayfa1!B3=Yeni değer' -> Change. Boş değer hücreyi temizler."""
    if "=" not in spec or "!" not in spec.split("=", 1)[0]:
        raise ValueError(f"Biçim 'Sayfa!HÜCRE=değer' olmalı: {spec!r}")
    ref, value = spec.split("=", 1)
    sheet, cell = ref.rsplit("!", 1)
    sheet, cell = sheet.strip().strip("'"), cell.strip().upper()
    if not sheet or not CELL_RE.match(cell):
        raise ValueError(f"Geçersiz sayfa/hücre: {ref!r}")
    return Change(sheet, cell, value)


def _show(v) -> str:
    return "(boş)" if v in (None, "") else repr(v)


def evaluate(backend, ch: Change) -> dict:
    """Bir değişikliğin yapılabilir olup olmadığını denetler. kind: ok | refused | failed | unchanged."""
    if ch.new_value.startswith("="):
        return {"kind": "refused", "reason": "formula-value",
                "message": "'=' ile başlayan değer (formül) bu araçla yazılamaz."}
    try:
        old, is_formula = backend.get_cell(ch.sheet, ch.cell)
    except Exception as e:  # noqa: BLE001
        return {"kind": "failed", "stage": "read", "message": f"okunamadı ({e})"}
    if is_formula:
        return {"kind": "refused", "reason": "cell-has-formula", "message": "hücre formül içeriyor; üzerine yazılmaz."}
    if str(old if old is not None else "") == ch.new_value:
        return {"kind": "unchanged", "old": old, "message": "değişiklik yok."}
    return {"kind": "ok", "old": old}


def log_evaluation(log, ch: Change, ev: dict) -> None:
    if ev["kind"] == "refused":
        log.record("refused", sheet=ch.sheet, cell=ch.cell, new=ch.new_value, reason=ev["reason"])
    elif ev["kind"] == "failed":
        log.record("failed", sheet=ch.sheet, cell=ch.cell, error=ev["message"], stage=ev["stage"])


def apply_change(backend, ch: Change, old, log) -> bool:
    """Onaylanmış değişikliği yazar (bellek modunda sahneler) ve kaydeder."""
    try:
        backend.set_cell(ch.sheet, ch.cell, ch.new_value)
    except Exception as e:  # noqa: BLE001
        log.record("failed", sheet=ch.sheet, cell=ch.cell, old=old, new=ch.new_value, error=str(e), stage="write")
        raise
    log.record("staged" if backend.needs_commit else "applied", mode=backend.name,
               sheet=ch.sheet, cell=ch.cell, old=old, new=ch.new_value)
    return True


def run_changes(backend, changes: list[Change], *, confirm: Callable[[str], bool], log,
                ensure_backup: Callable[[], dict], say=print) -> list[Change]:
    """Onaylanan değişiklikleri backend'e uygular (bellek modunda: sahneler). Onaylananları döndürür."""
    done: list[Change] = []
    backup_info: dict | None = None
    for ch in changes:
        where = f"{ch.sheet}!{ch.cell}"
        ev = evaluate(backend, ch)
        if ev["kind"] != "ok":
            say(f"{'=' if ev['kind'] == 'unchanged' else '✗'} {where}: {ev['message']}")
            log_evaluation(log, ch, ev)
            continue
        old = ev["old"]
        say(f"\n  {where}\n    eski: {_show(old)}\n    yeni: {_show(ch.new_value)}")
        if not confirm("  Bu değişiklik uygulansın mı?"):
            log.record("declined", sheet=ch.sheet, cell=ch.cell, old=old, new=ch.new_value)
            say("  → reddedildi.")
            continue
        if backup_info is None:
            backup_info = ensure_backup()  # başarısızsa istisna → hiçbir şey yazılmaz
            say(f"  ✓ Yedek alındı: {backup_info['path']}")
            log.record("backup", **backup_info)
        try:
            apply_change(backend, ch, old, log)
        except Exception as e:  # noqa: BLE001
            say(f"  ✗ yazılamadı: {e}")
            continue
        say("  ✓ " + ("hazırlandı (yükleme sonunda onaylanacak)." if backend.needs_commit else "uygulandı."))
        done.append(ch)
    return done

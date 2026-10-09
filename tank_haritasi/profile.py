"""Hasta verisini AÇMADAN dosyanın yapısını özetler: başlıklar, bölüm satırları, değer biçimleri, hücre renkleri.

Kişisel veri sızmasın diye: ad/soyad gibi sütunların değerleri yazdırılmaz; diğer sütunlarda ham değer yerine
"biçim" (rakam→9, harf→A) gösterilir; yalnızca az sayıda farklı değeri olan, kişi adı olmayan sütunlarda değerler listelenir.
"""
from __future__ import annotations

import io
import re
from collections import Counter

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

NAME_HEADERS = re.compile(r"SOYAD|^AD$|\bADI\b|EŞ|ESI|HASTA|İSİM|ISIM|ISIM|PROTOKOL|TC|TELEFON|DOSYA", re.I)
MAX_LISTED = 12


def shape(v) -> str:
    s = str(v)
    return re.sub(r"[A-Za-zÇĞİÖŞÜçğıöşü]", "A", re.sub(r"\d", "9", s))[:24]


def _fill(cell) -> str | None:
    f = cell.fill
    if f is None or f.fill_type in (None, "none"):
        return None
    c = f.fgColor
    if c is None:
        return None
    if c.type == "rgb":
        return str(c.rgb)[-6:]
    if c.type == "theme":
        return f"tema{c.theme}{'%+.2f' % c.tint if c.tint else ''}"
    return f"{c.type}{getattr(c, 'indexed', '')}"


def profile_workbook(data: bytes) -> list[str]:
    wb = load_workbook(io.BytesIO(data))
    out: list[str] = []
    for ws in wb.worksheets:
        out.append(f"\n=== Sayfa: {ws.title}  ({ws.max_row} satır x {ws.max_column} sütun) ===")
        rows = [[c for c in row] for row in ws.iter_rows()]
        # bölüm satırları: en çok 2 dolu hücre (örn. "TANK 1", "CANISTER 1")
        markers = []
        header = None
        for r in rows:
            filled = [c for c in r if c.value not in (None, "")]
            if 1 <= len(filled) <= 2 and all(isinstance(c.value, str) and len(c.value) <= 30 for c in filled):
                markers.append(f"{filled[0].row}:{' | '.join(str(c.value) for c in filled)}")
            if header is None and len(filled) >= 4 and all(isinstance(c.value, str) and not re.search(r"\d", c.value)
                                                           for c in filled):
                header = (filled[0].row, {c.column: str(c.value) for c in filled})
        out.append("Bölüm/başlık satırları: " + (", ".join(markers[:40]) + (" …" if len(markers) > 40 else "") or "yok"))
        hdr = header[1] if header else {}
        out.append("Başlık satırı: " + (f"{header[0]}: " + " | ".join(f"{get_column_letter(k)}={v}" for k, v in hdr.items())
                                        if header else "bulunamadı"))
        for col in range(1, ws.max_column + 1):
            cells = [r[col - 1] for r in rows if col - 1 < len(r)]
            vals = [c.value for c in cells if c.value not in (None, "")]
            if not vals:
                continue
            name = hdr.get(col, "")
            L = f"  {get_column_letter(col)} ({name or 'başlıksız'}): {len(vals)} dolu"
            if NAME_HEADERS.search(name):
                out.append(L + " — kişisel veri sütunu, değerler gösterilmiyor")
            else:
                distinct = Counter(str(v) for v in vals)
                if len(distinct) <= MAX_LISTED:
                    out.append(L + ", değerler: " + ", ".join(f"{k}×{n}" for k, n in distinct.most_common()))
                else:
                    sh = Counter(shape(v) for v in vals).most_common(6)
                    out.append(L + f", {len(distinct)} farklı; biçimler: " + ", ".join(f"{k}×{n}" for k, n in sh))
            fills = Counter(f for f in (_fill(c) for c in cells if c.value not in (None, "")) if f)
            if fills:
                out.append("      hücre renkleri: " + ", ".join(f"{k}×{n}" for k, n in fills.most_common(8)))
        allfills = Counter(f for r in rows for c in r if (f := _fill(c)))
        if allfills:
            out.append("  Sayfadaki tüm dolgu renkleri: " + ", ".join(f"{k}×{n}" for k, n in allfills.most_common(12)))
    return out

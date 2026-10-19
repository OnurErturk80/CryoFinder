"""Tank haritası modeli ve boş yer önerisi.

Standart düzen: her canister 7 sütunluk bir blok (NO | SOYAD | AD | EŞİ | TARİH | HÜCRE | VİAL). NO sütununda önceden
basılı goblet konumu etiketleri (1A, 1A, 1A, 1A, 2A, ... veya 1, 1, 1, 1, ...) bulunur; aynı etiketin ardışık 4 satırı
bir konumdur (= 4 straw yeri). Bir konumda straw renkleri (MAVİ, SARI, YEŞİL, TURUNCU) birbirinden farklı olmalıdır.
Bu modül yalnızca okur ve öneri üretir; yazma işlemi servis katmanındaki onaylı akıştan geçer.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from openpyxl.utils.cell import get_column_letter

_TR = str.maketrans({"İ": "I", "ı": "I", "Ş": "S", "ş": "S", "Ü": "U", "ü": "U",
                     "Ö": "O", "ö": "O", "Ç": "C", "ç": "C", "Ğ": "G", "ğ": "G"})
POS_RE = re.compile(r"^(\d{1,2})([A-Z]?)$")
TANK_RE = re.compile(r"^TANK\s*(\d+)$")
CAN_RE = re.compile(r"^CAN+ISTER\s*(\d+)")
SLOTS = 4
COLORS = ["MAVİ", "SARI", "YEŞİL", "TURUNCU"]          # öneri sırası ve yazım
_COLOR_FOLDED = {c.translate(_TR).upper(): c for c in COLORS}
STRAW_TYPES = ["VİTRİFİT", "CRYOLOCK", "CRYOTOP"]
# Atama kuralı (mevcut kullanılan araçtaki gibi): straw rengi gobletteki SIRAYA göre belirlenir;
# o renk kullanılmışsa sıradaki kullanılmamış renk seçilir.
COLOR_ORDER = ["MAVİ", "SARI", "TURUNCU", "YEŞİL"]
POS_COLOR = {1: "MAVİ", 2: "SARI", 3: "TURUNCU", 4: "YEŞİL"}
DEVICES = ["CRYOLOCK", "VİTRİFİT", "CRYOTOP", "RAPIDI"]
TANK_LABELS = {4: "Tank 4", 101: "Yeni sperm", 102: "Sayfa1 (eski sperm)", 103: "Küçük tank (Tank 3)"}


def tank_label(t) -> str:
    return TANK_LABELS.get(t) or f"Tank {t if t else '?'}"


def fold(v) -> str:
    return re.sub(r"\s+", " ", str(v).strip().translate(_TR).upper())


def tr_upper(s: str) -> str:
    """Türkçe büyük harf: i→İ, ı→I (haritadaki isimler büyük harfle yazılıyor)."""
    return s.strip().replace("i", "İ").replace("ı", "I").upper()


def vial_text(device: str, color: str | None, pos: int | None = None) -> str:
    """VİAL biçimi: '1 CRYOLOCKSARI 2', '1 VİTRİFİTMAVİ 1', rapidi için '1 RAPIDI 3' (sondaki sayı goblet içindeki sıra)."""
    tail = f" {pos}" if pos else ""
    if device == "RAPIDI":
        return f"1 RAPIDI{tail}"
    return f"1 {device}{color or ''}{tail}"


_DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%y", "%d-%m-%Y")


def parse_date(text):
    """Hücrenin görünen tarih metni → date (tanınmazsa None)."""
    from datetime import datetime
    t = str(text or "").strip().split(" ")[0]
    for f in _DATE_FORMATS:
        try:
            return datetime.strptime(t, f).date()
        except ValueError:
            continue
    return None


def vial_kind(text) -> str | None:
    f = fold(text)
    for key, name in (("RAPIDI", "RAPIDI"), ("VITRIFIT", "VİTRİFİT"), ("CRYOLOCK", "CRYOLOCK"), ("CRYOTOP", "CRYOTOP")):
        if key in f:
            return name
    return None


def vial_color(text) -> str | None:
    f = fold(text)
    for key, color in _COLOR_FOLDED.items():
        if key in f:
            return color
    return None


@dataclass
class Row:
    row: int
    cells: dict           # alan -> (satır, sütun)
    occupied: bool
    color: str | None
    vial: str
    date_text: str = ""
    soyad: str = ""
    ad: str = ""
    esi: str = ""
    hucre: str = ""


@dataclass
class Position:
    sheet: str
    tank: int | None
    canister: int | None
    label: str            # "2A" ya da "2"
    number: int
    suffix: str
    rows: list[Row] = field(default_factory=list)
    loose: bool = False   # standart goblet etiketi (1, 1A…) olmayan, ama dolu satırlar
    kind: str = "goblet"  # goblet (4 straw) | pos (harf+rakam konumları) | list (harf satırları: sperm)
    max_fill: int = SLOTS
    part: str = ""        # Tank 4 gibi düzenlerde etiketten gelen "Üst"/"Alt"
    special: bool = False # standart tank/canister düzeninden farklı ama tanınan düzen (Tank 4, sperm sayfaları)
    order: int = 0

    @property
    def kat(self) -> str:
        """Kat: etiketten (Ü/A) belliyse oradan, değilse sayfa adından: adında 'ÜST' geçen sayfa üst kat.
        'A' eki yalnızca o gobletin üst katının kullanıldığını gösteren bir işarettir."""
        if self.part:
            return "üst" if self.part == "Üst" else "alt"
        return "üst" if "UST" in fold(self.sheet) else "alt"

    @property
    def standard(self) -> bool:
        """Standart konum: tam 4 satır (ya da tanınan özel düzen). Daha kısa/uzun gruplar öneride kullanılmaz."""
        return self.special or (len(self.rows) == SLOTS and not self.loose)

    @property
    def name(self) -> str:
        return f"{tank_label(self.tank)} / Canister {self.canister or '?'} / {self.label} ({self.kat} kat)"

    @property
    def pid(self) -> str:
        return f"{self.sheet}|{self.rows[0].cells['no'][1]}|{self.rows[0].row}|{self.label}"

    @property
    def occupied_count(self) -> int:
        return sum(1 for r in self.rows if r.occupied)

    @property
    def capacity(self) -> int:
        return max(0, min(len(self.free_rows), self.max_fill - self.occupied_count))

    @property
    def group_type(self) -> str:
        """empty | rapid | color — bir gobletin içinde rapidi ile renkli straw karışmaz."""
        t = "empty"
        for r in self.rows:
            if r.occupied:
                if vial_kind(r.vial) == "RAPIDI":
                    return "rapid"
                t = "color"
        return t

    @property
    def goblet_key(self) -> tuple:
        return (self.tank, self.canister, self.number)

    @property
    def canister_key(self) -> tuple:
        return (self.sheet, self.tank, self.canister, self.kat)

    @property
    def free_rows(self) -> list[Row]:
        return [r for r in self.rows if not r.occupied]

    @property
    def used_colors(self) -> set[str]:
        return {r.color for r in self.rows if r.color}

    @property
    def free_colors(self) -> list[str]:
        return [c for c in COLORS if c not in self.used_colors]

    @property
    def unknown_occupied(self) -> int:
        """Dolu ama rengi okunamayan satır (rapidi renksiz olduğu için sayılmaz)."""
        return sum(1 for r in self.rows if r.occupied and not r.color and vial_kind(r.vial) != "RAPIDI")


FIELDS = ["no", "soyad", "ad", "esi", "tarih", "hucre", "vial"]


HEADER_WORDS = {"SOYAD", "SOYADI", "HARF"}


def _make_row(text: dict, r: int, cols: dict) -> Row:
    vial = text.get((r, cols["vial"]), "")
    occupied = any(text.get((r, cols[f]), "") for f in ("esi", "soyad", "ad", "tarih", "hucre", "vial"))
    return Row(r, {f: (r, cols[f]) for f in FIELDS}, occupied, vial_color(vial), vial,
               text.get((r, cols["tarih"]), ""), text.get((r, cols["soyad"]), ""),
               text.get((r, cols["ad"]), ""), text.get((r, cols["esi"]), ""), text.get((r, cols["hucre"]), ""))


def scan_sheet(sheet: str, cells: dict[tuple[int, int], object]) -> list[Position]:
    return scan_sheet_full(sheet, cells)[0]


def scan_sheet_full(sheet: str, cells: dict[tuple[int, int], object]) -> tuple[list[Position], set[tuple[int, int]]]:
    """Bir sayfanın hücrelerinden (satır, sütun) → konumlar ve (tank, canister) işaretleri.

    Standart konumlar: NO sütunundaki 1, 1A… etiketli ardışık satırlar. Bunların dışında kalan DOLU satırlar
    (etiketsiz/farklı düzen) `loose` konumlar olarak yine listelenir; böylece hiçbir hasta haritada ve aramada kaybolmaz.
    Desteklenmeyen düzende boş döner."""
    text = {k: str(v).strip() for k, v in cells.items() if str(v).strip() != ""}
    counts = Counter(c for (r, c), v in text.items()
                     if (m := POS_RE.match(fold(v))) and 1 <= int(m[1]) <= 60)
    blocks = []
    for c, n in sorted(counts.items()):
        names = sum(1 for (r, cc), v in text.items() if cc == c + 1 and not re.search(r"\d", v))
        if n >= 20 and names >= 10:
            blocks.append(c)
    first_col = blocks[0] if blocks else 1
    tanks = []
    for (r, c), v in text.items():
        if c != first_col:          # başka sütundaki "TANK n" yazıları (küçük tank vb.) bölüm başlığı değildir
            continue
        f = fold(v)
        if m := TANK_RE.match(f):
            tanks.append((r, int(m[1])))
        elif f.startswith("KUCUK TANK"):
            tanks.append((r, 0))    # 0 = küçük tank bölgesi: bu satırlardan sonrası haritaya dahil edilmez
    tanks.sort()
    cans = sorted((r, c, int(m[1])) for (r, c), v in text.items() if (m := CAN_RE.match(fold(v))))

    def current(markers, row):
        last = None
        for mk in markers:
            if mk[0] <= row:
                last = mk
            else:
                break
        return last

    out: list[Position] = []
    markers: set[tuple[int, int]] = set()
    for bi, c0 in enumerate(blocks):
        cols = {name: c0 + i for i, name in enumerate(FIELDS)}
        block_cans = [m for m in cans if c0 <= m[1] <= c0 + 6]
        for mr, _, mnum in block_cans:
            t = current(tanks, mr)
            if t and t[1] != 0:
                markers.add((t[1], mnum))
        no_rows = sorted((r, fold(v)) for (r, c), v in text.items() if c == c0 and POS_RE.match(fold(v)))
        prev, block_start = None, len(out)
        for r, lab in no_rows:
            m = POS_RE.match(lab)
            tank = current(tanks, r)
            if tank and tank[1] == 0:
                continue
            can = current(block_cans, r)
            key = (tank[1] if tank else None, can[2] if can else bi + 1, lab)
            pos = out[-1] if len(out) > block_start and prev else None
            fresh = (pos is None or prev[0] + 1 != r or prev[1] != key or len(pos.rows) >= SLOTS or pos.sheet != sheet)
            if fresh:
                pos = Position(sheet, key[0], key[1], lab, int(m[1]), m[2])
                out.append(pos)
            pos.rows.append(_make_row(text, r, cols))
            prev = (r, key)
        # --- standart etiketi olmayan ama dolu satırlar (farklı düzen): tek tek gruplanır, kaybolmaz
        covered = {row.row for p in out[block_start:] for row in p.rows}
        data_rows = sorted({r for (r, c) in text if c in (c0 + 1, c0 + 2, c0 + 5, c0 + 6)} - covered)
        prev_loose = None
        for r in data_rows:
            tank = current(tanks, r)
            if tank and tank[1] == 0:
                continue
            if fold(text.get((r, c0 + 1), "")) in HEADER_WORDS or fold(text.get((r, c0 + 6), "")) == "VIAL" \
                    or fold(text.get((r, c0 + 5), "")) == "HUCRE":
                continue                                          # başlık satırı
            row = _make_row(text, r, cols)
            if not row.occupied:
                continue
            can = current(block_cans, r)
            label = text.get((r, c0), "") or "—"
            key = (tank[1] if tank else None, can[2] if can else bi + 1, label)
            if prev_loose and prev_loose[0] + 1 == r and prev_loose[1] == key:
                out[-1].rows.append(row)
            else:
                lead = re.match(r"\d+", label)
                out.append(Position(sheet, key[0], key[1], label, int(lead[0]) if lead else 0, "", [row], loose=True))
            prev_loose = (r, key)
    return out, markers


# ---------------- özel düzenler: Tank 4, sperm sayfaları, küçük tank
_CAN_ANY = re.compile(r"CAN+ISTER\s*(\d+)")
_EXTRA_LABEL = re.compile(r"^[A-Z]{1,2}( ?\d+)?$")
EXTRA_SHEETS = {"TANK 4": 4, "YENI SPERM": 101, "SAYFA1": 102}


def extra_tank_for(sheet: str) -> tuple[int, str]:
    f = fold(sheet)
    if f in EXTRA_SHEETS:
        t = EXTRA_SHEETS[f]
        return t, tank_label(t)
    return 200 + (sum(ord(ch) for ch in f) % 700), sheet    # tanınmayan sayfa: sayfa adıyla göster (kararlı kimlik)


def scan_extra(sheet: str, cells: dict, tank_id: int, mode: str = "headers", col: int | None = None) -> list[Position]:
    """NO/SOYAD başlıklı (headers) ya da 'CANİSTER n' başlıklı tek sütunlu (ktank) özel düzenleri okur.

    Etiket biçimine göre tür belirlenir: harf+rakam (K3) → 'pos', harf+Ü/A (KÜ, KA) → 'goblet' (üst/alt kat),
    tek harf → 'goblet' (çoğu satır ≥3 ise) ya da 'list' (sperm: her satır bir kayıt)."""
    text = {k: str(v).strip() for k, v in cells.items() if str(v).strip() != ""}
    if not text:
        return []
    max_row = max(r for r, _ in text)
    blocks: list[dict] = []
    if mode == "headers":
        by_col: dict[int, list[int]] = defaultdict(list)
        for (r, c), v in text.items():
            if fold(v) == "NO" and fold(text.get((r, c + 1), "")) == "SOYAD":
                by_col[c].append(r)
        for c, rows in by_col.items():
            rows.sort()
            for i, h in enumerate(rows):
                cn = None
                left = text.get((h, c - 1)) if c > 1 else None
                if left:
                    m = re.match(r"^\d+(?:\.0+)?$", left) or re.search(r"\d+", left)
                    if m:
                        cn = int(float(m.group(0)))
                for up in (1, 2, 3):
                    if cn is not None:
                        break
                    mm = _CAN_ANY.search(fold(text.get((h - up, c), "")))
                    if mm:
                        cn = int(mm.group(1))
                blocks.append({"col": c, "from": h + 1, "to": rows[i + 1] - 1 if i + 1 < len(rows) else max_row,
                               "cn": cn, "stop": False})
    else:
        heads = sorted((r, int(m.group(1))) for (r, c), v in text.items()
                       if c == col and (m := re.match(r"^CAN+ISTER\s*(\d+)", fold(v))))
        for i, (r, cn) in enumerate(heads):
            blocks.append({"col": col, "from": r + 1, "to": heads[i + 1][0] - 1 if i + 1 < len(heads) else max_row,
                           "cn": cn, "stop": True})

    out: list[Position] = []
    used_cn: set[int] = set()
    for seq, bl in enumerate(blocks, 1):
        cn = bl["cn"] if bl["cn"] is not None else 900 + seq
        while cn in used_cn:
            cn += 100
        items = []
        for r in range(bl["from"], bl["to"] + 1):
            raw = text.get((r, bl["col"]), "")
            if not raw:
                if bl["stop"] and items:
                    break
                continue
            f = fold(raw)
            if f in ("HARF", "NO") or not _EXTRA_LABEL.match(f):
                continue
            items.append((r, f))
        if len(items) < 3:
            continue
        used_cn.add(cn)
        labs = [lab for _, lab in items]

        def runs_of(key_fn):
            runs: list[dict] = []
            for r, lab in items:
                k = key_fn(lab)
                if runs and runs[-1]["key"] == k:
                    runs[-1]["rows"].append(r)
                else:
                    runs.append({"key": k, "lab": lab, "rows": [r]})
            return runs

        pos_share = sum(1 for l in labs if re.match(r"^[A-Z]\d$", l)) / len(labs)
        if pos_share >= 0.85:
            kind, runs = "pos", runs_of(lambda l: l[0])
        elif all(re.match(r"^[A-Z][UA]$", l) for l in labs):
            kind, runs = "goblet", runs_of(lambda l: l)
        elif all(re.match(r"^[A-Z]$", l) for l in labs):
            runs = runs_of(lambda l: l)
            big = sum(1 for x in runs if len(x["rows"]) >= 3)
            kind = "goblet" if big >= len(runs) / 2 else "list"
        else:
            kind, runs = "list", runs_of(lambda l: l)
        is_ua = kind == "goblet" and all(re.match(r"^[A-Z][UA]$", l) for l in labs)
        letters: dict[str, int] = {}
        cols = {name: bl["col"] + i for i, name in enumerate(FIELDS)}
        for gi, run in enumerate(runs):
            letter, part, label = run["lab"][0], "", run["lab"]
            if is_ua:
                part, label = ("Üst" if run["lab"][1] == "U" else "Alt"), letter
            elif kind == "pos":
                label = letter
            number = letters.setdefault(letter, len(letters) + 1) if is_ua else gi + 1
            rows = [_make_row(text, r, cols) for r in run["rows"]]
            out.append(Position(sheet, tank_id, cn, label, number, "", rows, kind=kind,
                                max_fill=SLOTS if kind == "goblet" else len(rows), part=part, special=True, order=gi))
    return out


def find_small_tank_col(text: dict) -> int | None:
    """Küçük tank bloğu: 'HARF' başlığının hemen yanında 'SOYAD' olan sütun."""
    for (r, c), v in sorted(text.items()):
        if fold(v) == "HARF" and fold(text.get((r, c + 1), "")) == "SOYAD":
            return c
    return None


def scan_layout(sheet: str, cells: dict) -> tuple[list[Position], set[tuple[int, int]]]:
    """Bir sayfanın tüm konumları: standart bloklar + (standart yoksa) NO/SOYAD başlıklı özel düzen + küçük tank."""
    positions, marks = scan_sheet_full(sheet, cells)
    if not any(not p.loose for p in positions):
        tank_id, _ = extra_tank_for(sheet)
        extra = scan_extra(sheet, cells, tank_id, "headers")
        positions = extra or positions
        marks = marks | {(p.tank, p.canister) for p in extra}
    text = {k: str(v).strip() for k, v in cells.items() if str(v).strip() != ""}
    col = find_small_tank_col(text)
    if col:
        small = scan_extra(sheet, cells, 103, "ktank", col)
        positions = positions + small
        marks = marks | {(103, p.canister) for p in small}
    return positions, marks


# ---------------- öneri
@dataclass
class Placement:
    position: Position
    rows: list[Row]
    colors: list[str | None]


@dataclass
class Plan:
    placements: list[Placement]

    @property
    def span(self) -> int:
        return len(self.placements)


def _contiguous(rows: list[Row], m: int) -> list[Row]:
    """Mümkünse m ardışık boş satır; yoksa ilk m boş satır."""
    for i in range(len(rows) - m + 1):
        chunk = rows[i:i + m]
        if all(chunk[j + 1].row == chunk[j].row + 1 for j in range(m - 1)):
            return chunk
    return rows[:m]


def suggest(positions: list[Position], n: int, colored: bool = True, limit: int = 10) -> list[Plan]:
    """n straw için en az konuma yayılan, komşu konumlardaki planlar. Aynı konumda renkler farklıdır."""
    groups: dict[tuple, list[Position]] = defaultdict(list)
    for p in positions:
        if p.standard:
            groups[(p.sheet, p.tank, p.canister, p.kat)].append(p)
    plans: list[tuple[tuple, Plan]] = []
    # Önce tüm alt katlar (canister sırasıyla), sonra üst katlar: üst kata, alt kat dolunca geçilir.
    order = sorted(groups.items(), key=lambda kv: (1 if kv[0][3] == "üst" else 0, str(kv[0][0]),
                                                   kv[0][1] or 0, kv[0][2] or 0))
    for gi, (gkey, plist) in enumerate(order):
        plist.sort(key=lambda p: p.number)
        for i, start in enumerate(plist):
            remaining, placements, used_in_plan, prev = n, [], set(), None
            for pos in plist[i:]:
                if prev is not None and pos.number != prev.number + 1:
                    break
                free = pos.free_rows
                avail = pos.free_colors if colored else [None] * len(free)
                m = min(remaining, len(free), len(avail))
                if m == 0:
                    break
                rows = _contiguous(free, m)
                if colored:
                    prefer = [c for c in avail if c not in used_in_plan] + [c for c in avail if c in used_in_plan]
                    cols = sorted(prefer[:m], key=COLORS.index)
                    used_in_plan.update(cols)
                else:
                    cols = [None] * m
                placements.append(Placement(pos, rows, cols))
                remaining -= m
                prev = pos
                if remaining == 0:
                    break
            if remaining == 0 and placements:
                plans.append(((len(placements), gi, start.number), Plan(placements)))
    plans.sort(key=lambda t: t[0])
    return [p for _, p in plans[:limit]]


def summarize(positions: list[Position]) -> list[str]:
    """Kişisel veri içermeyen özet: sayfa/tank/canister/kat başına konum sayıları."""
    by = defaultdict(list)
    for p in positions:
        by[(p.sheet, p.tank, p.canister, p.kat)].append(p)
    lines = []
    for (sheet, tank, can, kat), allp in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0, kv[0][2] or 0, kv[0][3])):
        ps = [p for p in allp if p.standard]
        empty = sum(1 for p in ps if len(p.free_rows) == len(p.rows))
        partial = sum(1 for p in ps if 0 < len(p.free_rows) < len(p.rows))
        full = sum(1 for p in ps if not p.free_rows)
        odd = len(allp) - len(ps)
        unknown = sum(p.unknown_occupied for p in ps)
        lines.append(f"[{sheet}] Tank {tank or '?'} / Canister {can or '?'} / {kat} kat: {len(ps)} standart konum "
                     f"(tamamen boş {empty}, kısmen dolu {partial}, dolu {full}"
                     f"{', standart dışı ' + str(odd) if odd else ''}"
                     f"{', rengi okunamayan dolu satır ' + str(unknown) if unknown else ''})")
    return lines


def describe_plan(plan: Plan) -> str:
    parts = []
    for pl in plan.placements:
        cols = ", ".join(c or "renksiz" for c in pl.colors)
        rows = f"satır {pl.rows[0].row}" + (f"–{pl.rows[-1].row}" if len(pl.rows) > 1 else "")
        parts.append(f"{pl.position.name} ({rows}): {cols}   [boş renkler: {', '.join(pl.position.free_colors) or '-'}]")
    return " → ".join(parts) if len(parts) == 1 else "\n      ".join(parts)


def describe_layout(sheet: str, cells: dict, positions: list[Position]) -> list[str]:
    """Kişisel veri içermez: TANK/CANISTER işaret hücreleri ve her grubun sütun/satır/goblet aralığı."""
    lines = [f"--- {sheet} ---"]
    marks = []
    for (r, c), v in sorted(cells.items()):
        f = fold(v)
        if TANK_RE.match(f) or CAN_RE.match(f) or f.startswith("KUCUK TANK"):
            marks.append(f"{get_column_letter(c)}{r}='{str(v).strip()}'")
    lines.append("İşaret hücreleri: " + (", ".join(marks) or "yok"))
    groups = defaultdict(list)
    for p in positions:
        if not p.loose:
            groups[(p.tank, p.canister, p.suffix, p.rows[0].cells["no"][1])].append(p)
    for (tank, can, suf, col), ps in sorted(groups.items(), key=lambda kv: (kv[0][3], kv[1][0].rows[0].row)):
        rows = [r.row for p in ps for r in p.rows]
        nums = sorted({p.number for p in ps})
        sizes = Counter(len(p.rows) for p in ps)
        lines.append(f"  sütun {get_column_letter(col)}: Tank {tank or '?'} / Canister {can or '?'} / "
                     f"{'A etiketli' if suf else 'harfsiz'}: satır {min(rows)}–{max(rows)}, goblet {nums[0]}–{nums[-1]} "
                     f"({len(ps)} konum; satır sayıları {dict(sorted(sizes.items()))})")
    loose = defaultdict(list)
    for p in positions:
        if p.loose:
            loose[(p.tank, p.canister)].append(p)
    from .profile import shape
    for (tank, can), ps in sorted(loose.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1] or 0)):
        rr = [r.row for p in ps for r in p.rows]
        shapes = Counter(shape(p.label) for p in ps).most_common(6)
        lines.append(f"  etiketsiz dolu satırlar: Tank {tank or '?'} / Canister {can or '?'}: {len(rr)} satır "
                     f"({min(rr)}–{max(rr)}); NO biçimleri: " + ", ".join(f"{k}×{n}" for k, n in shapes))
    odd = [f"{get_column_letter(p.rows[0].cells['no'][1])}{p.rows[0].row}:{p.label}({len(p.rows)} satır)"
           for p in positions if not p.standard and not p.loose]
    lines.append("Standart dışı konumlar: " + (", ".join(odd[:60]) + (" …" if len(odd) > 60 else "") if odd else "yok"))
    from .profile import shape
    shapes = Counter(shape(r.vial) if r.vial else "(boş)" for p in positions if p.standard
                     for r in p.rows if r.occupied and not r.color and vial_kind(r.vial) != "RAPIDI")
    if shapes:
        lines.append("Rengi okunamayan VİAL biçimleri: " + ", ".join(f"{k}×{n}" for k, n in shapes.most_common(10)))
    return lines

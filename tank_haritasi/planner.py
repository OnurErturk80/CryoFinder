"""Yer önerisi: mevcut kullanılan araçtaki (Tank haritası · yer önerisi) puanlama ve yerleştirme kurallarının birebir karşılığı.

Kurallar:
- Aynı hastanın straw'ları mümkünse aynı goblet bölümünde (+50), aynı gobletin diğer katında (+20), aynı canister'da (+8).
- Yarı dolu bölümler önce doldurulur, yeni bölüm açılmaz (+15 + 3×dolu); bölümü tam dolduran seçenek +10.
- Birden fazla bölüme bölünen plan her ek bölüm için -60.
- Rapidi renksizdir; rapidi ile renkli straw aynı bölümde karışmaz.
- Renk, gobletteki sıraya göre atanır (1 mavi, 2 sarı, 3 turuncu, 4 yeşil); kullanılmışsa sıradaki boş renk. Aynı bölümde renk tekrarlanmaz.
- En fazla 3 farklı öneri; her biri gerekçeleriyle.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .harita import COLOR_ORDER, POS_COLOR, Position, fold, parse_date, vial_text


@dataclass
class Item:
    row: int
    pos: int
    device: str
    color: str | None
    hucre: str
    vial: str


@dataclass
class Placement:
    position: Position
    items: list[Item]
    why: list[str]


@dataclass
class Plan:
    score: float
    placements: list[Placement]
    unplaced: int
    warnings: list[str] = field(default_factory=list)


def patient_key(soyad: str, ad: str) -> str:
    return f"{fold(soyad)}|{fold(ad)}"


class Index:
    """Hasta → bölümler, bölüm → hasta sayıları, kardeş (aynı goblet) bölümler."""

    def __init__(self, positions: list[Position]):
        self.by_id = {p.pid: p for p in positions}
        self.patients: dict[str, dict[str, dict]] = {}       # pid -> key -> {"n": sayı, "dates": {date}}
        self.where: dict[str, set[str]] = {}                   # hasta anahtarı -> {pid}
        self.siblings: dict[tuple, list[Position]] = {}
        for p in positions:
            self.siblings.setdefault(p.goblet_key, []).append(p)
            for r in p.rows:
                if r.soyad or r.ad:
                    k = patient_key(r.soyad, r.ad)
                    d = self.patients.setdefault(p.pid, {}).setdefault(k, {"n": 0, "dates": set()})
                    d["n"] += 1
                    pd = parse_date(r.date_text)
                    if pd:
                        d["dates"].add(pd)
                    self.where.setdefault(k, set()).add(p.pid)

    def sib(self, p: Position) -> list[Position]:
        return [x for x in self.siblings.get(p.goblet_key, []) if x.pid != p.pid]


def _free_colors(p: Position) -> list[str]:
    used = p.used_colors
    return [c for c in COLOR_ORDER if c not in used]


def compatible(p: Position, device: str) -> bool:
    if p.kind != "goblet" or p.loose or p.capacity <= 0:
        return False
    if device == "RAPIDI":
        return p.group_type in ("rapid", "empty")
    return p.group_type != "rapid" and len(_free_colors(p)) >= 1


def _cap(p: Position, device: str) -> int:
    cap = p.capacity
    if device != "RAPIDI":
        cap = min(cap, len(_free_colors(p)))
    return cap


def score_group(idx: Index, p: Position, k: int, key: str, date, picked: list[str]) -> tuple[float, list[str]]:
    s, why = 0.0, []
    pg = idx.patients.get(p.pid, {}).get(key)
    if pg:
        s += 50
        why.append(f"Aynı hastanın {pg['n']} straw'ı bu grupta zaten var")
        if date and date in pg["dates"]:
            s += 10
            why.append("Aynı tarihli kayıt burada")
    here = idx.where.get(key, set())
    sib_has = any(x.pid in here or x.pid in picked for x in idx.sib(p))
    if not pg and sib_has:
        s += 20
        why.append(f"Aynı goblet'in {'üst' if p.kat == 'alt' else 'alt'} bölümünde bu hasta var")
    can_has = any(idx.by_id[i].canister_key == p.canister_key for i in list(here) + picked if i in idx.by_id)
    if not pg and not sib_has and can_has:
        s += 8
        why.append("Aynı kanisterde bu hastanın başka örnekleri var")
    if p.occupied_count > 0:
        s += 15 + 3 * p.occupied_count
        why.append(f"Yarı dolu grup ({p.occupied_count}/{p.max_fill} dolu), yeni grup açılmaz")
    else:
        why.append("Boş grup, yeni grup açılır")
    if p.occupied_count + k == p.max_fill:
        s += 10
        why.append("Grubu tam doldurur")
    s -= p.order * 0.01
    return s, why


def assign_slots(p: Position, k: int, device: str) -> list[tuple[int, int, str | None]]:
    """İlk k boş satır; renk gobletteki sıraya göre. (satır, sıra, renk)"""
    used = set(p.used_colors)
    out = []
    for r in p.free_rows[:k]:
        pos = p.rows.index(r) + 1
        color = None
        if device != "RAPIDI":
            pref = POS_COLOR.get(pos)
            if pref and pref not in used:
                color = pref
            else:
                color = next((c for c in COLOR_ORDER if c not in used), None)
            if color:
                used.add(color)
        out.append((r.row, pos, color))
    return out


def _runs(straws: list[dict]) -> int:
    dev = straws[0]["device"]
    n = 0
    while n < len(straws) and (straws[n]["device"] == "RAPIDI") == (dev == "RAPIDI"):
        n += 1
    return n


def _build(idx: Index, cands: list[Position], patient: dict, straws: list[dict], seed: Position | None, cov: int) -> Plan:
    key = patient_key(patient["soyad"], patient["ad"])
    date = patient.get("tarih")
    remaining = list(straws)
    placements: list[Placement] = []
    picked: list[str] = []
    used: set[str] = set()
    total, first = 0.0, True
    while remaining:
        dev = remaining[0]["device"]
        run = _runs(remaining)
        best = None
        for p in cands:
            if p.pid in used or not compatible(p, dev):
                continue
            if first and seed is not None and p.pid != seed.pid:
                continue
            k = min(_cap(p, dev), run)
            if k <= 0:
                continue
            sc, why = score_group(idx, p, k, key, date, picked)
            val = sc + cov * k
            if best is None or val > best[0]:
                best = (val, p, k, sc, why)
        if best is None:
            break
        _, p, k, sc, why = best
        take, remaining = remaining[:k], remaining[k:]
        slots = assign_slots(p, k, dev)
        items = [Item(row, pos, st["device"], color, st.get("hucre", ""),
                      vial_text(st["device"], color, pos)) for (row, pos, color), st in zip(slots, take)]
        placements.append(Placement(p, items, why))
        total += sc
        used.add(p.pid)
        picked.append(p.pid)
        first = False
    warnings: list[str] = []
    if len(placements) > 1:
        total -= 60 * (len(placements) - 1)
        warnings.append(f"Örnekler {len(placements)} farklı gruba bölünüyor. Aynı hastanın straw'ları tek grupta kalamıyor.")
    if remaining:
        warnings.append(f"{len(remaining)} straw için uygun yer bulunamadı.")
    return Plan(total, placements, len(remaining), warnings)


def _seeds(idx: Index, cands: list[Position], patient: dict, dev: str, run: int, scorer) -> list[Position]:
    scored = []
    for p in cands:
        if not compatible(p, dev):
            continue
        k = min(_cap(p, dev), run) if dev is not None else 1
        if k <= 0:
            continue
        scored.append((p, k, scorer(p, k)))
    by_score = sorted(scored, key=lambda t: -t[2])
    by_cover = sorted(scored, key=lambda t: (-t[1], -t[2]))
    seeds, seen = [], set()
    for p, _, _ in by_cover[:8] + by_score[:8]:
        if p.pid not in seen:
            seen.add(p.pid)
            seeds.append(p)
    return seeds


def _finish(plans: list[Plan], max_plans: int) -> list[Plan]:
    plans.sort(key=lambda p: (p.unplaced, -p.score))
    return plans[:max_plans]


def plan_embryo(all_positions: list[Position], candidates: list[Position], patient: dict, straws: list[dict],
                max_plans: int = 3) -> list[Plan]:
    """straws: [{device, hucre}]  (device: CRYOLOCK | VİTRİFİT | CRYOTOP | RAPIDI)."""
    if not straws:
        return []
    straws = sorted(straws, key=lambda s: s["device"] == "RAPIDI")        # renklileri önce, rapidi sonra (sıralama kararlı)
    idx = Index(all_positions)
    key = patient_key(patient["soyad"], patient["ad"])
    dev, run = straws[0]["device"], _runs(straws)
    seeds = _seeds(idx, candidates, patient, dev, run,
                   lambda p, k: score_group(idx, p, k, key, patient.get("tarih"), [])[0])
    plans, seen = [], set()
    for cov in (35, 0):                    # 35: grupları az tut, 0: boşlukları doldur
        for sg in seeds:
            plan = _build(idx, candidates, patient, straws, sg, cov)
            sig = "+".join(sorted(pl.position.pid for pl in plan.placements))
            if sig and sig not in seen:
                seen.add(sig)
                plans.append(plan)
    return _finish(plans, max_plans)


# ---------------- sperm
def _compatible_sperm(p: Position) -> bool:
    return p.capacity > 0 and p.kind in ("pos", "list") and not p.loose


def _score_sperm(idx: Index, p: Position, k: int, key: str, date, picked: list[str]) -> tuple[float, list[str]]:
    if p.kind != "list":
        return score_group(idx, p, k, key, date, picked)
    s, why = 0.0, []
    here = idx.where.get(key, set())
    if any(idx.by_id[i].canister_key == p.canister_key for i in list(here) + picked if i in idx.by_id):
        s += 8
        why.append("Aynı kanisterde bu hastanın başka örnekleri var")
    why.append(f"Boş harf satırı ({p.label}), tüm vial'ler tek satıra yazılır")
    s -= p.order * 0.01
    return s, why


def plan_sperm(all_positions: list[Position], candidates: list[Position], patient: dict, sperm: dict,
               max_plans: int = 3) -> list[Plan]:
    """sperm: {hucre, vials, note}"""
    n = max(1, int(sperm.get("vials") or 1))
    note = (sperm.get("note") or "").strip()
    idx = Index(all_positions)
    key = patient_key(patient["soyad"], patient["ad"])
    date = patient.get("tarih")

    def build(seed, cov):
        remaining, placements, picked, used, total, first = n, [], [], set(), 0.0, True
        while remaining > 0:
            best = None
            for p in candidates:
                if p.pid in used or not _compatible_sperm(p):
                    continue
                if first and seed is not None and p.pid != seed.pid:
                    continue
                k = 1 if p.kind == "list" else min(p.capacity, remaining)
                if k <= 0:
                    continue
                covered = remaining if p.kind == "list" else k
                sc, why = _score_sperm(idx, p, k, key, date, picked)
                val = sc + cov * covered
                if best is None or val > best[0]:
                    best = (val, p, k, covered, sc, why)
            if best is None:
                break
            _, p, k, covered, sc, why = best
            vial = f"{remaining}{(' ' + note) if note else ''}" if p.kind == "list" else f"1{(' ' + note) if note else ''}"
            items = [Item(r.row, p.rows.index(r) + 1, "SPERM", None, sperm.get("hucre", ""), vial) for r in p.free_rows[:k]]
            placements.append(Placement(p, items, why))
            total += sc
            used.add(p.pid)
            picked.append(p.pid)
            remaining -= covered
            first = False
        warnings = []
        if len(placements) > 1:
            total -= 60 * (len(placements) - 1)
            warnings.append(f"Vial'ler {len(placements)} farklı gruba bölünüyor.")
        if remaining > 0:
            warnings.append(f"{remaining} vial için uygun yer bulunamadı.")
        return Plan(total, placements, remaining, warnings)

    scored = []
    for p in candidates:
        if _compatible_sperm(p):
            k = 1 if p.kind == "list" else min(p.capacity, n)
            scored.append((p, n if p.kind == "list" else k, _score_sperm(idx, p, k, key, date, [])[0]))
    by_score = sorted(scored, key=lambda t: -t[2])
    by_cover = sorted(scored, key=lambda t: (-t[1], -t[2]))
    seeds, seen0 = [], set()
    for p, _, _ in by_cover[:8] + by_score[:8]:
        if p.pid not in seen0:
            seen0.add(p.pid)
            seeds.append(p)
    plans, seen = [], set()
    for cov in (35, 0):
        for sg in seeds:
            plan = build(sg, cov)
            sig = "+".join(sorted(pl.position.pid for pl in plan.placements))
            if sig and sig not in seen:
                seen.add(sig)
                plans.append(plan)
    return _finish(plans, max_plans)

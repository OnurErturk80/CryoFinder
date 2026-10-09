import io
import re
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import load_workbook

from tank_haritasi import onedrive
from tank_haritasi.backup import Backuper, BackupError
from tank_haritasi.changelog import ChangeLog
from tank_haritasi.editor import parse_change, run_changes
from tank_haritasi.excel_api import ExcelApiBackend, probe
from tank_haritasi.graph import ForbiddenOperation, GraphClient
from tank_haritasi.memory import MemoryBackend
from tests.fake_onedrive import FakeOneDrive, make_xlsx

PATH = "TANK_HARITASI_TEST.xlsx"
SEED = {"A1": "Kanister 1", "B1": "Boş", "C3": "=1+1"}


def setup(excel_api=False, files=None):
    fake = FakeOneDrive(files or {PATH: make_xlsx(SEED)}, excel_api=excel_api)
    return fake, GraphClient(lambda: "tok", session=fake, sleep=lambda s: None)


def logger(tmp_path):
    return ChangeLog(tmp_path / "log.jsonl", {"file": PATH})


def test_no_delete_anywhere():
    _, c = setup()
    with pytest.raises(ForbiddenOperation):
        c.request("DELETE", "/me/drive/items/ID1")
    src = "\n".join(p.read_text(encoding="utf-8") for p in Path("tank_haritasi").glob("*.py"))
    methods = set(re.findall(r"""\.request\(\s*["'](\w+)["']""", src))
    assert methods and methods <= {"GET", "POST", "PUT", "PATCH"}
    assert not re.search(r"\.delete\(|os\.remove|unlink|rmtree|shutil\.move", src)


def test_probe_detects_missing_excel_api():
    fake, c = setup(excel_api=False)
    ok, steps = probe(c, "ID1")
    assert not ok and not steps[-1][0]


def test_probe_ok_when_supported():
    fake, c = setup(excel_api=True)
    assert probe(c, "ID1")[0]


def test_parse_change():
    ch = parse_change("Tank1!b3=Yeni = değer")
    assert (ch.sheet, ch.cell, ch.new_value) == ("Tank1", "B3", "Yeni = değer")
    with pytest.raises(ValueError):
        parse_change("B3=1")


def test_memory_flow_backup_commit_log_and_decline(tmp_path):
    fake, c = setup()
    meta, data = onedrive.download_consistent(c, PATH)
    be = MemoryBackend(c, meta, data)
    bk = Backuper(c, "Yedekler", meta["name"], lambda: data, now=lambda: datetime(2026, 10, 9, 12, 0, 0))
    answers = iter([True, False])
    changes = [parse_change("Tank1!B1=Dolu"), parse_change("Tank1!A1=Başka")]
    done = run_changes(be, changes, confirm=lambda q: next(answers), log=logger(tmp_path),
                       ensure_backup=bk.ensure, say=lambda *_: None)
    assert [d.cell for d in done] == ["B1"]
    problems, lost = be.verify(be.serialize())
    assert problems == [] and lost == []
    be.commit(be.serialize())
    wb = load_workbook(io.BytesIO(fake.items[fake.by_path(PATH)]["data"]))
    assert wb["Tank1"]["B1"].value == "Dolu" and wb["Tank1"]["A1"].value == "Kanister 1"
    backup = fake.items[fake.by_path("Yedekler/TANK_HARITASI_TEST_yedek_2026-10-09_120000.xlsx")]
    assert backup["data"] == data  # yedek, değişiklikten ÖNCEKİ içerik
    events = [l for l in (tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any('"declined"' in e for e in events) and any('"staged"' in e for e in events)
    assert not any(m == "DELETE" for m, _ in fake.log)


def test_etag_conflict_writes_nothing(tmp_path):
    fake, c = setup()
    meta, data = onedrive.download_consistent(c, PATH)
    be = MemoryBackend(c, meta, data)
    be.set_cell("Tank1", "B1", "Benim")
    theirs = make_xlsx({"A1": "Başkasının düzenlemesi"})
    fake.external_edit(PATH, theirs)
    with pytest.raises(onedrive.ConflictError):
        be.commit(be.serialize())
    assert fake.items[fake.by_path(PATH)]["data"] == theirs


def test_no_write_without_approval_or_backup(tmp_path):
    fake, c = setup()
    meta, data = onedrive.download_consistent(c, PATH)
    be = MemoryBackend(c, meta, data)
    # onay yok → yedek de yazma da yok
    run_changes(be, [parse_change("Tank1!B1=X")], confirm=lambda q: False, log=logger(tmp_path),
                ensure_backup=lambda: pytest.fail("yedek istenmemeliydi"), say=lambda *_: None)
    assert be.staged == {}
    # yedek başarısız → yazma yok
    def boom(): raise BackupError("disk dolu")
    with pytest.raises(BackupError):
        run_changes(be, [parse_change("Tank1!B1=X")], confirm=lambda q: True, log=logger(tmp_path),
                    ensure_backup=boom, say=lambda *_: None)
    assert be.staged == {}


def test_formula_cells_and_values_refused(tmp_path):
    fake, c = setup()
    meta, data = onedrive.download_consistent(c, PATH)
    be = MemoryBackend(c, meta, data)
    done = run_changes(be, [parse_change("Tank1!C3=5"), parse_change("Tank1!B1==SUM(A1)")],
                       confirm=lambda q: True, log=logger(tmp_path), ensure_backup=lambda: {"path": "x"},
                       say=lambda *_: None)
    assert done == []


def test_verify_catches_unapproved_diff(tmp_path):
    fake, c = setup()
    meta, data = onedrive.download_consistent(c, PATH)
    be = MemoryBackend(c, meta, data)
    be.set_cell("Tank1", "B1", "ok")
    be.wb["Tank1"]["A1"] = "sızan değişiklik"
    problems, _ = be.verify(be.serialize())
    assert problems == ["Tank1!A1 onaylanmadığı hâlde değişti"]


def test_excel_api_mode_applies_and_logs(tmp_path):
    fake, c = setup(excel_api=True)
    be = ExcelApiBackend(c, "ID1"); be.open()
    bk = Backuper(c, "Yedekler", PATH, lambda: onedrive.download(c, "ID1"))
    done = run_changes(be, [parse_change("Tank1!B1=Excel API")], confirm=lambda q: True,
                       log=logger(tmp_path), ensure_backup=bk.ensure, say=lambda *_: None)
    be.close()
    assert len(done) == 1
    assert load_workbook(io.BytesIO(fake.items["ID1"]["data"]))["Tank1"]["B1"].value == "Excel API"
    assert fake.by_path(next(p for p in [i["path"] for i in fake.items.values()] if p.startswith("Yedekler/T")))


def test_gitignore_protects_secrets():
    text = Path(".gitignore").read_text()
    for pat in (".env", ".token_cache", "degisiklik_kaydi", "*.xlsx"):
        assert pat in text


# ---- arayüz servisi ve yerel sunucu güvenliği
import json
import urllib.error
import urllib.request

from tank_haritasi.service import EditService
from tank_haritasi.webui import make_server, serve_in_thread


def make_service(tmp_path, excel_api=True):
    fake, c = setup(excel_api=excel_api)
    if excel_api:
        be = ExcelApiBackend(c, "ID1")
        data = None
    else:
        meta, data = onedrive.download_consistent(c, PATH)
        be = MemoryBackend(c, meta, data)
    getter = (lambda: data) if data else (lambda: onedrive.download(c, "ID1"))
    bk = Backuper(c, "Yedekler", PATH, getter, now=lambda: datetime(2026, 10, 9, 12, 0, 0))
    return fake, EditService(be, bk, logger(tmp_path), PATH)


def test_service_propose_apply_backup_and_single_use(tmp_path):
    fake, svc = make_service(tmp_path)
    p = svc.propose("Tank1", "B1", "Yeni")
    assert p["ok"] and p["old"] == "Boş" and p["new"] == "Yeni"
    assert not any(v["path"].startswith("Yedekler/T") for v in fake.items.values())  # onaydan önce yedek/yazma yok
    r = svc.apply(p["id"])
    assert r["ok"] and r["backup"].startswith("Yedekler/")
    assert load_workbook(io.BytesIO(fake.items["ID1"]["data"]))["Tank1"]["B1"].value == "Yeni"
    assert not svc.apply(p["id"])["ok"]  # tek kullanımlık


def test_service_refuses_formula_and_detects_stale(tmp_path):
    fake, svc = make_service(tmp_path)
    assert not svc.propose("Tank1", "C3", "5")["ok"]
    assert not svc.propose("Tank1", "B1", "=1+1")["ok"]
    p = svc.propose("Tank1", "B1", "Yeni")
    fake.external_edit(PATH, make_xlsx({"B1": "başkası yazdı"}))
    assert not svc.apply(p["id"])["ok"]
    assert load_workbook(io.BytesIO(fake.items["ID1"]["data"]))["Tank1"]["B1"].value == "başkası yazdı"


def test_service_decline_writes_nothing(tmp_path):
    fake, svc = make_service(tmp_path)
    p = svc.propose("Tank1", "B1", "X")
    svc.decline(p["id"])
    assert not svc.apply(p["id"])["ok"]
    assert "declined" in (tmp_path / "log.jsonl").read_text(encoding="utf-8")


def test_service_memory_commit_flow(tmp_path):
    fake, svc = make_service(tmp_path, excel_api=False)
    svc.apply(svc.propose("Tank1", "B1", "Bellek")["id"])
    assert svc.state()["staged"] == 1
    assert svc.prepare_commit()["ok"]
    assert svc.commit()["ok"]
    assert load_workbook(io.BytesIO(fake.items["ID1"]["data"]))["Tank1"]["B1"].value == "Bellek"
    svc.apply(svc.propose("Tank1", "B1", "İkinci")["id"])
    assert svc.commit()["ok"]  # eTag güncellendiği için ikinci yükleme çakışmaz


def _call(url, token=None, host=None, body=None, origin=None, ctype="application/json"):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 method="POST" if body is not None else "GET")
    if token: req.add_header("X-Session-Token", token)
    if host: req.add_header("Host", host)
    if origin: req.add_header("Origin", origin)
    if body is not None: req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def test_webui_security_and_happy_path(tmp_path):
    fake, svc = make_service(tmp_path)
    srv, token = make_server(svc, tmp_path / "log.jsonl")
    serve_in_thread(srv)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        assert _call(base + "/api/state")[0] == 403                                   # anahtarsız
        assert _call(base + "/api/state", token="yanlis")[0] == 403
        assert _call(base + "/api/state", token=token, host="evil.example")[0] == 403  # DNS rebinding
        assert _call(base + "/api/propose", token=token, body={}, origin="http://evil.example")[0] == 403
        assert _call(base + "/api/propose", token=token, body={"sheet": "Tank1", "cell": "B1"}, ctype="text/plain")[0] == 415
        code, page = _call(base + "/")
        assert code == 200 and token in page
        assert json.loads(_call(base + "/api/state", token=token)[1])["mode"] == "excel-api"
        view = json.loads(_call(base + "/api/sheet?name=Tank1", token=token)[1])
        assert view["rows"][0][0] == "Kanister 1"
        p = json.loads(_call(base + "/api/propose", token=token, body={"sheet": "Tank1", "cell": "B1", "value": "Web"})[1])
        assert json.loads(_call(base + "/api/apply", token=token, body={"id": p["id"]})[1])["ok"]
        assert _call(base + "/api/delete", token=token, body={})[0] == 404             # silme ucu yok
    finally:
        srv.shutdown()


def test_profile_hides_personal_data():
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill
    from tank_haritasi.profile import profile_workbook
    wb = Workbook(); ws = wb.active; ws.title = "TANK 1"
    ws["A1"] = "TANK 1"; ws["A3"] = "CANISTER 1"
    for i, h in enumerate(["NO", "SOYAD", "AD", "TARİH", "VİAL"], 1):
        ws.cell(5, i, h)
    for r, (no, soyad, ad, vial) in enumerate([("1A", "GİZLİSOYAD", "GİZLİAD", "RAPIDI 1"),
                                               ("1B", "BAŞKASOYAD", "BAŞKAAD", "VİTRİFİT MAVİ")], 6):
        ws.cell(r, 1, no); ws.cell(r, 2, soyad); ws.cell(r, 3, ad); ws.cell(r, 4, 44597); ws.cell(r, 5, vial)
        ws.cell(r, 5).fill = PatternFill("solid", fgColor="0000FF")
    b = io.BytesIO(); wb.save(b)
    out = "\n".join(profile_workbook(b.getvalue()))
    for secret in ("GİZLİSOYAD", "GİZLİAD", "BAŞKASOYAD", "BAŞKAAD"):
        assert secret not in out
    assert "CANISTER 1" in out and "VİTRİFİT MAVİ" in out and "0000FF" in out and "SOYAD" in out


# ---- harita modeli ve yer önerisi
from tank_haritasi.harita import COLORS, scan_sheet, suggest, summarize, vial_color, vial_text


def make_map_cells():
    """Tek sayfa, TANK 1, iki canister bloğu (sütun A ve I); her blokta 1A..8A (4'er satır)."""
    cells = {(1, 1): "TANK 1", (3, 1): "CANISTER 1", (3, 9): "CANISTER 2"}
    def put(block_col, row, soyad, vial):
        cells[(row, block_col + 1)], cells[(row, block_col + 2)] = soyad, "Ad"
        cells[(row, block_col + 5)], cells[(row, block_col + 6)] = "D5 (4AA)", vial
    for col in (1, 9):
        for g in range(1, 9):
            for k in range(4):
                cells[(5 + (g - 1) * 4 + k, col)] = f"{g}A"
    filled = {1: ["1 RAPIDI 1", "1 RAPIDI 2", "1 RAPIDI 3", "1 RAPIDI 4"],           # 1A dolu (rapidi)
              6: ["1 RAPIDI 1", "1 RAPIDI 2", "1 RAPIDI 3", "1 RAPIDI 4"],           # 6A dolu (rapidi)
              2: ["1 VİTRİFİTMAVİ", "1 RAPIDI 2", "1 RAPIDI 3"],                       # 2A: 1 boş satır, mavi kullanılmış
              4: ["1 CRYOLOCKSARI", "1 VİTRİFİTMAVİ"]}                                   # 4A: 2 boş satır
    for g, vials in filled.items():
        for k, v in enumerate(vials):
            put(1, 5 + (g - 1) * 4 + k, "SOYAD" + "ABCDEFGH"[g - 1], v)
    for g in range(1, 9):  # 2. canister: tamamen boş, ama soyad sütununda yeterli metin olsun diye 5-8. goblet dolu
        if g >= 5:
            for k in range(4):
                put(9, 5 + (g - 1) * 4 + k, "BSOYAD" + "ABCDEFGH"[g - 1], f"1 RAPIDI {k + 1}")
    return cells


def test_vial_helpers():
    assert vial_color("1 VİTRİFİTMAVİ") == "MAVİ" and vial_color("1 CRYOLOCKSARI") == "SARI"
    assert vial_color("1 vitrifityeşil") == "YEŞİL" and vial_color("1 CRYOTOPTURUNCU") == "TURUNCU"
    assert vial_color("1 RAPIDI 1") is None
    assert vial_text("CRYOLOCK", "SARI") == "1 CRYOLOCKSARI"


def test_scan_finds_positions_and_state():
    ps = scan_sheet("S", make_map_cells())
    assert len(ps) == 16 and all(len(p.rows) == 4 for p in ps)
    p = {(x.canister, x.label): x for x in ps}
    assert p[(1, "1A")].free_rows == [] and p[(1, "3A")].free_colors == COLORS
    assert len(p[(1, "2A")].free_rows) == 1 and p[(1, "2A")].free_colors == ["SARI", "YEŞİL", "TURUNCU"]
    assert p[(1, "4A")].used_colors == {"SARI", "MAVİ"} and p[(1, "2A")].tank == 1
    text = "\n".join(summarize(ps))
    assert "SOYAD" not in text and "Canister 1" in text


def test_suggest_two_straws_different_colors_adjacent():
    ps = [p for p in scan_sheet("S", make_map_cells()) if p.canister == 1]
    plan = suggest(ps, 2)[0]
    pl = plan.placements[0]
    assert plan.span == 1 and pl.position.label == "3A" and pl.colors == ["MAVİ", "SARI"]
    assert pl.rows[1].row == pl.rows[0].row + 1  # yan yana satırlar


def test_suggest_never_repeats_color_in_a_goblet_and_spans_neighbours():
    ps = [p for p in scan_sheet("S", make_map_cells()) if p.canister == 1]
    for n in (1, 2, 3, 5, 6):
        for plan in suggest(ps, n, limit=50):
            assert sum(len(pl.rows) for pl in plan.placements) == n
            for pl in plan.placements:
                taken = pl.position.used_colors
                assert len(set(pl.colors)) == len(pl.colors) and not (set(pl.colors) & taken)
                assert all(not r.occupied for r in pl.rows)
            nums = [pl.position.number for pl in plan.placements]
            assert nums == list(range(nums[0], nums[0] + len(nums)))  # komşu gobletler
    five = suggest(ps, 5)[0]
    assert five.span == 2  # 4'ten fazla straw tek goblete sığmaz


def test_suggest_colorless_uses_free_rows_only():
    ps = [p for p in scan_sheet("S", make_map_cells()) if p.canister == 1]
    plan = suggest(ps, 3, colored=False)[0]
    assert plan.placements[0].colors == [None, None, None]


def test_level_comes_from_sheet_and_lower_levels_suggested_first():
    from tank_haritasi.harita import Position, Row
    def pos(sheet, can):
        return Position(sheet, 1, can, "1", 1, "", [Row(i, {}, False, None, "") for i in range(1, 5)])
    ps = [pos("Tank 1-5 üst", 1), pos("TANK 5", 2)]      # canister 1'in ÜST katı, canister 2'nin ALT katı
    assert [p.kat for p in ps] == ["üst", "alt"]
    first = suggest(ps, 2)[0].placements[0].position
    assert first.kat == "alt" and first.canister == 2


def test_tank_marker_in_other_column_is_ignored_and_small_tank_region_skipped():
    cells = make_map_cells()
    cells[(2, 53)] = "TANK 3"                      # küçük tank etiketi (başka sütun) - bölüm başlığı değil
    cells[(30, 1)] = "KÜÇÜK TANK"                  # bu satırdan sonrası haritaya dahil değil
    ps = scan_sheet("S", cells)
    assert {p.tank for p in ps} == {1}
    assert all(p.rows[0].row < 30 for p in ps)


def test_nonstandard_positions_are_never_suggested():
    from tank_haritasi.harita import Position, Row
    odd = Position("S", 1, 1, "9", 9, "", [Row(1, {}, False, None, "")])
    assert not odd.standard and suggest([odd], 1) == []


def test_layout_detail_and_rapidi_not_unknown():
    from tank_haritasi.harita import describe_layout
    cells = make_map_cells()
    ps = scan_sheet("S", cells)
    text = "\n".join(describe_layout("S", cells, ps))
    assert "A1='TANK 1'" in text and "A3='CANISTER 1'" in text and "satır 5–36" in text and "SOYAD" not in text
    assert next(p for p in ps if p.canister == 1 and p.label == "1A").unknown_occupied == 0  # rapidi renksiz, belirsiz değil


# ---- yeni hasta kaydı
def make_map_xlsx(sheet="TANK 5"):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = sheet
    for (r, c), v in make_map_cells().items():
        ws.cell(r, c, v)
    ws.cell(5, 5, date(2025, 1, 2)); ws.cell(5, 5).number_format = "dd.mm.yyyy"   # biçim referansı (1A'nın ilk satırı)
    b = io.BytesIO(); wb.save(b); return b.getvalue()


from datetime import date


def make_reg_service(tmp_path, excel_api=True):
    fake = FakeOneDrive({PATH: make_map_xlsx()}, excel_api=excel_api)
    c = GraphClient(lambda: "tok", session=fake, sleep=lambda s: None)
    if excel_api:
        be, data = ExcelApiBackend(c, "ID1"), None
    else:
        meta, data = onedrive.download_consistent(c, PATH)
        be = MemoryBackend(c, meta, data)
    getter = (lambda: data) if data else (lambda: onedrive.download(c, "ID1"))
    bk = Backuper(c, "Yedekler", PATH, getter, now=lambda: datetime(2026, 10, 9, 12, 0, 0))
    return fake, EditService(be, bk, logger(tmp_path), PATH)


def sheet_of(fake):
    return load_workbook(io.BytesIO(fake.items["ID1"]["data"]))["TANK 5"]


PATIENT = {"soyad": "yılmaz", "ad": "ayşe", "esi": "", "tarih": "2026-10-09"}


def test_registration_end_to_end_excel_api(tmp_path):
    fake, svc = make_reg_service(tmp_path)
    assert svc.reg_options()["tanks"] == [1]
    sug = svc.reg_suggest(1, 2, "otomatik")
    plan = sug["plans"][0]
    pl = plan["placements"][0]
    assert len(sug["plans"]) > 0 and plan["span"] == 1 and len(pl["rows"]) == 2
    straws = [{"color": c, "hucre": "D5 (4AA)"} for c in pl["colors"]]
    prev = svc.reg_preview(plan["id"], "CRYOLOCK", straws, PATIENT)
    assert prev["ok"] and prev["count"] == 10                 # 2 straw × (soyad, ad, tarih, hücre, vial)
    assert not any(v["path"].startswith("Yedekler/T") for v in fake.items.values())   # onaydan önce yazma/yedek yok
    res = svc.reg_apply(prev["id"])
    assert res["ok"] and res["backup"].startswith("Yedekler/")
    ws = sheet_of(fake)
    r0, r1 = pl["rows"]
    assert (ws.cell(r0, 2).value, ws.cell(r0, 3).value) == ("YILMAZ", "AYŞE")          # Türkçe büyük harf
    assert ws.cell(r0, 7).value == f"1 CRYOLOCK{pl['colors'][0]}"
    assert ws.cell(r1, 7).value == f"1 CRYOLOCK{pl['colors'][1]}" and pl["colors"][0] != pl["colors"][1]
    assert r1 == r0 + 1                                                                  # yan yana
    assert ws.cell(r0, 5).value in (46304, 46304.0)                                     # 2026-10-09 Excel seri numarası
    assert "registration" in (tmp_path / "log.jsonl").read_text(encoding="utf-8")
    assert not svc.reg_apply(prev["id"])["ok"]                                           # tek kullanımlık


def test_registration_validation(tmp_path):
    fake, svc = make_reg_service(tmp_path)
    plan = svc.reg_suggest(1, 2, "otomatik")["plans"][0]
    pl = plan["placements"][0]
    same = [{"color": pl["colors"][0], "hucre": "D5"}] * 2
    assert not svc.reg_preview(plan["id"], "CRYOLOCK", same, PATIENT)["ok"]                          # aynı renk iki kez
    ok = [{"color": c, "hucre": "D5"} for c in pl["colors"]]
    assert not svc.reg_preview(plan["id"], "CRYOLOCK", ok, {**PATIENT, "soyad": ""})["ok"]           # soyad zorunlu
    assert not svc.reg_preview(plan["id"], "CRYOLOCK", ok, {**PATIENT, "tarih": "09.10.2026"})["ok"]  # tarih biçimi
    assert not svc.reg_preview(plan["id"], "BILINMEYEN", ok, PATIENT)["ok"]
    assert not svc.reg_preview(plan["id"], "CRYOLOCK", [{"color": "MOR", "hucre": "D5"}] * 2, PATIENT)["ok"]
    assert not svc.reg_preview(plan["id"], "CRYOLOCK", [{"color": c, "hucre": ""} for c in pl["colors"]], PATIENT)["ok"]
    assert not svc.reg_preview(plan["id"], "CRYOLOCK", [{"color": c, "hucre": "=1+1"} for c in pl["colors"]], PATIENT)["ok"]


def test_registration_aborts_if_rows_filled_meanwhile(tmp_path):
    fake, svc = make_reg_service(tmp_path)
    plan = svc.reg_suggest(1, 2, "otomatik")["plans"][0]
    pl = plan["placements"][0]
    prev = svc.reg_preview(plan["id"], "VİTRİFİT", [{"color": c, "hucre": "D5"} for c in pl["colors"]], PATIENT)
    wb = load_workbook(io.BytesIO(fake.items["ID1"]["data"]))
    wb["TANK 5"].cell(pl["rows"][1], 2).value = "BAŞKASI"        # biri aynı satıra yazdı
    b = io.BytesIO(); wb.save(b); fake.external_edit(PATH, b.getvalue())
    res = svc.reg_apply(prev["id"])
    assert not res["ok"] and "Hiçbir şey yazılmadı" in res["message"]
    assert sheet_of(fake).cell(pl["rows"][0], 2).value is None


def test_registration_memory_mode_stages_then_commits(tmp_path):
    fake, svc = make_reg_service(tmp_path, excel_api=False)
    plan = svc.reg_suggest(1, 3, "alt")["plans"][0]
    pl = plan["placements"][0]
    prev = svc.reg_preview(plan["id"], "CRYOTOP", [{"color": c, "hucre": "OOSİT"} for c in pl["colors"]], PATIENT)
    assert svc.reg_apply(prev["id"])["ok"] and svc.state()["staged"] == prev["count"]
    assert sheet_of(fake).cell(pl["rows"][0], 2).value is None            # henüz yüklenmedi
    assert svc.commit()["ok"]
    assert sheet_of(fake).cell(pl["rows"][0], 2).value == "YILMAZ"


def test_registration_http_endpoints(tmp_path):
    fake, svc = make_reg_service(tmp_path)
    srv, token = make_server(svc, tmp_path / "log.jsonl"); serve_in_thread(srv)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        assert _call(base + "/api/reg/options")[0] == 403
        sug = json.loads(_call(base + "/api/reg/suggest", token=token, body={"tank": 1, "n": 1, "kat": "otomatik"})[1])
        assert sug["ok"] and sug["plans"]
    finally:
        srv.shutdown()


# ---- hasta çıkarma (hücre temizleme)
def register_patient(svc, n=2, straw_type="CRYOLOCK"):
    plan = svc.reg_suggest(1, n, "otomatik")["plans"][0]
    pl = plan["placements"][0]
    prev = svc.reg_preview(plan["id"], straw_type, [{"color": c, "hucre": "D5 (4AA)"} for c in pl["colors"]], PATIENT)
    assert svc.reg_apply(prev["id"])["ok"]
    return pl["rows"]


def test_removal_clears_cells_keeps_label_makes_backup_and_logs(tmp_path):
    fake, svc = make_reg_service(tmp_path)
    rows = register_patient(svc)
    n_backups = lambda: sum(v["path"].startswith("Yedekler/T") for v in fake.items.values())
    hits = svc.rem_search("yilmaz")["hits"]                      # 'yilmaz' ~ 'YILMAZ' (Türkçe harf duyarsız)
    assert [h["row"] for h in hits] == rows and hits[0]["ad"] == "AYŞE" and hits[0]["kat"] == "alt"
    prev = svc.rem_preview([{"sheet": h["sheet"], "row": h["row"], "col": h["col"]} for h in hits])
    assert prev["ok"] and prev["rows"] == 2 and prev["count"] == 10 and all(c["new"] == "" for c in prev["changes"])
    before = fake.items["ID1"]["data"]
    res = svc.rem_apply(prev["id"])
    assert res["ok"] and res["count"] == 10
    ws = sheet_of(fake)
    for r in rows:
        assert [ws.cell(r, c).value for c in range(2, 8)] == [None] * 6      # SOYAD..VİAL boş
        assert ws.cell(r, 1).value == "3A"                                      # NO etiketi kalır
    assert svc.rem_search("yilmaz")["hits"] == []
    log = (tmp_path / "log.jsonl").read_text(encoding="utf-8")
    assert '"removal"' in log and "YILMAZ" in log                               # eski değerler kayıtta
    assert n_backups() >= 1 and fake.log and not any(m == "DELETE" for m, _ in fake.log)


def test_removal_frees_the_color_again(tmp_path):
    fake, svc = make_reg_service(tmp_path)
    rows = register_patient(svc)
    hits = svc.rem_search("yilmaz")["hits"]
    svc.rem_apply(svc.rem_preview([{"sheet": h["sheet"], "row": h["row"], "col": h["col"]} for h in hits])["id"])
    plan = svc.reg_suggest(1, 2, "otomatik")["plans"][0]
    assert plan["placements"][0]["rows"] == rows and plan["placements"][0]["colors"] == ["MAVİ", "SARI"]


def test_removal_partial_selection_and_validation(tmp_path):
    fake, svc = make_reg_service(tmp_path)
    rows = register_patient(svc)
    first = svc.rem_search("yilmaz")["hits"][0]
    sheet, col = first["sheet"], first["col"]
    assert not svc.rem_search("y")["ok"]                                          # çok kısa
    assert not svc.rem_preview([])["ok"]
    assert not svc.rem_preview([{"sheet": sheet, "row": 999, "col": col}])["ok"]              # olmayan satır
    assert not svc.rem_preview([{"sheet": sheet, "row": rows[0], "col": col}] * 2)["ok"]
    assert not svc.rem_preview([{"sheet": sheet, "row": rows[0], "col": 9}])["ok"]                # başka blok: o satır boş  # yinelenen
    prev = svc.rem_preview([{"sheet": sheet, "row": rows[0], "col": col}])        # yalnızca ilk straw
    assert svc.rem_apply(prev["id"])["ok"]
    ws = sheet_of(fake)
    assert ws.cell(rows[0], 2).value is None and ws.cell(rows[1], 2).value == "YILMAZ"
    assert not svc.rem_apply(prev["id"])["ok"]                                    # tek kullanımlık


def test_removal_aborts_when_row_changed_before_approval(tmp_path):
    fake, svc = make_reg_service(tmp_path)
    rows = register_patient(svc)
    first = svc.rem_search("yilmaz")["hits"][0]
    prev = svc.rem_preview([{"sheet": first["sheet"], "row": rows[0], "col": first["col"]}])
    wb = load_workbook(io.BytesIO(fake.items["ID1"]["data"]))
    wb["TANK 5"].cell(rows[0], 2).value = "BAŞKASI"
    b = io.BytesIO(); wb.save(b); fake.external_edit(PATH, b.getvalue())
    res = svc.rem_apply(prev["id"])
    assert not res["ok"] and "Hiçbir şey silinmedi" in res["message"]
    assert sheet_of(fake).cell(rows[0], 2).value == "BAŞKASI"


def test_removal_memory_mode_and_http(tmp_path):
    fake, svc = make_reg_service(tmp_path, excel_api=False)
    rows = register_patient(svc)
    assert svc.commit()["ok"]
    hits = svc.rem_search("ayşe")["hits"]
    assert len(hits) == 2
    prev = svc.rem_preview([{"sheet": h["sheet"], "row": h["row"], "col": h["col"]} for h in hits])
    assert svc.rem_apply(prev["id"])["ok"] and svc.commit()["ok"]
    assert sheet_of(fake).cell(rows[0], 2).value is None
    srv, token = make_server(svc, tmp_path / "log.jsonl"); serve_in_thread(srv)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        assert _call(base + "/api/rem/search", body={"q": "ab"})[0] == 403
        ok = json.loads(_call(base + "/api/rem/search", token=token, body={"q": "soyad"})[1])
        assert ok["ok"]
    finally:
        srv.shutdown()


def test_sheet_view_can_return_whole_sheet(tmp_path):
    fake, svc = make_reg_service(tmp_path)
    v = svc.sheet_view("TANK 5", 1, 5000)
    assert v["max_row"] >= 36 and len(v["rows"]) == v["max_row"] and v["row0"] == 1


# ---- görsel tank haritası
def make_two_level_xlsx():
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = "TANK 1+2+3"
    for (r, c), v in make_map_cells().items():
        ws.cell(r, c, v)
    up = wb.create_sheet("Tank 1-5 üst")                      # üst kat: adında "üst" geçen sayfa
    for (r, c), v in make_map_cells().items():
        up.cell(r, c, v)
    for k in range(4):                                         # üstte 3. goblet 2 straw ile doldurulmuş
        pass
    up.cell(13, 2, "UYELIK"); up.cell(13, 3, "Ad"); up.cell(13, 6, "D5 (4AA)"); up.cell(13, 7, "1 VİTRİFİTYEŞİL")
    b = io.BytesIO(); wb.save(b); return b.getvalue()


def make_viz_service(tmp_path):
    fake = FakeOneDrive({PATH: make_two_level_xlsx()}, excel_api=True)
    c = GraphClient(lambda: "tok", session=fake, sleep=lambda s: None)
    bk = Backuper(c, "Yedekler", PATH, lambda: onedrive.download(c, "ID1"))
    return fake, EditService(ExcelApiBackend(c, "ID1"), bk, logger(tmp_path), PATH)


def test_map_view_structure_states_and_no_names(tmp_path):
    fake, svc = make_viz_service(tmp_path)
    m = svc.map_view(1)
    assert m["ok"] and m["has_ust"] and [c["canister"] for c in m["canisters"]] == [1, 2]
    g = {x["n"]: x for x in m["canisters"][0]["goblets"]}
    assert len(g) == 8
    assert [s["state"] for s in g[1]["alt"]["slots"]] == ["rapidi"] * 4
    assert [s["state"] for s in g[2]["alt"]["slots"]] == ["color", "rapidi", "rapidi", "empty"]
    assert g[2]["alt"]["slots"][0]["color"] == "MAVİ" and g[3]["alt"]["slots"][0]["state"] == "empty"
    assert g[3]["ust"]["slots"][0]["state"] == "color" and g[3]["ust"]["slots"][0]["color"] == "YEŞİL"   # üst kat ayrı sayfadan
    st = m["stats"]
    assert st["slots"] == sum(len(x["slots"]) for c in m["canisters"] for gg in c["goblets"]
                              for x in (gg["alt"], gg["ust"]) if x)
    assert st["MAVİ"] >= 1 and st["free"] >= 1
    assert "SOYAD" not in json.dumps(m, ensure_ascii=False) and "UYELIK" not in json.dumps(m, ensure_ascii=False)  # adlar yok


def test_map_slot_and_find(tmp_path):
    fake, svc = make_viz_service(tmp_path)
    sid = next(s["id"] for c in svc.map_view(1)["canisters"] for gg in c["goblets"]
               for x in (gg["alt"], gg["ust"]) if x for s in x["slots"] if s["state"] == "color" and s["color"] == "MAVİ")
    d = svc.map_slot(sid)
    assert d["ok"] and d["soyad"] == "SOYADA" or d["soyad"].startswith("SOYAD")
    assert not svc.map_slot("bozuk")["ok"] and not svc.map_slot("1:1:YOKSAYFA")["ok"]
    hits = svc.map_find("uyelik", 1)
    assert hits["ok"] and len(hits["hits"]) == 1 and "UYELIK" not in json.dumps(hits, ensure_ascii=False)
    assert svc.map_find("uyelik", 5)["hits"] == [] and not svc.map_find("u")["ok"]
    assert svc.map_view(9)["ok"] is False


def test_map_endpoints_require_token(tmp_path):
    fake, svc = make_viz_service(tmp_path)
    srv, token = make_server(svc, tmp_path / "log.jsonl"); serve_in_thread(srv)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        assert _call(base + "/api/map?tank=1")[0] == 403
        assert _call(base + "/api/map/find", body={"q": "ab"})[0] == 403
        assert json.loads(_call(base + "/api/map?tank=1", token=token)[1])["ok"]
    finally:
        srv.shutdown()


def test_page_sends_selected_rows_per_page_to_server():
    """'Tümü' seçimi sunucuya gerçekten iletilmeli (sabit 50 kalmamalı)."""
    from tank_haritasi.webui import PAGE
    assert "rows=50" not in PAGE and 'rows=${$("per").value}' in PAGE
    for v in ("50", "100", "250", "5000"):
        assert f'<option value="{v}">' in PAGE


def test_sheet_view_serves_requested_row_counts(tmp_path):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = "BUYUK"
    for r in range(1, 596):
        for c in range(1, 60):
            if (r + c) % 3:
                ws.cell(r, c, f"r{r}c{c}")
    b = io.BytesIO(); wb.save(b)
    fake = FakeOneDrive({PATH: b.getvalue()}, excel_api=True)
    cl = GraphClient(lambda: "tok", session=fake, sleep=lambda s: None)
    svc = EditService(ExcelApiBackend(cl, "ID1"), Backuper(cl, "Yedekler", PATH, lambda: b.getvalue()), logger(tmp_path), PATH)
    assert len(svc.sheet_view("BUYUK", 1, 50)["rows"]) == 50
    assert len(svc.sheet_view("BUYUK", 1, 250)["rows"]) == 250
    whole = svc.sheet_view("BUYUK", 1, 5000)
    assert len(whole["rows"]) == 595 and whole["max_row"] == 595 and whole["max_col"] == 59
    assert len(svc.sheet_view("BUYUK", 551, 100)["rows"]) == 45        # son sayfa

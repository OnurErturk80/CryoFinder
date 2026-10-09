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

"""Graph Excel API (workbook uç noktaları). Kişisel hesaplarda desteği değişken olabilir → probe()."""
from __future__ import annotations

import urllib.parse

from .graph import GraphClient, GraphError
from .sheetutil import grid_to_cells


class ExcelApiBackend:
    name = "excel-api"
    needs_commit = False

    def __init__(self, client: GraphClient, item_id: str, persist: bool = True):
        self.c, self.persist = client, persist
        self.base = f"/me/drive/items/{item_id}/workbook"
        self.session_id: str | None = None
        self._sheets: dict[str, str] | None = None

    def _h(self) -> dict:
        return {"workbook-session-id": self.session_id} if self.session_id else {}

    def open(self) -> None:
        r = self.c.request("POST", f"{self.base}/createSession", json={"persistChanges": self.persist})
        self.session_id = r.json()["id"]

    def close(self) -> None:
        if self.session_id:
            try:
                self.c.request("POST", f"{self.base}/closeSession", headers=self._h(), json={})
            except GraphError:
                pass  # oturum zaten süresi dolmuş olabilir
            self.session_id = None

    def sheet_map(self) -> dict[str, str]:
        if self._sheets is None:
            r = self.c.request("GET", f"{self.base}/worksheets", headers=self._h(), params={"$select": "id,name"})
            self._sheets = {s["name"]: s["id"] for s in r.json()["value"]}
        return self._sheets

    def sheet_names(self) -> list[str]:
        return list(self.sheet_map())

    def _ws(self, sheet: str) -> str:
        for name, sid in self.sheet_map().items():
            if name.lower() == sheet.lower():
                return f"{self.base}/worksheets/{urllib.parse.quote(sid, safe='')}"
        raise KeyError(f"Sayfa yok: {sheet}")

    def dump(self, sheet: str) -> dict[tuple[int, int], object]:
        r = self.c.request("GET", f"{self._ws(sheet)}/usedRange(valuesOnly=true)", headers=self._h(),
                           params={"$select": "address,values"}).json()
        return grid_to_cells(r["address"], r["values"])

    def get_cell(self, sheet: str, cell: str):
        r = self.c.request("GET", f"{self._ws(sheet)}/range(address='{cell}')", headers=self._h(),
                           params={"$select": "values,formulas"}).json()
        formula = r["formulas"][0][0]
        return r["values"][0][0], isinstance(formula, str) and formula.startswith("=")

    def set_cell(self, sheet: str, cell: str, value: str) -> None:
        self.c.request("PATCH", f"{self._ws(sheet)}/range(address='{cell}')", headers=self._h(),
                       json={"values": [[value]]})


def probe(client: GraphClient, item_id: str) -> tuple[bool, list[tuple[bool, str]]]:
    """Salt-okunur / dosyayı değiştirmeyen adımlarla Excel API'nin çalışıp çalışmadığını dener."""
    steps: list[tuple[bool, str]] = []
    be = ExcelApiBackend(client, item_id, persist=False)

    def step(label, fn):
        try:
            res = fn()
            steps.append((True, label))
            return res
        except Exception as e:  # noqa: BLE001 - teşhis çıktısı
            steps.append((False, f"{label} -> {e}"))
            raise

    try:
        names = step("Çalışma sayfalarını listele", be.sheet_names)
        step(f"Kullanılan aralığı oku ({names[0]})" if names else "Sayfa yok", lambda: be.dump(names[0]))
        step("Oturum aç (persistChanges=false)", be.open)
        step("Oturumu kapat", be.close)
    except Exception:  # noqa: BLE001
        be.close()
        return False, steps
    return True, steps

from __future__ import annotations

import re

from openpyxl.utils.cell import range_boundaries

CELL_RE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]{0,6}$")


def parse_address(address: str) -> tuple[int, int]:
    """"'Sayfa 1'!B2:K80" -> (ilk satır, ilk sütun)."""
    rng = address.rsplit("!", 1)[-1]
    min_col, min_row, _, _ = range_boundaries(rng)
    return min_row, min_col


def grid_to_cells(address: str, values: list[list]) -> dict[tuple[int, int], object]:
    r0, c0 = parse_address(address)
    return {(r0 + i, c0 + j): v for i, row in enumerate(values) for j, v in enumerate(row) if v not in ("", None)}

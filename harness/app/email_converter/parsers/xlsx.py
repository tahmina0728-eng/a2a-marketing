"""Parser: .xlsx / .xls (openpyxl) and .csv"""
from __future__ import annotations
import csv as _csv_mod
import io


def parse_xlsx(content: bytes) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    blocks: list[dict] = []
    multi = len(wb.worksheets) > 1

    for sheet in wb.worksheets:
        rows_data: list[list[str]] = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c).strip() if c is not None else "" for c in row]
            cells = [c for c in cells if c]
            if cells:
                rows_data.append(cells)
        if rows_data:
            if multi:
                blocks.append({"type": "heading", "level": 2, "text": sheet.title})
            blocks.append({"type": "table", "headers": rows_data[0], "rows": rows_data[1:]})

    wb.close()
    return {"blocks": blocks, "images": []}


def parse_csv(content: bytes) -> dict:
    text   = content.decode("utf-8-sig", errors="replace")
    reader = _csv_mod.reader(io.StringIO(text))
    rows   = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        return {"blocks": [], "images": []}
    return {"blocks": [{"type": "table", "headers": rows[0], "rows": rows[1:]}], "images": []}

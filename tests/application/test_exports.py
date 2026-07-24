import csv
from pathlib import Path

from app.application.exports import EXPORT_HEADERS, ExportService


def test_exports_write_deterministic_header_only_csvs_for_empty_results(
    tmp_path: Path,
) -> None:
    service = ExportService(
        output_directory=tmp_path,
        rows_for_run=lambda _run_id: ((), ()),
    )

    result = service.generate("run-1")

    assert result.qualified_rows == 0
    assert result.rejected_rows == 0
    with result.qualified_path.open(newline="") as file:
        assert next(csv.reader(file)) == list(EXPORT_HEADERS)
    with result.rejected_path.open(newline="") as file:
        assert next(csv.reader(file)) == list(EXPORT_HEADERS)


def test_exports_sort_and_escape_rows(tmp_path: Path) -> None:
    qualified = (
        {"restaurant_name": "Zulu, Cafe", "business_id": "b-2", "run_id": "run-1"},
        {"restaurant_name": "Alpha", "business_id": "b-1", "run_id": "run-1"},
    )
    service = ExportService(
        output_directory=tmp_path,
        rows_for_run=lambda _run_id: (qualified, ()),
    )

    result = service.generate("run-1")

    with result.qualified_path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    assert [row["restaurant_name"] for row in rows] == ["Alpha", "Zulu, Cafe"]

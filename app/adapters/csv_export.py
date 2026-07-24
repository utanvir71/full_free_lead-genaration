from __future__ import annotations

import csv
import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path


def write_csv_projection(
    path: Path,
    *,
    headers: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> int:
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    count = 0
    with temporary_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})
            count += 1
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary_path, path)
    return count

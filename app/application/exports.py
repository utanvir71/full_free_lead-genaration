from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.adapters.csv_export import write_csv_projection

EXPORT_HEADERS = (
    "date_found",
    "restaurant_name",
    "city",
    "state",
    "website",
    "address",
    "phone",
    "recipient_email",
    "contact_name",
    "contact_role",
    "reservation_method",
    "pain_signal",
    "personalization_fact",
    "lead_score",
    "score_breakdown",
    "source_url",
    "evidence_urls",
    "email_confidence",
    "outreach_status",
    "date_contacted",
    "follow_up_date",
    "reply_status",
    "notes",
    "run_id",
    "business_id",
    "last_seen",
)

ExportRows = tuple[Sequence[Mapping[str, object]], Sequence[Mapping[str, object]]]


@dataclass(frozen=True, slots=True)
class ExportResult:
    qualified_path: Path
    rejected_path: Path
    qualified_rows: int
    rejected_rows: int


class ExportService:
    def __init__(
        self,
        *,
        output_directory: Path,
        rows_for_run: Callable[[str], ExportRows],
    ) -> None:
        self._output_directory = output_directory
        self._rows_for_run = rows_for_run

    def generate(self, run_id: str) -> ExportResult:
        self._output_directory.mkdir(parents=True, exist_ok=True)
        qualified, rejected = self._rows_for_run(run_id)
        qualified_path = self._output_directory / "qualified_leads.csv"
        rejected_path = self._output_directory / "rejected_leads.csv"
        qualified_rows = write_csv_projection(
            qualified_path,
            headers=EXPORT_HEADERS,
            rows=_sorted_rows(qualified),
        )
        rejected_rows = write_csv_projection(
            rejected_path,
            headers=EXPORT_HEADERS,
            rows=_sorted_rows(rejected),
        )
        return ExportResult(
            qualified_path=qualified_path,
            rejected_path=rejected_path,
            qualified_rows=qualified_rows,
            rejected_rows=rejected_rows,
        )


def _sorted_rows(rows: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("restaurant_name", "")).casefold(),
            str(row.get("business_id", "")),
        ),
    )

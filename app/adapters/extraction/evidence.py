from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from app.adapters.extraction.page_text import PageText
from app.domain.enums import ValidationState
from app.domain.models import Evidence


class EvidenceFactory:
    def __init__(
        self,
        *,
        excerpt_length: int = 500,
        extractor_version: str = "website-evidence-v1",
    ) -> None:
        if not 1 <= excerpt_length <= 1000:
            raise ValueError("excerpt_length must be between 1 and 1000")
        self._excerpt_length = excerpt_length
        self._extractor_version = extractor_version

    def from_match(
        self,
        *,
        source_url: str,
        page: PageText,
        matched_phrase: str,
        locator: str | None,
        captured_at: datetime,
    ) -> Evidence:
        position = page.text.find(matched_phrase)
        if position < 0:
            raise ValueError("matched_phrase must appear in the page text")
        excerpt = self._excerpt(page.text, position, matched_phrase)
        identity = "\n".join(
            (
                source_url,
                page.content_hash,
                matched_phrase,
                locator or "",
                self._extractor_version,
            )
        )
        return Evidence(
            evidence_id=f"website:{sha256(identity.encode()).hexdigest()}",
            source=source_url,
            excerpt=excerpt,
            locator=locator,
            captured_at=captured_at,
            extractor_version=self._extractor_version,
            validation_state=ValidationState.NOT_APPLICABLE,
        )

    def _excerpt(self, text: str, position: int, matched_phrase: str) -> str:
        if len(matched_phrase) > self._excerpt_length:
            raise ValueError("matched_phrase exceeds the configured excerpt length")
        remaining = self._excerpt_length - len(matched_phrase)
        before = min(position, remaining // 2)
        after = min(len(text) - position - len(matched_phrase), remaining - before)
        before = min(position, remaining - after)
        return text[position - before : position + len(matched_phrase) + after].strip()

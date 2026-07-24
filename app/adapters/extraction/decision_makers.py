from __future__ import annotations

import re
from collections.abc import Sequence
from hashlib import sha256

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.extraction.evidence import EvidenceFactory
from app.adapters.extraction.page_text import extract_visible_text
from app.domain.models import DecisionMaker

_ROLE = (
    r"(?:owner|founder|operator|general manager|restaurant manager|"
    r"operations manager|events manager|catering manager|marketing manager)"
)
_PERSON = re.compile(
    rf"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){{1,2}})\s*(?:,|—|-)\s*"
    rf"(({_ROLE})(?:\s+and\s+({_ROLE}))?)\b",
    re.IGNORECASE,
)


class DecisionMakerExtractor:
    def __init__(self, *, extractor_version: str = "decision-makers-v1") -> None:
        self._evidence = EvidenceFactory(extractor_version=extractor_version)
        self._extractor_version = extractor_version

    def extract(self, pages: Sequence[FetchedPage]) -> list[DecisionMaker]:
        people: dict[tuple[str, str], DecisionMaker] = {}
        for page in pages:
            text = extract_visible_text(page.html)
            for match in _PERSON.finditer(text.text):
                phrase = match.group(0)
                evidence = self._evidence.from_match(
                    source_url=page.url,
                    page=text,
                    matched_phrase=phrase,
                    locator=None,
                    captured_at=page.fetched_at,
                )
                name, role = match.group(1), match.group(2)
                identity = "\n".join(
                    (name, role, evidence.evidence_id, self._extractor_version)
                )
                people[(name, role)] = DecisionMaker(
                    person_id=f"person:{sha256(identity.encode()).hexdigest()}",
                    name=name,
                    role=role,
                    evidence_ids=(evidence.evidence_id,),
                )
        return list(people.values())

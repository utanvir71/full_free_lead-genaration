from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from hashlib import sha256
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.extraction.evidence import EvidenceFactory
from app.adapters.extraction.page_text import extract_visible_text
from app.domain.enums import FactState, ValidationState
from app.domain.models import Fact, FactValue

_CALL_TO_RESERVE = re.compile(
    r"(?:please\s+)?call(?:\s+us)?(?:\s+at\s+[^.!?]+)?\s+to\s+(?:make\s+)?(?:a\s+)?reserv(?:e|ation)",
    re.IGNORECASE,
)
_PROVIDERS = {
    "opentable": "opentable",
    "resy": "resy",
    "sevenrooms": "sevenrooms",
    "tock": "tock",
}
_RESERVATION_FACT_TYPES = (
    "reservation_method",
    "reservation_provider",
    "reservation_form",
    "call_to_reserve",
)


class ReservationExtractor:
    def __init__(self, *, extractor_version: str = "reservation-facts-v1") -> None:
        self._extractor_version = extractor_version
        self._evidence = EvidenceFactory(extractor_version=extractor_version)

    def extract(self, pages: Sequence[FetchedPage]) -> list[Fact]:
        facts: list[Fact] = []
        for page in pages:
            page_facts = self._page_facts(page)
            observed_types = {fact.fact_type for fact in page_facts}
            facts.extend(page_facts)
            facts.extend(
                self._unknown_facts(page, observed_types=observed_types)
            )
        return facts

    def _page_facts(self, page: FetchedPage) -> list[Fact]:
        text = extract_visible_text(page.html)
        facts: list[Fact] = []
        for match in _CALL_TO_RESERVE.finditer(text.text):
            phrase = match.group(0)
            facts.extend(
                (
                    self._website_fact(
                        "reservation_method", "call", page, phrase
                    ),
                    self._website_fact(
                        "call_to_reserve", phrase, page, phrase
                    ),
                )
            )

        parser = _ReservationMarkupParser()
        parser.feed(page.html)
        parser.close()
        for href in parser.links:
            provider = _provider(href)
            if provider is not None:
                facts.extend(
                    (
                        self._markup_fact("reservation_method", "online", page, href),
                        self._markup_fact("reservation_provider", provider, page, href),
                    )
                )
        for action in parser.form_actions:
            resolved = urljoin(page.url, action)
            facts.extend(
                (
                    self._markup_fact("reservation_method", "online", page, resolved),
                    self._markup_fact("reservation_form", resolved, page, resolved),
                )
            )
        return _distinct(facts)

    def _unknown_facts(
        self, page: FetchedPage, *, observed_types: set[str]
    ) -> list[Fact]:
        return [
            self._fact(
                fact_type=fact_type,
                value=None,
                source=page.url,
                excerpt=f"No {fact_type} observed on fetched official page",
                captured_at=page.fetched_at,
            )
            for fact_type in _RESERVATION_FACT_TYPES
            if fact_type not in observed_types
        ]

    def _website_fact(
        self,
        fact_type: str,
        value: FactValue,
        page: FetchedPage,
        phrase: str,
    ) -> Fact:
        evidence = self._evidence.from_match(
            source_url=page.url,
            page=extract_visible_text(page.html),
            matched_phrase=phrase,
            locator=None,
            captured_at=page.fetched_at,
        )
        return self._fact(
            fact_type=fact_type,
            value=value,
            source=page.url,
            excerpt=evidence.excerpt,
            captured_at=page.fetched_at,
        )

    def _markup_fact(
        self, fact_type: str, value: str, page: FetchedPage, marker: str
    ) -> Fact:
        return self._fact(
            fact_type=fact_type,
            value=value,
            source=page.url,
            excerpt=f"HTML reservation markup: {marker}",
            captured_at=page.fetched_at,
        )

    def _fact(
        self,
        *,
        fact_type: str,
        value: FactValue,
        source: str,
        excerpt: str,
        captured_at: datetime,
    ) -> Fact:
        state = FactState.PRESENT if value is not None else FactState.UNKNOWN
        identity = "\n".join(
            (source, fact_type, str(value), excerpt, self._extractor_version)
        )
        return Fact(
            fact_id=f"fact:{sha256(identity.encode()).hexdigest()}",
            fact_type=fact_type,
            state=state,
            value=value,
            source=source,
            excerpt=excerpt,
            captured_at=captured_at,
            extractor_version=self._extractor_version,
            validation_state=ValidationState.NOT_APPLICABLE,
        )


class _ReservationMarkupParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.form_actions: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        if tag == "form" and values.get("action"):
            self.form_actions.append(values["action"] or "")


def _provider(href: str) -> str | None:
    hostname = urlparse(href).hostname or ""
    lowered = hostname.casefold()
    for domain, provider in _PROVIDERS.items():
        provider_host = f"{domain}.com"
        if lowered == provider_host or lowered.endswith(f".{provider_host}"):
            return provider
    return None


def _distinct(facts: list[Fact]) -> list[Fact]:
    return list({fact.fact_id: fact for fact in facts}.values())

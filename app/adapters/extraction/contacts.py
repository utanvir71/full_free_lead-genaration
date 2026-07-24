from __future__ import annotations

import re
from collections.abc import Sequence
from hashlib import sha256
from html.parser import HTMLParser
from urllib.parse import urljoin

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.extraction.evidence import EvidenceFactory
from app.adapters.extraction.page_text import extract_visible_text
from app.domain.enums import ValidationState
from app.domain.models import ContactChannel, Evidence

_EMAIL = re.compile(r"(?<![\w.+-])([\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
_OBFUSCATED_EMAIL = re.compile(
    r"\b([\w.+-]+)\s*(?:\[at\]|\(at\)|at)\s*([\w.-]+)\s*(?:\[dot\]|\(dot\)|dot)\s*([A-Za-z]{2,})\b",
    re.IGNORECASE,
)
_PHONE = re.compile(r"(?<!\w)(?:\+?1[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]\d{4}(?!\w)")
_ROLE_MAILBOXES = {
    "admin",
    "catering",
    "contact",
    "events",
    "hello",
    "info",
    "marketing",
    "office",
    "reservations",
    "team",
}
_PERSONAL_DOMAINS = {"gmail.com", "icloud.com", "outlook.com", "yahoo.com"}


class ContactExtractor:
    def __init__(self, *, extractor_version: str = "contacts-v1") -> None:
        self._evidence = EvidenceFactory(extractor_version=extractor_version)
        self._extractor_version = extractor_version

    def extract(self, pages: Sequence[FetchedPage]) -> list[ContactChannel]:
        contacts: dict[tuple[str, str], ContactChannel] = {}
        for page in pages:
            text = extract_visible_text(page.html)
            for email, phrase in _emails(text.text):
                if not _is_business_email(email):
                    continue
                evidence = self._evidence.from_match(
                    source_url=page.url,
                    page=text,
                    matched_phrase=phrase,
                    locator=None,
                    captured_at=page.fetched_at,
                )
                self._add(contacts, "email", email, evidence)
            for match in _PHONE.finditer(text.text):
                evidence = self._evidence.from_match(
                    source_url=page.url,
                    page=text,
                    matched_phrase=match.group(0),
                    locator=None,
                    captured_at=page.fetched_at,
                )
                self._add(contacts, "phone", match.group(0), evidence)
            for action in _form_actions(page.html):
                value = urljoin(page.url, action)
                self._add(contacts, "form", value, self._form_evidence(page, value))
        return list(contacts.values())

    def _add(
        self,
        contacts: dict[tuple[str, str], ContactChannel],
        kind: str,
        value: str,
        evidence: Evidence,
    ) -> None:
        key = (kind, value)
        existing = contacts.get(key)
        evidence_ids = (
            (evidence.evidence_id,)
            if existing is None
            else tuple(sorted((*existing.evidence_ids, evidence.evidence_id)))
        )
        identity = "\n".join((kind, value, *evidence_ids, self._extractor_version))
        contacts[key] = ContactChannel(
            contact_id=f"contact:{sha256(identity.encode()).hexdigest()}",
            kind=kind,  # type: ignore[arg-type]
            value=value,
            evidence_ids=evidence_ids,
            validation_state=ValidationState.UNKNOWN,
        )

    def _form_evidence(self, page: FetchedPage, value: str) -> Evidence:
        identity = "\n".join((page.url, value, self._extractor_version))
        return Evidence(
            evidence_id=f"website:{sha256(identity.encode()).hexdigest()}",
            source=page.url,
            excerpt=f"Official-site contact form: {value}",
            locator="form",
            captured_at=page.fetched_at,
            extractor_version=self._extractor_version,
            validation_state=ValidationState.NOT_APPLICABLE,
        )


class _FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.actions: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "form":
            self.actions.append(dict(attrs).get("action") or "")


def _form_actions(html: str) -> list[str]:
    parser = _FormParser()
    parser.feed(html)
    parser.close()
    return parser.actions


def _emails(text: str) -> list[tuple[str, str]]:
    found = [
        (match.group(1).casefold(), match.group(1)) for match in _EMAIL.finditer(text)
    ]
    for match in _OBFUSCATED_EMAIL.finditer(text):
        email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}".casefold()
        found.append((email, match.group(0)))
    return found


def _is_business_email(email: str) -> bool:
    local, domain = email.rsplit("@", maxsplit=1)
    return (
        local.casefold() in _ROLE_MAILBOXES
        and domain.casefold() not in _PERSONAL_DOMAINS
    )

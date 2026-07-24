from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin

from app.adapters.crawler.fetcher import FetchedPage
from app.adapters.crawler.url_policy import UrlPolicy


@dataclass(frozen=True, slots=True)
class RankedLink:
    url: str
    category: str
    score: int


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._text)))
            self._href = None
            self._text = []


_SIGNALS = (
    ("private_dining", 80, ("private dining", "events", "event")),
    ("catering", 75, ("catering",)),
    ("reservations", 70, ("reservation", "reserve", "booking")),
    ("contact", 60, ("contact",)),
    ("locations", 50, ("location",)),
    ("about", 45, ("about", "team", "our story")),
    ("faq", 40, ("faq", "question")),
    ("menu", 35, ("menu",)),
)


def rank_relevant_links(homepage: FetchedPage) -> list[RankedLink]:
    parser = _LinkParser()
    parser.feed(homepage.html)
    ranked: dict[str, RankedLink] = {}
    for href, text in parser.links:
        url = urldefrag(urljoin(homepage.url, href))[0]
        if not UrlPolicy.same_official_domain(homepage.url, url):
            continue
        category = _classify(f"{href} {text}")
        if category is None or url == homepage.url:
            continue
        candidate = RankedLink(url=url, category=category[0], score=category[1])
        if url not in ranked or candidate.score > ranked[url].score:
            ranked[url] = candidate
    return sorted(ranked.values(), key=lambda link: (-link.score, link.url))


def _classify(value: str) -> tuple[str, int] | None:
    lowered = value.casefold()
    for category, score, terms in _SIGNALS:
        if any(term in lowered for term in terms):
            return category, score
    return None

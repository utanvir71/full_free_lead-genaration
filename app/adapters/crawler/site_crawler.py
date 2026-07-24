from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.adapters.crawler.errors import FetchError
from app.adapters.crawler.fetcher import FetchedPage, RequestBudget
from app.adapters.crawler.link_ranker import rank_relevant_links


class Fetcher(Protocol):
    def fetch(self, url: str, budget: RequestBudget) -> FetchedPage: ...


@dataclass(frozen=True, slots=True)
class CrawlManifest:
    considered: tuple[str, ...]
    selected: tuple[str, ...]
    skipped: tuple[str, ...]
    blocked: tuple[str, ...]
    fetched: tuple[str, ...]
    failed: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CrawlResult:
    pages: tuple[FetchedPage, ...]
    manifest: CrawlManifest
    complete: bool


class SiteCrawler:
    def __init__(
        self, fetcher: Fetcher, *, max_response_bytes: int = 2_000_000
    ) -> None:
        self._fetcher = fetcher
        self._max_response_bytes = max_response_bytes

    def crawl(self, official_url: str) -> CrawlResult:
        budget = RequestBudget(official_url, self._max_response_bytes)
        homepage = self._fetcher.fetch(official_url, budget)
        ranked = rank_relevant_links(homepage)
        selected = ranked[:5]
        pages = [homepage]
        fetched = [homepage.url]
        blocked: list[str] = []
        failed: list[str] = []
        for link in selected:
            try:
                page = self._fetcher.fetch(link.url, budget)
            except FetchError as error:
                if error.code in {"robots_denied", "unsafe_url", "off_domain"}:
                    blocked.append(link.url)
                else:
                    failed.append(link.url)
                continue
            pages.append(page)
            fetched.append(page.url)
        selected_urls = tuple(link.url for link in selected)
        return CrawlResult(
            pages=tuple(pages),
            manifest=CrawlManifest(
                considered=tuple(link.url for link in ranked),
                selected=selected_urls,
                skipped=tuple(link.url for link in ranked[5:]),
                blocked=tuple(blocked),
                fetched=tuple(fetched),
                failed=tuple(failed),
            ),
            complete=not blocked and not failed,
        )

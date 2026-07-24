from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser

_WHITESPACE = re.compile(r"\s+")
_NON_PRIMARY_TAGS = {
    "footer",
    "head",
    "nav",
    "noscript",
    "script",
    "style",
    "svg",
    "template",
}


@dataclass(frozen=True, slots=True)
class PageText:
    text: str
    content_hash: str


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._hidden_depth or self._is_hidden(tag, dict(attrs)):
            self._hidden_depth += 1

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del tag, attrs

    def handle_endtag(self, tag: str) -> None:
        del tag
        if self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self._parts.append(data)

    @staticmethod
    def _is_hidden(tag: str, attrs: dict[str, str | None]) -> bool:
        style = (attrs.get("style") or "").casefold().replace(" ", "")
        return (
            tag in _NON_PRIMARY_TAGS
            or "hidden" in attrs
            or str(attrs.get("aria-hidden") or "").casefold() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
            or str(attrs.get("role") or "").casefold() == "navigation"
        )

    @property
    def text(self) -> str:
        return " ".join(part for part in self._parts if part.strip())


def extract_visible_text(html: str) -> PageText:
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    text = _WHITESPACE.sub(" ", parser.text).strip()
    return PageText(text=text, content_hash=sha256(text.encode()).hexdigest())

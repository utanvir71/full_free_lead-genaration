from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from app.domain.normalization import normalize_domain


class UnsafeUrlError(ValueError):
    """A URL violates the public official-site crawling policy."""


@dataclass(frozen=True, slots=True)
class ValidatedUrl:
    url: str
    hostname: str


class UrlPolicy:
    def __init__(
        self, *, resolve: Callable[[str], Iterable[str]] | None = None
    ) -> None:
        self._resolve = resolve or _resolve_host

    def validate_initial(self, url: str) -> ValidatedUrl:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise UnsafeUrlError("Only absolute HTTP(S) URLs are allowed")
        if parsed.username or parsed.password:
            raise UnsafeUrlError("URLs with embedded credentials are not allowed")
        hostname = parsed.hostname.casefold()
        self._validate_public_host(hostname)
        normalized = urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, "")
        )
        return ValidatedUrl(url=normalized, hostname=hostname)

    def validate_redirect(self, source: str, target: str) -> ValidatedUrl:
        self.validate_initial(source)
        validated = self.validate_initial(target)
        if not self.same_official_domain(source, target):
            raise UnsafeUrlError("Redirect leaves the official registrable domain")
        return validated

    @staticmethod
    def same_official_domain(left: str, right: str) -> bool:
        left_domain = normalize_domain(left)
        right_domain = normalize_domain(right)
        return left_domain is not None and left_domain == right_domain

    def _validate_public_host(self, hostname: str) -> None:
        try:
            direct_address = ipaddress.ip_address(hostname)
        except ValueError:
            addresses = tuple(self._resolve(hostname))
        else:
            addresses = (str(direct_address),)
        if not addresses or any(
            not ipaddress.ip_address(address).is_global for address in addresses
        ):
            raise UnsafeUrlError("URL must resolve only to public network addresses")


def _resolve_host(hostname: str) -> tuple[str, ...]:
    addresses: set[str] = set()
    for item in socket.getaddrinfo(hostname, None):
        address = item[4][0]
        if isinstance(address, str):
            addresses.add(address)
    return tuple(addresses)

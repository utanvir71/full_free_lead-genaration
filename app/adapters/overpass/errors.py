class OverpassError(Exception):
    """Base error for bounded Overpass discovery failures."""


class OverpassPayloadError(OverpassError):
    """The response did not contain valid discovery elements."""


class OverpassResponseError(OverpassError):
    """Overpass returned an invalid JSON or error response payload."""


class OverpassRetryExhausted(OverpassError):
    """A retryable Overpass response exceeded the bounded retry limit."""

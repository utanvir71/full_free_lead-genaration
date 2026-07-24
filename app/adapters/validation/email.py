from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.domain.enums import ValidationState
from app.domain.models import ContactChannel

_EMAIL = re.compile(r"^[^@\s]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)$")


class DnsResolver(Protocol):
    def resolve(self, domain: str, record_type: str) -> object: ...


@dataclass(frozen=True, slots=True)
class EmailValidationResult:
    syntax: ValidationState
    domain: ValidationState
    mx: ValidationState
    domain_reason: str | None
    mx_reason: str | None


class EmailValidator:
    def __init__(self, resolver: DnsResolver) -> None:
        self._resolver = resolver

    def validate(self, contact: ContactChannel) -> EmailValidationResult:
        match = _EMAIL.fullmatch(contact.value) if contact.kind == "email" else None
        if match is None:
            return EmailValidationResult(
                syntax=ValidationState.INVALID,
                domain=ValidationState.NOT_APPLICABLE,
                mx=ValidationState.NOT_APPLICABLE,
                domain_reason=None,
                mx_reason=None,
            )
        domain = match.group(1).casefold()
        domain_state, domain_reason = self._lookup(domain, "A")
        if domain_state is not ValidationState.VALID:
            return EmailValidationResult(
                syntax=ValidationState.VALID,
                domain=domain_state,
                mx=ValidationState.UNKNOWN,
                domain_reason=domain_reason,
                mx_reason="not_checked",
            )
        mx_state, mx_reason = self._lookup(domain, "MX")
        return EmailValidationResult(
            syntax=ValidationState.VALID,
            domain=domain_state,
            mx=mx_state,
            domain_reason=domain_reason,
            mx_reason=mx_reason,
        )

    def _lookup(self, domain: str, record_type: str) -> tuple[ValidationState, str]:
        for attempt in range(2):
            try:
                answer = self._resolver.resolve(domain, record_type)
            except TimeoutError:
                if attempt == 1:
                    return ValidationState.UNKNOWN, "timeout"
                continue
            except LookupError:
                return ValidationState.INVALID, "nxdomain"
            values = list(answer) if isinstance(answer, (list, tuple, set)) else []
            if record_type == "MX":
                if not values:
                    return ValidationState.INVALID, "missing_mx"
                if all(str(value).strip() == "." for value in values):
                    return ValidationState.INVALID, "null_mx"
            elif not values:
                return ValidationState.INVALID, "nxdomain"
            return ValidationState.VALID, "valid"
        return ValidationState.UNKNOWN, "timeout"

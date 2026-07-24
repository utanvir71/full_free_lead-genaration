from __future__ import annotations

from dataclasses import dataclass

from app.adapters.validation.email import EmailValidator
from app.domain.enums import ValidationState
from app.domain.models import ContactChannel


@dataclass
class FakeResolver:
    answers: dict[tuple[str, str], object]
    calls: list[tuple[str, str]]

    def resolve(self, domain: str, record_type: str) -> object:
        self.calls.append((domain, record_type))
        answer = self.answers[(domain, record_type)]
        if isinstance(answer, Exception):
            raise answer
        return answer


def _contact(value: str) -> ContactChannel:
    return ContactChannel(
        contact_id="contact:1",
        kind="email",
        value=value,
        evidence_ids=("website:1",),
        validation_state=ValidationState.UNKNOWN,
    )


def test_email_validator_reports_independent_valid_syntax_domain_and_mx() -> None:
    resolver = FakeResolver(
        {
            ("rosa.example", "A"): ["203.0.113.2"],
            ("rosa.example", "MX"): ["mx.rosa.example."],
        },
        [],
    )

    result = EmailValidator(resolver).validate(_contact("info@rosa.example"))

    assert result.syntax is ValidationState.VALID
    assert result.domain is ValidationState.VALID
    assert result.mx is ValidationState.VALID
    assert resolver.calls == [("rosa.example", "A"), ("rosa.example", "MX")]


def test_email_validator_distinguishes_missing_null_nxdomain_and_timeout_mx() -> None:
    cases = {
        "missing": ([], "missing_mx", ValidationState.INVALID),
        "null": (["."], "null_mx", ValidationState.INVALID),
        "nxdomain": (LookupError("NXDOMAIN"), "nxdomain", ValidationState.INVALID),
        "timeout": (TimeoutError(), "timeout", ValidationState.UNKNOWN),
    }
    for name, (mx_answer, reason, state) in cases.items():
        resolver = FakeResolver(
            {("rosa.example", "A"): ["203.0.113.2"], ("rosa.example", "MX"): mx_answer},
            [],
        )

        result = EmailValidator(resolver).validate(_contact("info@rosa.example"))

        assert result.mx is state, name
        assert result.mx_reason == reason, name
        if name == "timeout":
            assert resolver.calls.count(("rosa.example", "MX")) == 2


def test_email_validator_keeps_dns_unknown_after_two_timeouts() -> None:
    resolver = FakeResolver(
        {
            ("rosa.example", "A"): TimeoutError(),
            ("rosa.example", "MX"): ["mx.rosa.example."],
        },
        [],
    )

    result = EmailValidator(resolver).validate(_contact("info@rosa.example"))

    assert result.domain is ValidationState.UNKNOWN
    assert result.mx is ValidationState.UNKNOWN
    assert resolver.calls.count(("rosa.example", "A")) == 2

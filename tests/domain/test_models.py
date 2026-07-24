from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.enums import (
    DraftMethod,
    FactState,
    SignalState,
    ValidationState,
)
from app.domain.models import (
    Assessment,
    ContactChannel,
    DecisionMaker,
    Draft,
    Evidence,
    Fact,
    ScoreComponent,
    StageError,
)

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)


def test_fact_preserves_bounded_evidence_metadata() -> None:
    fact = Fact(
        fact_id="fact-1",
        fact_type="reservation_method",
        state=FactState.PRESENT,
        value="Call the restaurant",
        source="https://example.com/reservations",
        excerpt="For reservations, call us.",
        captured_at=NOW,
        extractor_version="reservations-v1",
        validation_state=ValidationState.VALID,
    )

    assert fact.source == "https://example.com/reservations"
    assert fact.excerpt == "For reservations, call us."
    assert fact.captured_at == NOW
    assert fact.extractor_version == "reservations-v1"
    assert fact.validation_state is ValidationState.VALID

    with pytest.raises(ValidationError):
        Fact(
            fact_id="fact-2",
            fact_type="oversized",
            state=FactState.PRESENT,
            value="value",
            source="https://example.com",
            excerpt="x" * 1001,
            captured_at=NOW,
            extractor_version="test-v1",
            validation_state=ValidationState.UNKNOWN,
        )


def test_fact_states_keep_unknown_absent_false_and_true_distinct() -> None:
    states = {
        FactState.UNKNOWN,
        FactState.ABSENT,
        FactState.FALSE,
        FactState.TRUE,
    }

    assert len(states) == 4
    assert len({state.value for state in states}) == 4


def test_decision_maker_rejects_personal_contact_fields() -> None:
    with pytest.raises(ValidationError):
        DecisionMaker.model_validate(
            {
                "person_id": "person-1",
                "name": "Alex Rivera",
                "role": "General Manager",
                "evidence_ids": ["evidence-1"],
                "email": "alex@example.com",
            }
        )


def test_draft_records_method_evidence_validation_and_version() -> None:
    draft = Draft(
        draft_id="draft-1",
        run_id="run-1",
        business_id="business-1",
        subject="Quick question",
        body="Would it be useful if I shared a short example?",
        method=DraftMethod.FALLBACK,
        evidence_ids=("evidence-1",),
        validation_state=ValidationState.VALID,
        version="draft-v1",
        created_at=NOW,
    )

    assert draft.method is DraftMethod.FALLBACK
    assert draft.evidence_ids == ("evidence-1",)
    assert draft.validation_state is ValidationState.VALID
    assert draft.version == "draft-v1"


def test_domain_models_round_trip_identifiers_and_enums() -> None:
    evidence = Evidence(
        evidence_id="evidence-1",
        source="osm:node:123",
        excerpt="amenity=restaurant",
        locator="tags.amenity",
        captured_at=NOW,
        extractor_version="osm-v1",
        validation_state=ValidationState.VALID,
    )
    contact = ContactChannel(
        contact_id="contact-1",
        kind="email",
        value="hello@example.com",
        evidence_ids=(evidence.evidence_id,),
        validation_state=ValidationState.VALID,
    )
    person = DecisionMaker(
        person_id="person-1",
        name="Alex Rivera",
        role="General Manager",
        evidence_ids=(evidence.evidence_id,),
    )
    component = ScoreComponent(
        signal="calling_required",
        state=SignalState.AWARDED,
        delta=3,
        explanation="Official reservations page requires a call.",
        evidence_ids=(evidence.evidence_id,),
    )
    assessment = Assessment(
        assessment_id="assessment-1",
        run_id="run-1",
        business_id="business-1",
        scoring_version="scoring-v1",
        components=(component,),
        total=3,
        qualified=False,
    )
    error = StageError(
        error_id="error-1",
        stage="crawl",
        code="robots_denied",
        message="The page is disallowed by robots.txt.",
        retryable=False,
        occurred_at=NOW,
    )

    round_trips = [
        (Evidence, evidence),
        (ContactChannel, contact),
        (DecisionMaker, person),
        (ScoreComponent, component),
        (Assessment, assessment),
        (StageError, error),
    ]
    for model_type, value in round_trips:
        assert model_type.model_validate_json(value.model_dump_json()) == value


def test_models_are_immutable() -> None:
    evidence = Evidence(
        evidence_id="evidence-1",
        source="osm:node:123",
        excerpt="amenity=restaurant",
        captured_at=NOW,
        extractor_version="osm-v1",
        validation_state=ValidationState.VALID,
    )

    with pytest.raises(ValidationError):
        evidence.source = "changed"  # type: ignore[misc]

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import DraftMethod, FactState, SignalState, ValidationState

Identifier = Annotated[str, Field(min_length=1, max_length=255)]
ShortText = Annotated[str, Field(min_length=1, max_length=500)]
EvidenceText = Annotated[str, Field(min_length=1, max_length=1000)]
SourceReference = Annotated[str, Field(min_length=1, max_length=2048)]
FactValue = str | int | float | bool | None


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Evidence(DomainModel):
    evidence_id: Identifier
    source: SourceReference
    excerpt: EvidenceText
    locator: ShortText | None = None
    captured_at: datetime
    extractor_version: Identifier
    validation_state: ValidationState


class Fact(DomainModel):
    fact_id: Identifier
    fact_type: Identifier
    state: FactState
    value: FactValue
    source: SourceReference
    excerpt: EvidenceText
    captured_at: datetime
    extractor_version: Identifier
    validation_state: ValidationState


class ContactChannel(DomainModel):
    contact_id: Identifier
    kind: Literal["email", "phone", "form"]
    value: SourceReference
    evidence_ids: tuple[Identifier, ...]
    validation_state: ValidationState


class DecisionMaker(DomainModel):
    person_id: Identifier
    name: ShortText
    role: ShortText
    evidence_ids: tuple[Identifier, ...]


class ScoreComponent(DomainModel):
    signal: Identifier
    state: SignalState
    delta: int
    explanation: EvidenceText
    evidence_ids: tuple[Identifier, ...]


class Assessment(DomainModel):
    assessment_id: Identifier
    run_id: Identifier
    business_id: Identifier
    scoring_version: Identifier
    components: tuple[ScoreComponent, ...]
    total: int
    qualified: bool


class Draft(DomainModel):
    draft_id: Identifier
    run_id: Identifier
    business_id: Identifier
    subject: ShortText
    body: EvidenceText
    method: DraftMethod
    evidence_ids: tuple[Identifier, ...]
    validation_state: ValidationState
    version: Identifier
    created_at: datetime


class StageError(DomainModel):
    error_id: Identifier
    stage: Identifier
    code: Identifier
    message: EvidenceText
    retryable: bool
    occurred_at: datetime

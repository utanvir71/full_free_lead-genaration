from datetime import UTC, datetime

from app.application.ports import RestaurantCheckpoint
from app.domain.enums import FactState, SignalState, ValidationState
from app.domain.models import Assessment, Fact, ScoreComponent, StageError
from app.worker.restaurant_pipeline import (
    PipelineStageFailure,
    RestaurantPipeline,
    RestaurantResearch,
)

NOW = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


class RecordingRepository:
    def __init__(self) -> None:
        self.checkpoints: list[RestaurantCheckpoint] = []

    def checkpoint(self, checkpoint: RestaurantCheckpoint) -> None:
        self.checkpoints.append(checkpoint)


class RecordingErrors:
    def __init__(self) -> None:
        self.errors: list[StageError] = []

    def add(self, error: StageError, *, run_id: str, business_id: str) -> None:
        assert run_id == "run-1"
        assert business_id == "business-1"
        self.errors.append(error)


def test_pipeline_checkpoints_injected_research_once() -> None:
    fact = Fact(
        fact_id="fact-1",
        fact_type="reservation_method",
        state=FactState.PRESENT,
        value="call",
        source="https://example.test",
        excerpt="Call to reserve.",
        captured_at=NOW,
        extractor_version="fixture-v1",
        validation_state=ValidationState.NOT_APPLICABLE,
    )
    assessment = Assessment(
        assessment_id="assessment-1",
        run_id="run-1",
        business_id="business-1",
        scoring_version="scoring-v1",
        components=(
            ScoreComponent(
                signal="call_required",
                state=SignalState.AWARDED,
                delta=3,
                explanation="Call required.",
                evidence_ids=("fact-1",),
            ),
        ),
        total=3,
        qualified=False,
    )
    repository = RecordingRepository()
    pipeline = RestaurantPipeline(
        repository=repository,
        research=lambda run_id, business_id: RestaurantResearch(
            canonical_name="Example Restaurant",
            snapshot_id="snapshot-1",
            snapshot_name="Example Restaurant",
            captured_at=NOW,
            facts=(fact,),
            assessment=assessment,
        ),
    )

    result = pipeline.process("run-1", "business-1")

    assert result.checkpointed is True
    assert repository.checkpoints[0].assessment == assessment
    assert repository.checkpoints[0].facts == (fact,)

    duplicate = pipeline.process("run-1", "business-1")

    assert duplicate.checkpointed is False
    assert repository.checkpoints == [repository.checkpoints[0]]


def test_pipeline_records_a_typed_stage_failure_without_checkpointing() -> None:
    repository = RecordingRepository()
    errors = RecordingErrors()
    failure = StageError(
        error_id="error-1",
        stage="crawl",
        code="robots_denied",
        message="The official site disallows crawling.",
        retryable=False,
        occurred_at=NOW,
    )
    pipeline = RestaurantPipeline(
        repository=repository,
        errors=errors,
        research=lambda _run_id, _business_id: (_ for _ in ()).throw(
            PipelineStageFailure(failure)
        ),
    )

    result = pipeline.process("run-1", "business-1")

    assert result.checkpointed is False
    assert result.error == failure
    assert repository.checkpoints == []
    assert errors.errors == [failure]

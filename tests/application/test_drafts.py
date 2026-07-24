from app.application.draft_guard import DraftValidation
from app.application.drafts import DraftService
from app.application.fact_packets import FactPacket


class RejectingGenerator:
    def generate(self, _packet: FactPacket) -> DraftValidation:
        return DraftValidation(False, "malformed_output")


class RecordingDrafts:
    def __init__(self) -> None:
        self.drafts: list[object] = []

    def add(self, draft: object) -> None:
        self.drafts.append(draft)


def test_draft_service_uses_fallback_and_caps_a_run_at_ten() -> None:
    packets = tuple(
        FactPacket(f"business-{index}", "assessment", (), ()) for index in range(12)
    )
    repository = RecordingDrafts()
    service = DraftService(
        packets_for_run=lambda _run_id: packets,
        generator=RejectingGenerator(),
        repository=repository,
    )

    generated = service.generate_for_run("run-1")

    assert generated == 10
    assert len(repository.drafts) == 10

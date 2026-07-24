from app.application.draft_generator import DraftGenerator
from app.application.fact_packets import FactPacket


class RepairingClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, _packet: object, _schema: object) -> object:
        self.calls += 1
        if self.calls == 1:
            return type("Result", (), {"content": "not json"})()
        return type(
            "Result",
            (),
            {"content": '{"subject":"Hello","body":"Hi","evidence_ids":["fact-1"]}'},
        )()


def test_draft_generator_retries_one_malformed_response() -> None:
    client = RepairingClient()
    packet = FactPacket("business-1", "assessment-1", (), ("fact-1",))

    result = DraftGenerator(client=client).generate(packet)

    assert result.approved is True
    assert client.calls == 2

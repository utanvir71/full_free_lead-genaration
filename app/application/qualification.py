from app.domain.models import Assessment
from app.domain.scoring import score_v1
from app.domain.signal_policy import SignalInputs


class QualificationService:
    def assess(self, run_id: str, business_id: str, inputs: SignalInputs) -> Assessment:
        return score_v1(inputs, run_id=run_id, business_id=business_id)

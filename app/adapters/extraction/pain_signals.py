from __future__ import annotations

from collections.abc import Mapping
from statistics import median

from app.domain.enums import SignalState
from app.domain.signal_policy import SignalInput, SignalInputs


class PainSignalExtractor:
    def extract(self, research: Mapping[str, object]) -> SignalInputs:
        complete = bool(research.get("complete_crawl"))
        evidence = research.get("evidence_ids")
        evidence_map = evidence if isinstance(evidence, Mapping) else {}
        prices = _prices(research.get("entree_prices"))
        price_median = median(prices) if len(prices) >= 5 else None
        return SignalInputs(
            call_required=self._present(
                research, "call_to_reserve", evidence_map, evidence_key="call_required"
            ),
            no_online_booking=self._absence(
                research, "online_booking", complete, evidence_map
            ),
            private_events=self._present(research, "private_events", evidence_map),
            catering=self._present(research, "catering", evidence_map),
            multiple_locations=self._threshold(
                research, "location_count", 2, evidence_map
            ),
            phone_prominent=self._present(research, "phone_prominent", evidence_map),
            complex_hours=self._present(research, "complex_hours", evidence_map),
            large_faq_or_menu=self._boolean(
                _integer(research.get("faq_pairs")) >= 10
                or _integer(research.get("menu_items")) >= 40,
                "large_faq_or_menu",
                evidence_map,
            ),
            high_ticket=self._boolean(
                price_median is not None and price_median >= 30,
                "high_ticket",
                evidence_map,
            ),
            no_contact_route=self._absence(
                research, "contact_route", complete, evidence_map
            ),
            permanently_closed=self._present(research, "closed", evidence_map),
            low_ticket=self._boolean(
                bool(research.get("quick_service"))
                or (price_median is not None and price_median < 15),
                "low_ticket",
                evidence_map,
            ),
        )

    def _present(
        self,
        research: Mapping[str, object],
        key: str,
        evidence: Mapping[object, object],
        *,
        evidence_key: str | None = None,
    ) -> SignalInput:
        value = research.get(key)
        return self._boolean(
            bool(value) if value is not None else None, evidence_key or key, evidence
        )

    def _absence(
        self,
        research: Mapping[str, object],
        key: str,
        complete: bool,
        evidence: Mapping[object, object],
    ) -> SignalInput:
        if not complete or key not in research:
            return SignalInput(SignalState.UNKNOWN)
        return self._boolean(not bool(research[key]), f"no_{key}", evidence)

    def _threshold(
        self,
        research: Mapping[str, object],
        key: str,
        minimum: int,
        evidence: Mapping[object, object],
    ) -> SignalInput:
        value = research.get(key)
        return self._boolean(
            int(value) >= minimum if isinstance(value, int) else None, key, evidence
        )

    def _boolean(
        self, value: bool | None, key: str, evidence: Mapping[object, object]
    ) -> SignalInput:
        state = (
            SignalState.UNKNOWN
            if value is None
            else (SignalState.AWARDED if value else SignalState.DENIED)
        )
        raw = evidence.get(key, ())
        ids = (
            tuple(item for item in raw if isinstance(item, str))
            if isinstance(raw, (tuple, list))
            else ()
        )
        return SignalInput(state, ids)


def _prices(value: object) -> list[float]:
    if not isinstance(value, (tuple, list)):
        return []
    return [float(price) for price in value if isinstance(price, (int, float))]


def _integer(value: object) -> int:
    return value if isinstance(value, int) else 0

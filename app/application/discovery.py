from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import Connection, Engine, insert, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.adapters.overpass.parser import Candidate
from app.db import schema
from app.domain.enums import LeadStatus
from app.domain.normalization import (
    normalize_address,
    normalize_domain,
    normalize_osm_identity,
    normalize_phone,
)


@dataclass(frozen=True, slots=True)
class ReconciledCandidate:
    business_id: str
    needs_review: bool


class DiscoveryService:
    def __init__(self, engine: Engine, *, clock: Callable[[], datetime]) -> None:
        self._engine = engine
        self._clock = clock

    def reconcile(
        self, run_id: str, candidates: Iterable[Candidate]
    ) -> list[ReconciledCandidate]:
        reconciled: list[ReconciledCandidate] = []
        with self._engine.begin() as connection:
            for candidate in candidates:
                reconciled.append(self._reconcile_one(connection, run_id, candidate))
        return reconciled

    def _reconcile_one(
        self, connection: Connection, run_id: str, candidate: Candidate
    ) -> ReconciledCandidate:
        now = self._clock()
        osm_identity = normalize_osm_identity(candidate.osm_type, candidate.osm_id)
        existing_osm = self._matching_business_ids(connection, "osm", osm_identity)
        aliases = self._secondary_aliases(candidate)
        if existing_osm:
            business_id = next(iter(existing_osm))
            needs_review = False
        else:
            secondary_matches: set[str] = set()
            for alias_type, value in aliases.items():
                secondary_matches.update(
                    self._matching_business_ids(connection, alias_type, value)
                )
            needs_review = len(secondary_matches) > 1
            business_id = (
                next(iter(secondary_matches))
                if len(secondary_matches) == 1
                else str(uuid5(NAMESPACE_URL, f"{run_id}:{osm_identity}"))
            )

        name = candidate.tags.get("name", candidate.source_identity)
        website = candidate.tags.get("website") or candidate.tags.get("contact:website")
        phone = candidate.tags.get("phone") or candidate.tags.get("contact:phone")
        address = _candidate_address(candidate)
        self._upsert_business(
            connection,
            business_id=business_id,
            name=name,
            website=website,
            phone=phone,
            address=address,
            needs_review=needs_review,
            now=now,
        )
        if not needs_review:
            self._add_alias(connection, business_id, "osm", osm_identity, now)
            for alias_type, value in aliases.items():
                self._add_alias(connection, business_id, alias_type, value, now)
        snapshot_id = str(uuid5(NAMESPACE_URL, f"{run_id}:{osm_identity}"))
        connection.execute(
            insert(schema.run_candidates).values(
                id=snapshot_id,
                run_id=run_id,
                business_id=business_id,
                osm_type=candidate.osm_type,
                osm_id=str(candidate.osm_id),
                name_snapshot=name,
                website_snapshot=website,
                phone_snapshot=phone,
                address_snapshot=address,
                created_at=now,
            )
        )
        connection.execute(
            insert(schema.source_records).values(
                id=str(uuid5(NAMESPACE_URL, f"{snapshot_id}:osm")),
                run_candidate_id=snapshot_id,
                source_type="overpass",
                source_identifier=candidate.source_identity,
                payload_json=json.dumps(dict(candidate.tags), sort_keys=True),
                captured_at=now,
            )
        )
        return ReconciledCandidate(business_id=business_id, needs_review=needs_review)

    @staticmethod
    def _matching_business_ids(
        connection: Connection, alias_type: str, value: str
    ) -> set[str]:
        return set(
            connection.execute(
                select(schema.business_aliases.c.business_id)
                .where(schema.business_aliases.c.alias_type == alias_type)
                .where(schema.business_aliases.c.normalized_value == value)
            ).scalars()
        )

    @staticmethod
    def _secondary_aliases(candidate: Candidate) -> dict[str, str]:
        website = candidate.tags.get("website") or candidate.tags.get("contact:website")
        phone = candidate.tags.get("phone") or candidate.tags.get("contact:phone")
        address = _candidate_address(candidate)
        values = {
            "domain": normalize_domain(website) if website else None,
            "phone": normalize_phone(phone) if phone else None,
            "address": normalize_address(address) if address else None,
        }
        return {alias_type: value for alias_type, value in values.items() if value}

    @staticmethod
    def _upsert_business(
        connection: Connection,
        *,
        business_id: str,
        name: str,
        website: str | None,
        phone: str | None,
        address: str | None,
        needs_review: bool,
        now: datetime,
    ) -> None:
        statement = sqlite_insert(schema.businesses).values(
            id=business_id,
            name=name,
            lead_status=(
                LeadStatus.NEEDS_REVIEW if needs_review else LeadStatus.NEW
            ).value,
            website=website,
            phone=phone,
            address=address,
            created_at=now,
            updated_at=now,
        )
        connection.execute(
            statement.on_conflict_do_update(
                index_elements=[schema.businesses.c.id],
                set_={
                    "name": name,
                    "website": website,
                    "phone": phone,
                    "address": address,
                    "updated_at": now,
                },
            )
        )

    @staticmethod
    def _add_alias(
        connection: Connection,
        business_id: str,
        alias_type: str,
        value: str,
        now: datetime,
    ) -> None:
        existing = DiscoveryService._matching_business_ids(
            connection, alias_type, value
        )
        if not existing:
            connection.execute(
                insert(schema.business_aliases).values(
                    id=str(uuid5(NAMESPACE_URL, f"{alias_type}:{value}")),
                    business_id=business_id,
                    alias_type=alias_type,
                    normalized_value=value,
                    created_at=now,
                )
            )


def _candidate_address(candidate: Candidate) -> str | None:
    fields = (
        "addr:housenumber",
        "addr:street",
        "addr:city",
        "addr:state",
        "addr:postcode",
    )
    value = " ".join(
        candidate.tags[field] for field in fields if candidate.tags.get(field)
    )
    return value or candidate.tags.get("addr:full")

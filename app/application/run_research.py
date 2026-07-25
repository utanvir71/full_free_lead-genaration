"""Run the local, evidence-backed research steps after OSM discovery."""
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, cast
from uuid import NAMESPACE_URL, uuid5

import httpx
from sqlalchemy import Engine, insert, select

from app.adapters.crawler.fetcher import FetchedPage, PageFetcher
from app.adapters.crawler.robots import RobotsPolicy
from app.adapters.crawler.site_crawler import CrawlResult, SiteCrawler
from app.adapters.crawler.url_policy import UrlPolicy
from app.adapters.extraction.business import BusinessExtractor
from app.adapters.extraction.contacts import ContactExtractor
from app.adapters.extraction.decision_makers import DecisionMakerExtractor
from app.adapters.extraction.page_text import extract_visible_text
from app.adapters.extraction.pain_signals import PainSignalExtractor
from app.adapters.extraction.reservations import ReservationExtractor
from app.adapters.ollama.client import OllamaClient, OllamaReadiness
from app.application.draft_generator import DraftGenerator, GeneratedResult
from app.application.exports import ExportService
from app.application.fact_packets import FactPacket
from app.application.fallback_draft import build_fallback_draft
from app.config import Settings
from app.db import schema
from app.domain.enums import DraftMethod, FactState, ValidationState
from app.domain.models import ContactChannel, DecisionMaker, Fact
from app.domain.scoring import score_v1
from app.domain.signal_policy import SignalInputs


class Crawler(Protocol):
    def crawl(self, official_url: str) -> CrawlResult: ...


@dataclass
class LocalGeneratedResult:
    content: str | None


class OllamaDraftModel:
    """Adapt a FactPacket to Ollama's JSON-only local API."""

    def __init__(self, client: OllamaClient) -> None:
        self._client = client

    def generate(self, packet: object, schema: object) -> GeneratedResult:
        if not isinstance(packet, FactPacket) or not isinstance(schema, Mapping):
            return LocalGeneratedResult(content=None)
        result = self._client.generate(
            {
                "business_id": packet.business_id,
                "facts": [
                    {
                        "fact_id": fact.fact_id,
                        "fact_type": fact.fact_type,
                        "value": fact.value,
                        "source": fact.source,
                        "excerpt": fact.excerpt,
                    }
                    for fact in packet.facts
                ],
                "evidence_ids": list(packet.evidence_ids),
            },
            schema,
        )
        return LocalGeneratedResult(content=result.content)


class RunResearchProcessor:
    """Persist official-site research, assessments, local drafts and CSVs."""

    def __init__(
        self,
        engine: Engine,
        *,
        settings: Settings,
        clock: Callable[[], datetime],
        crawler: Crawler | None = None,
        draft_model_factory: Callable[[Settings], OllamaDraftModel | None]
        | None = None,
    ) -> None:
        self._engine = engine
        self._settings = settings
        self._clock = clock
        self._crawler = crawler or _build_crawler(settings)
        self._draft_model_factory = draft_model_factory or _draft_model

    def process(self, run_id: str) -> None:
        for candidate in self._candidates(run_id):
            self._research_candidate(run_id, candidate)
        self._write_drafts(run_id)
        self._write_exports(run_id)

    def _candidates(self, run_id: str) -> list[Mapping[str, object]]:
        with self._engine.connect() as connection:
            return cast(
                list[Mapping[str, object]],
                list(
                    connection.execute(
                        select(schema.businesses, schema.run_candidates)
                        .join(
                            schema.run_candidates,
                            schema.run_candidates.c.business_id
                            == schema.businesses.c.id,
                        )
                        .where(schema.run_candidates.c.run_id == run_id)
                    ).mappings()
                ),
            )

    def _research_candidate(self, run_id: str, candidate: Mapping[str, object]) -> None:
        business_id = str(candidate["business_id"])
        website = candidate.get("website")
        if not isinstance(website, str) or not website.strip():
            self._record_error(
                run_id,
                business_id,
                "crawl",
                "no_official_website",
                "No official website was supplied by OpenStreetMap.",
            )
            self._save_assessment(
                run_id, business_id, PainSignalExtractor().extract({})
            )
            return
        try:
            result = self._crawler.crawl(website)
        except Exception as error:
            self._record_error(
                run_id,
                business_id,
                "crawl",
                "official_site_unavailable",
                _safe_error(error),
            )
            self._save_assessment(
                run_id, business_id, PainSignalExtractor().extract({})
            )
            return
        self._save_pages(run_id, business_id, result)
        facts = self._extract_facts(candidate, result.pages)
        self._save_facts(run_id, business_id, facts)
        contacts = ContactExtractor().extract(result.pages)
        self._save_contacts(run_id, business_id, contacts)
        self._save_people(
            run_id, business_id, DecisionMakerExtractor().extract(result.pages)
        )
        inputs = PainSignalExtractor().extract(
            _signal_research(result, facts, contacts)
        )
        self._save_assessment(run_id, business_id, inputs)

    def _extract_facts(
        self, candidate: Mapping[str, object], pages: tuple[FetchedPage, ...]
    ) -> list[Fact]:
        # Website facts are usable evidence; OSM facts remain discovery-only metadata.
        from app.adapters.overpass.parser import Candidate

        osm_type = str(candidate.get("osm_type") or "node")
        typed_osm_type = cast(Literal["node", "way", "relation"], osm_type)
        osm_id = candidate.get("osm_id")
        osm = Candidate(
            osm_type=typed_osm_type,
            osm_id=int(str(osm_id or "0")),
            latitude=0.0,
            longitude=0.0,
            tags={
                "name": str(candidate["name"]),
                "website": str(candidate.get("website") or ""),
            },
        )
        extracted = BusinessExtractor().extract(osm, pages, captured_at=self._clock())
        extracted.extend(ReservationExtractor().extract(pages))
        extracted.extend(_service_facts(pages))
        return [
            fact.model_copy(update={"validation_state": ValidationState.VALID})
            if fact.source.startswith("http") and fact.state is FactState.PRESENT
            else fact
            for fact in extracted
        ]

    def _save_pages(self, run_id: str, business_id: str, result: CrawlResult) -> None:
        with self._engine.begin() as connection:
            for page in result.pages:
                connection.execute(
                    insert(schema.crawl_pages)
                    .prefix_with("OR IGNORE")
                    .values(
                        id=_id("page", run_id, business_id, page.url),
                        run_id=run_id,
                        business_id=business_id,
                        url=page.url,
                        robots_decision="allowed",
                        status="fetched",
                        http_status=page.http_status,
                        content_hash=hashlib.sha256(page.html.encode()).hexdigest(),
                        error_code=None,
                        fetched_at=page.fetched_at,
                    )
                )

    def _save_facts(self, run_id: str, business_id: str, facts: list[Fact]) -> None:
        with self._engine.begin() as connection:
            for fact in facts:
                connection.execute(
                    insert(schema.facts)
                    .prefix_with("OR IGNORE")
                    .values(
                        id=_id("fact", run_id, business_id, fact.fact_id),
                        run_id=run_id,
                        business_id=business_id,
                        fact_type=fact.fact_type,
                        state=fact.state.value,
                        value_json=json.dumps(fact.value),
                        source=fact.source,
                        excerpt=fact.excerpt,
                        captured_at=fact.captured_at,
                        extractor_version=fact.extractor_version,
                        validation_state=fact.validation_state.value,
                        idempotency_key=f"{run_id}:{business_id}:{fact.fact_id}",
                    )
                )

    def _save_contacts(
        self, run_id: str, business_id: str, contacts: Sequence[ContactChannel]
    ) -> None:
        with self._engine.begin() as connection:
            for contact in contacts:
                syntax = "valid" if contact.kind == "email" else "not_applicable"
                connection.execute(
                    insert(schema.contacts)
                    .prefix_with("OR IGNORE")
                    .values(
                        id=_id("contact", run_id, business_id, contact.contact_id),
                        run_id=run_id,
                        business_id=business_id,
                        kind=contact.kind,
                        value=contact.value,
                        evidence_ids_json=json.dumps(contact.evidence_ids),
                        classification="official_site_public",
                        syntax_state=syntax,
                        dns_state="unknown",
                        mx_state="unknown",
                        idempotency_key=f"{run_id}:{business_id}:{contact.contact_id}",
                    )
                )

    def _save_people(
        self, run_id: str, business_id: str, people: Sequence[DecisionMaker]
    ) -> None:
        with self._engine.begin() as connection:
            for person in people:
                connection.execute(
                    insert(schema.people)
                    .prefix_with("OR IGNORE")
                    .values(
                        id=_id("person", run_id, business_id, person.person_id),
                        run_id=run_id,
                        business_id=business_id,
                        name=person.name,
                        role=person.role,
                        evidence_ids_json=json.dumps(person.evidence_ids),
                        idempotency_key=f"{run_id}:{business_id}:{person.person_id}",
                    )
                )

    def _save_assessment(
        self, run_id: str, business_id: str, inputs: SignalInputs
    ) -> None:
        assessment = score_v1(inputs, run_id=run_id, business_id=business_id)
        now = self._clock()
        with self._engine.begin() as connection:
            connection.execute(
                insert(schema.assessments)
                .prefix_with("OR IGNORE")
                .values(
                    id=assessment.assessment_id,
                    run_id=run_id,
                    business_id=business_id,
                    total=assessment.total,
                    qualified=assessment.qualified,
                    scoring_version=assessment.scoring_version,
                    created_at=now,
                )
            )
            for component in assessment.components:
                connection.execute(
                    insert(schema.score_signals)
                    .prefix_with("OR IGNORE")
                    .values(
                        id=_id("signal", assessment.assessment_id, component.signal),
                        assessment_id=assessment.assessment_id,
                        signal=component.signal,
                        state=component.state.value,
                        delta=component.delta,
                        explanation=component.explanation,
                        evidence_ids_json=json.dumps(component.evidence_ids),
                    )
                )

    def _record_error(
        self, run_id: str, business_id: str, stage: str, code: str, message: str
    ) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                insert(schema.errors)
                .prefix_with("OR IGNORE")
                .values(
                    id=_id("error", run_id, business_id, stage, code),
                    run_id=run_id,
                    business_id=business_id,
                    job_id=None,
                    stage=stage,
                    code=code,
                    message=message,
                    retryable=True,
                    occurred_at=self._clock(),
                    idempotency_key=f"{run_id}:{business_id}:{stage}:{code}",
                )
            )

    def _write_drafts(self, run_id: str) -> None:
        with self._engine.connect() as connection:
            rows = (
                connection.execute(
                    select(
                        schema.businesses.c.id,
                        schema.businesses.c.name,
                        schema.assessments.c.id.label("assessment_id"),
                    )
                    .join(
                        schema.assessments,
                        schema.assessments.c.business_id == schema.businesses.c.id,
                    )
                    .where(
                        schema.assessments.c.run_id == run_id,
                        schema.assessments.c.qualified.is_(True),
                    )
                    .limit(10)
                )
                .mappings()
                .all()
            )
        model = self._draft_model_factory(self._settings)
        for row in rows:
            facts = self._valid_facts(run_id, str(row["id"]))
            packet = FactPacket(
                str(row["id"]),
                str(row["assessment_id"]),
                tuple(facts),
                tuple(f.fact_id for f in facts),
            )
            draft = build_fallback_draft(packet).model_copy(
                update={
                    "run_id": run_id,
                    "subject": f"A question for {row['name']}",
                    "created_at": self._clock(),
                }
            )
            if model is not None:
                validation = DraftGenerator(client=model).generate(packet)
                if validation.approved:
                    draft = draft.model_copy(
                        update={
                            "subject": validation.subject,
                            "body": validation.body,
                            "method": DraftMethod.OLLAMA,
                            "evidence_ids": validation.evidence_ids,
                        }
                    )
            with self._engine.begin() as connection:
                connection.execute(
                    insert(schema.drafts)
                    .prefix_with("OR IGNORE")
                    .values(
                        id=draft.draft_id,
                        run_id=run_id,
                        business_id=draft.business_id,
                        subject=draft.subject,
                        body=draft.body,
                        method=draft.method.value,
                        evidence_ids_json=json.dumps(draft.evidence_ids),
                        validation_state=draft.validation_state.value,
                        version=draft.version,
                        created_at=draft.created_at,
                    )
                )
            path = (
                self._settings.export_directory / run_id / "drafts" / f"{row['id']}.txt"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f"Subject: {draft.subject}\n\n{draft.body}\n", encoding="utf-8"
            )

    def _valid_facts(self, run_id: str, business_id: str) -> list[Fact]:
        with self._engine.connect() as connection:
            rows = (
                connection.execute(
                    select(schema.facts).where(
                        schema.facts.c.run_id == run_id,
                        schema.facts.c.business_id == business_id,
                        schema.facts.c.validation_state == ValidationState.VALID.value,
                    )
                )
                .mappings()
                .all()
            )
        return [
            Fact(
                fact_id=str(row["id"]),
                fact_type=str(row["fact_type"]),
                state=FactState(str(row["state"])),
                value=json.loads(row["value_json"]),
                source=str(row["source"]),
                excerpt=str(row["excerpt"]),
                captured_at=row["captured_at"],
                extractor_version=str(row["extractor_version"]),
                validation_state=ValidationState.VALID,
            )
            for row in rows
        ]

    def _write_exports(self, run_id: str) -> None:
        result = ExportService(
            output_directory=self._settings.export_directory / run_id,
            rows_for_run=self._export_rows,
        ).generate(run_id)
        with self._engine.begin() as connection:
            for kind, path, count in (
                ("qualified", result.qualified_path, result.qualified_rows),
                ("rejected", result.rejected_path, result.rejected_rows),
            ):
                connection.execute(
                    insert(schema.exports)
                    .prefix_with("OR REPLACE")
                    .values(
                        id=_id("export", run_id, kind),
                        run_id=run_id,
                        kind=kind,
                        file_path=str(path),
                        row_count=count,
                        generated_at=self._clock(),
                    )
                )

    def _export_rows(
        self, run_id: str
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        with self._engine.connect() as connection:
            rows = (
                connection.execute(
                    select(
                        schema.businesses,
                        schema.assessments,
                        schema.runs.c.city,
                        schema.runs.c.state,
                    )
                    .join(
                        schema.assessments,
                        schema.assessments.c.business_id == schema.businesses.c.id,
                    )
                    .join(schema.runs, schema.runs.c.id == schema.assessments.c.run_id)
                    .where(schema.assessments.c.run_id == run_id)
                )
                .mappings()
                .all()
            )
            contacts = (
                connection.execute(
                    select(schema.contacts).where(schema.contacts.c.run_id == run_id)
                )
                .mappings()
                .all()
            )
        emails = {
            str(row["business_id"]): str(row["value"])
            for row in contacts
            if row["kind"] == "email"
        }
        qualified: list[dict[str, object]] = []
        rejected: list[dict[str, object]] = []
        for row in rows:
            item = {
                "date_found": str(row["created_at"]),
                "restaurant_name": row["name"],
                "city": row["city"],
                "state": row["state"],
                "website": row["website"] or "",
                "address": row["address"] or "",
                "phone": row["phone"] or "",
                "recipient_email": emails.get(str(row["id"]), ""),
                "lead_score": row["total"],
                "outreach_status": "draft_ready" if row["qualified"] else "rejected",
                "run_id": run_id,
                "business_id": row["id"],
                "last_seen": str(row["updated_at"]),
            }
            (qualified if row["qualified"] else rejected).append(item)
        return qualified, rejected


def _build_crawler(settings: Settings) -> SiteCrawler:
    timeout = httpx.Timeout(
        settings.http_read_timeout_seconds,
        connect=settings.http_connect_timeout_seconds,
    )
    client = httpx.Client(timeout=timeout, headers={"User-Agent": settings.user_agent})
    robots = RobotsPolicy(
        user_agent=settings.user_agent, get=lambda url: client.get(url)
    )
    return SiteCrawler(
        PageFetcher(UrlPolicy(), robots, http_client=client),
        max_response_bytes=settings.max_response_bytes,
    )


def _draft_model(settings: Settings) -> OllamaDraftModel | None:
    client = OllamaClient(
        endpoint=str(settings.ollama_endpoint),
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    return (
        OllamaDraftModel(client)
        if client.readiness() is OllamaReadiness.READY
        else None
    )


def _signal_research(
    result: CrawlResult,
    facts: list[Fact],
    contacts: Sequence[ContactChannel],
) -> dict[str, object]:
    evidence: dict[str, tuple[str, ...]] = {}
    for fact in facts:
        if fact.fact_type == "call_to_reserve" and fact.state is FactState.PRESENT:
            evidence["call_required"] = (fact.fact_id,)
        if fact.fact_type in {"private_events", "catering"}:
            evidence[fact.fact_type] = (fact.fact_id,)
    public_phone_facts = [
        fact
        for fact in facts
        if fact.fact_type == "phone" and fact.state is FactState.PRESENT
    ]
    public_phone_contacts = [contact for contact in contacts if contact.kind == "phone"]
    if public_phone_facts:
        evidence["phone_prominent"] = tuple(fact.fact_id for fact in public_phone_facts)
    elif public_phone_contacts:
        evidence["phone_prominent"] = tuple(
            evidence_id
            for contact in public_phone_contacts
            for evidence_id in contact.evidence_ids
        )
    hour_facts = [
        fact
        for fact in facts
        if fact.fact_type == "hours" and fact.state is FactState.PRESENT
    ]
    if len(hour_facts) >= 5 and len({str(fact.value) for fact in hour_facts}) >= 2:
        evidence["complex_hours"] = tuple(fact.fact_id for fact in hour_facts)
    return {
        "complete_crawl": result.complete,
        "call_to_reserve": "call_required" in evidence,
        "online_booking": any(
            f.fact_type == "reservation_method" and f.value == "online" for f in facts
        ),
        "private_events": "private_events" in evidence,
        "catering": "catering" in evidence,
        "phone_prominent": "phone_prominent" in evidence,
        "complex_hours": "complex_hours" in evidence,
        "contact_route": bool(contacts),
        "evidence_ids": evidence,
    }


def _service_facts(pages: tuple[FetchedPage, ...]) -> list[Fact]:
    facts: list[Fact] = []
    for page in pages:
        text = extract_visible_text(page.html).text
        for kind, phrase in (
            ("private_events", "private event"),
            ("catering", "catering"),
        ):
            index = text.casefold().find(phrase)
            if index >= 0:
                excerpt = text[max(0, index - 100) : index + len(phrase) + 100].strip()
                identity = f"{page.url}:{kind}:{excerpt}"
                facts.append(
                    Fact(
                        fact_id=f"fact:{hashlib.sha256(identity.encode()).hexdigest()}",
                        fact_type=kind,
                        state=FactState.PRESENT,
                        value=True,
                        source=page.url,
                        excerpt=excerpt,
                        captured_at=page.fetched_at,
                        extractor_version="service-signals-v1",
                        validation_state=ValidationState.VALID,
                    )
                )
    return facts


def _id(*parts: str) -> str:
    return str(uuid5(NAMESPACE_URL, ":".join(parts)))


def _safe_error(error: Exception) -> str:
    return f"Official website could not be researched ({type(error).__name__})."

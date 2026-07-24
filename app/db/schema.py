from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)

from app.db.base import metadata as metadata

runs = Table(
    "runs",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("city", String(255), nullable=False),
    Column("state", String(2), nullable=False),
    Column("candidate_limit", Integer, nullable=False),
    Column("status", String(50), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
)

businesses = Table(
    "businesses",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("name", String(500), nullable=False),
    Column("lead_status", String(50), nullable=False, default="new"),
    Column("website", String(2048)),
    Column("phone", String(100)),
    Column("address", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

jobs = Table(
    "jobs",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("run_id", ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
    Column("business_id", ForeignKey("businesses.id", ondelete="CASCADE")),
    Column("stage", String(100), nullable=False),
    Column("status", String(50), nullable=False),
    Column("attempt_count", Integer, nullable=False),
    Column("max_attempts", Integer, nullable=False),
    Column("next_attempt_at", DateTime(timezone=True)),
    Column("lease_expires_at", DateTime(timezone=True)),
    Column("error_code", String(255)),
    Column("idempotency_key", String(500), nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True)),
)

business_aliases = Table(
    "business_aliases",
    metadata,
    Column("id", String(255), primary_key=True),
    Column(
        "business_id",
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("alias_type", String(100), nullable=False),
    Column("normalized_value", String(2048), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("alias_type", "normalized_value"),
)

run_candidates = Table(
    "run_candidates",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("run_id", ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
    Column(
        "business_id",
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("osm_type", String(20)),
    Column("osm_id", String(100)),
    Column("name_snapshot", String(500), nullable=False),
    Column("website_snapshot", String(2048)),
    Column("phone_snapshot", String(100)),
    Column("address_snapshot", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("run_id", "business_id"),
    UniqueConstraint("run_id", "osm_type", "osm_id"),
)

source_records = Table(
    "source_records",
    metadata,
    Column("id", String(255), primary_key=True),
    Column(
        "run_candidate_id",
        ForeignKey("run_candidates.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("source_type", String(100), nullable=False),
    Column("source_identifier", String(500), nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("captured_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("run_candidate_id", "source_type", "source_identifier"),
)

crawl_pages = Table(
    "crawl_pages",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("run_id", ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
    Column(
        "business_id",
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("url", String(2048), nullable=False),
    Column("robots_decision", String(50)),
    Column("status", String(50), nullable=False),
    Column("http_status", Integer),
    Column("content_hash", String(255)),
    Column("error_code", String(255)),
    Column("fetched_at", DateTime(timezone=True)),
    UniqueConstraint("run_id", "business_id", "url"),
)

facts = Table(
    "facts",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("run_id", ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
    Column(
        "business_id",
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("fact_type", String(255), nullable=False),
    Column("state", String(50), nullable=False),
    Column("value_json", Text),
    Column("source", String(2048), nullable=False),
    Column("excerpt", Text, nullable=False),
    Column("captured_at", DateTime(timezone=True), nullable=False),
    Column("extractor_version", String(255), nullable=False),
    Column("validation_state", String(50), nullable=False),
    Column("idempotency_key", String(500), nullable=False, unique=True),
)

contacts = Table(
    "contacts",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("run_id", ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
    Column(
        "business_id",
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("kind", String(50), nullable=False),
    Column("value", String(2048), nullable=False),
    Column("evidence_ids_json", Text, nullable=False),
    Column("classification", String(100)),
    Column("syntax_state", String(50), nullable=False),
    Column("dns_state", String(50), nullable=False),
    Column("mx_state", String(50), nullable=False),
    Column("idempotency_key", String(500), nullable=False, unique=True),
)

people = Table(
    "people",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("run_id", ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
    Column(
        "business_id",
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("name", String(500), nullable=False),
    Column("role", String(500), nullable=False),
    Column("evidence_ids_json", Text, nullable=False),
    Column("idempotency_key", String(500), nullable=False, unique=True),
)

assessments = Table(
    "assessments",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("run_id", ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
    Column(
        "business_id",
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("total", Integer, nullable=False),
    Column("qualified", Boolean, nullable=False),
    Column("scoring_version", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("run_id", "business_id", "scoring_version"),
)

score_signals = Table(
    "score_signals",
    metadata,
    Column("id", String(255), primary_key=True),
    Column(
        "assessment_id",
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("signal", String(255), nullable=False),
    Column("state", String(50), nullable=False),
    Column("delta", Integer, nullable=False),
    Column("explanation", Text, nullable=False),
    Column("evidence_ids_json", Text, nullable=False),
    UniqueConstraint("assessment_id", "signal"),
)

drafts = Table(
    "drafts",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("run_id", ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
    Column(
        "business_id",
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("subject", String(500), nullable=False),
    Column("body", Text, nullable=False),
    Column("method", String(50), nullable=False),
    Column("evidence_ids_json", Text, nullable=False),
    Column("validation_state", String(50), nullable=False),
    Column("version", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("run_id", "business_id", "version"),
)

notes = Table(
    "notes",
    metadata,
    Column("id", String(255), primary_key=True),
    Column(
        "business_id",
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("body", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

status_history = Table(
    "status_history",
    metadata,
    Column("id", String(255), primary_key=True),
    Column(
        "business_id",
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("from_status", String(50)),
    Column("to_status", String(50), nullable=False),
    Column("changed_at", DateTime(timezone=True), nullable=False),
)

errors = Table(
    "errors",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("run_id", ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
    Column("business_id", ForeignKey("businesses.id", ondelete="CASCADE")),
    Column("job_id", ForeignKey("jobs.id", ondelete="SET NULL")),
    Column("stage", String(100), nullable=False),
    Column("code", String(255), nullable=False),
    Column("message", Text, nullable=False),
    Column("retryable", Boolean, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("idempotency_key", String(500), nullable=False, unique=True),
)

exports = Table(
    "exports",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("run_id", ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
    Column("kind", String(50), nullable=False),
    Column("file_path", String(2048), nullable=False),
    Column("row_count", Integer, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("run_id", "kind"),
)

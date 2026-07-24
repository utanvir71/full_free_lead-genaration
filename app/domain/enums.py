from enum import StrEnum


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class LeadStatus(StrEnum):
    NEW = "new"
    NEEDS_REVIEW = "needs_review"
    DRAFT_READY = "draft_ready"
    CONTACTED = "contacted"
    REPLIED = "replied"
    REJECTED = "rejected"


class FactState(StrEnum):
    UNKNOWN = "unknown"
    ABSENT = "absent"
    FALSE = "false"
    TRUE = "true"
    PRESENT = "present"


class SignalState(StrEnum):
    AWARDED = "awarded"
    DENIED = "denied"
    UNKNOWN = "unknown"


class ValidationState(StrEnum):
    UNKNOWN = "unknown"
    VALID = "valid"
    INVALID = "invalid"
    NOT_APPLICABLE = "not_applicable"


class DraftMethod(StrEnum):
    OLLAMA = "ollama"
    FALLBACK = "fallback"

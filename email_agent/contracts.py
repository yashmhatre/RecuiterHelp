"""Frozen types shared by every stage of the pipeline.

Transcribed from ``docs/CONTRACTS.md`` section 1 -- same names, same order, same types;
formatting normalised to this repo's style. Types only: no logic, no I/O, and no
imports from the rest of this package. Every other ticket imports from here and treats this
module as read-only.

Changing anything in this file means changing ``docs/CONTRACTS.md`` first, in its own PR, flagged
in every open ticket it touches. Do not widen a shape inside a feature ticket.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol

# ---------- enums ----------


class Intent(str, Enum):
    NEW_REQUIREMENT = "new_requirement"
    RESUME_REQUEST = "resume_request"
    FOLLOW_UP = "follow_up"
    INTERVIEW = "interview"
    OTHER = "other"


class AuthResult(str, Enum):
    PASS = "pass"  # SPF + DKIM + DMARC all pass
    FAIL = "fail"  # any of the three fails
    UNKNOWN = "unknown"  # headers absent or unparseable


class EmailStatus(str, Enum):
    FETCHED = "fetched"
    SKIPPED_BULK = "skipped_bulk"
    SKIPPED_AUTH = "skipped_auth"
    NOT_RECRUITER = "not_recruiter"
    NEEDS_REVIEW = "needs_review"
    DRAFTED = "drafted"


# ---------- email ----------


@dataclass(frozen=True)
class RawEmail:
    """What a provider returns. Providers normalise into this; nothing downstream
    knows whether it came from Gmail or Graph."""

    provider: str  # "gmail" | "outlook"
    provider_message_id: str
    thread_id: str
    from_name: str
    from_email: str
    reply_to: str | None
    to: Sequence[str]
    subject: str
    body_text: str  # plain text, HTML already stripped
    received_at: datetime
    headers: dict[str, str]  # lower-cased header names
    is_from_self: bool


@dataclass(frozen=True)
class VerificationResult:
    result: AuthResult
    spf: str  # "pass" | "fail" | "softfail" | "none"
    dkim: str
    dmarc: str
    flags: Sequence[str]  # e.g. ["reply_to_domain_mismatch", "freemail_claims_company"]
    reason: str


@dataclass(frozen=True)
class PrefilterResult:
    keep: bool
    rule: str | None  # the rule that dropped it, e.g. "list_unsubscribe"


# ---------- classification ----------


@dataclass(frozen=True)
class ExtractedFields:
    role: str | None
    skills: Sequence[str]
    min_years_experience: float | None
    location: str | None
    candidate_names: Sequence[str]
    resume_requested: bool


@dataclass(frozen=True)
class Classification:
    is_recruiter: bool
    confidence: float  # 0.0 - 1.0
    intent: Intent
    fields: ExtractedFields
    model: str  # e.g. "qwen3:8b"


# ---------- candidates ----------


@dataclass(frozen=True)
class Candidate:
    id: int
    name: str
    email: str
    phone: str | None
    location: str | None
    notice_period_days: int | None
    availability: str | None
    active: bool


@dataclass(frozen=True)
class Profile:
    id: int
    candidate_id: int
    title: str
    skills: Sequence[str]
    years_experience: float
    summary: str
    active: bool
    candidate: Candidate | None = None


@dataclass(frozen=True)
class Resume:
    id: int
    profile_id: int
    file_path: str
    version: int
    uploaded_at: datetime
    is_current: bool


# ---------- matching ----------


@dataclass(frozen=True)
class Match:
    profile_id: int
    candidate_id: int
    score: float  # 0.0 - 1.0, comparable across stages
    reason: str  # one line, shown to the reviewer
    stage: str  # "hybrid" | "rerank"
    selected: bool


# ---------- draft ----------


@dataclass(frozen=True)
class DraftAttachment:
    profile_id: int
    candidate_id: int
    file_path: str
    filename: str  # what the recipient sees


@dataclass(frozen=True)
class DraftContent:
    """draft.py produces this. validate.py checks it. The provider saves it."""

    to: Sequence[str]
    subject: str
    body_text: str
    in_reply_to_message_id: str
    thread_id: str
    attachments: Sequence[DraftAttachment]
    profiles_used: Sequence[int]


@dataclass(frozen=True)
class ValidationIssue:
    check: str  # e.g. "attachment_belongs_to_candidate"
    detail: str


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    issues: Sequence[ValidationIssue] = field(default_factory=tuple)


@dataclass(frozen=True)
class SavedDraft:
    provider_draft_id: str
    thread_id: str


# ---------- provider interface ----------


class MailProvider(Protocol):
    """No send method exists on this interface. That is requirement 5, enforced by shape."""

    name: str

    def fetch_new(self, cursor: str | None) -> tuple[Sequence[RawEmail], str]:
        """Return new messages and the next cursor (Gmail history id / Graph delta link)."""

    def save_draft(self, content: DraftContent) -> SavedDraft:
        """Save a reply draft in the original thread."""

    def apply_label(self, provider_message_id: str, label: str) -> None:
        """Gmail label or Outlook category. Creates it if missing."""

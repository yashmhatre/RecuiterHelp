# Contracts (frozen for v1)

Every ticket is built against this file, **not** against another ticket's output. That is what
makes the tickets independent: two people can work on `classify.py` and `match.py` at the same
time, in different clones, and the pieces fit when both land.

Rules:

1. This file is the only cross-ticket dependency. If a ticket needs something from another
   ticket, that something is written down here first.
2. A ticket never imports code owned by another ticket. It imports from `contracts.py`
   (types only) and consumes/produces the shapes below.
3. Changing a contract is its own change: a PR that edits this file, flagged in every open
   ticket it touches. Do not silently widen a shape inside a feature ticket.
4. Every ticket ships its own fixtures built from the shapes here. No ticket waits for real
   data, a real mailbox, or a real database to be testable.

---

## 1. Python types

Ticket **P0-01** creates `contracts.py` from this section verbatim. Every other ticket imports
from it and treats it as read-only.

```python
# contracts.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol, Sequence

# ---------- enums ----------

class Intent(str, Enum):
    NEW_REQUIREMENT = "new_requirement"
    RESUME_REQUEST  = "resume_request"
    FOLLOW_UP       = "follow_up"
    INTERVIEW       = "interview"
    OTHER           = "other"

class AuthResult(str, Enum):
    PASS    = "pass"        # SPF + DKIM + DMARC all pass
    FAIL    = "fail"        # any of the three fails
    UNKNOWN = "unknown"     # headers absent or unparseable

class EmailStatus(str, Enum):
    FETCHED       = "fetched"
    SKIPPED_BULK  = "skipped_bulk"
    SKIPPED_AUTH  = "skipped_auth"
    NOT_RECRUITER = "not_recruiter"
    NEEDS_REVIEW  = "needs_review"
    DRAFTED       = "drafted"

# ---------- email ----------

@dataclass(frozen=True)
class RawEmail:
    """What a provider returns. Providers normalise into this; nothing downstream
    knows whether it came from Gmail or Graph."""
    provider: str                     # "gmail" | "outlook"
    provider_message_id: str
    thread_id: str
    from_name: str
    from_email: str
    reply_to: str | None
    to: Sequence[str]
    subject: str
    body_text: str                    # plain text, HTML already stripped
    received_at: datetime
    headers: dict[str, str]           # lower-cased header names
    is_from_self: bool

@dataclass(frozen=True)
class VerificationResult:
    result: AuthResult
    spf: str                          # "pass" | "fail" | "softfail" | "none"
    dkim: str
    dmarc: str
    flags: Sequence[str]              # e.g. ["reply_to_domain_mismatch", "freemail_claims_company"]
    reason: str

@dataclass(frozen=True)
class PrefilterResult:
    keep: bool
    rule: str | None                  # the rule that dropped it, e.g. "list_unsubscribe"

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
    confidence: float                 # 0.0 - 1.0
    intent: Intent
    fields: ExtractedFields
    model: str                        # e.g. "qwen3:8b"

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
    score: float                      # 0.0 - 1.0, comparable across stages
    reason: str                       # one line, shown to the reviewer
    stage: str                        # "hybrid" | "rerank"
    selected: bool

# ---------- draft ----------

@dataclass(frozen=True)
class DraftAttachment:
    profile_id: int
    candidate_id: int
    file_path: str
    filename: str                     # what the recipient sees

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
    check: str                        # e.g. "attachment_belongs_to_candidate"
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
```

---

## 2. Label names

Exactly two, created on first use:

| Constant | Value | Applied when |
|---|---|---|
| `LABEL_DRAFTED` | `AI Draft` | A draft was saved and passed validation |
| `LABEL_REVIEW` | `Needs review` | Low confidence, failed auth, or failed validation — **no draft saved** |

---

## 3. Model call contract

Two Ollama calls, both with `format: json` and thinking disabled. `classify.py` and the re-ranker
each own their prompt file under `config/prompts/`.

**Classify response schema** (`classify.v1`):

```json
{
  "is_recruiter": true,
  "confidence": 0.93,
  "intent": "new_requirement",
  "role": "Senior Python Engineer",
  "skills": ["python", "fastapi", "postgres"],
  "min_years_experience": 5,
  "location": "Pune, hybrid",
  "candidate_names": [],
  "resume_requested": false
}
```

**Re-rank response schema** (`rerank.v1`) — input is the requirement plus up to 10 candidate
profiles, each with an opaque `profile_id`:

```json
{
  "ranked": [
    { "profile_id": 42, "score": 0.88, "reason": "7 yrs Python + FastAPI, Pune, 30-day notice" }
  ]
}
```

Any response failing schema validation is retried once, then treated as `is_recruiter=false` /
empty ranking, and the email goes to `Needs review`.

---

## 4. Thresholds

Config keys in `config/settings.yaml`, all overridable by env var. Owned by **P0-01**; the values
are tuned in **P3-03**, and no other ticket hardcodes them.

| Key | Default | Meaning |
|---|---|---|
| `classify.min_confidence` | `0.75` | Below this → `Needs review`, no draft |
| `match.min_score` | `0.60` | A match below this is never drafted |
| `match.max_profiles` | `3` | Hard cap on profiles per draft |
| `match.rerank_pool` | `10` | How many hybrid hits go to the re-ranker |
| `match.hybrid_alpha` | `0.6` | Vector weight; keyword weight is `1 - alpha` |
| `draft.max_words` | `200` | Validation fails above this |
| `poll.interval_seconds` | `120` | Polling loop period |

---

## 5. Database

`docs/schema.reference.sql` is the frozen DDL. **P1-01** turns it into real migrations; any ticket
needing a table reads the shape from that file and builds its own fixtures. Column names there are
final.

---

## 6. MLflow logging contract

One MLflow run per email, tagged `provider`, `intent`, `email_id`. Owned by **P0-04**, which ships
`tracing.py` with this surface:

```python
def start_email_run(email_id: str, provider: str) -> contextlib.AbstractContextManager: ...
def log_stage(stage: str, duration_ms: int, payload: dict) -> None: ...
def log_metrics(metrics: dict[str, float]) -> None: ...
```

Callers use `log_stage("classify", ms, {...})`. If MLflow is unreachable, every function is a
no-op that logs a warning — **a tracing outage never fails the pipeline**, and no ticket needs
MLflow running to be testable.

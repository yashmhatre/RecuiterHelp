"""Shared provider surface: the abstract base, the label names, and the error types.

Both real providers (P2-02 Gmail, P2-03 Graph) subclass ``BaseMailProvider`` and are verified by
the same reusable suite in ``tests/test_provider_contract.py``. Anything downstream sees only
``RawEmail`` and ``DraftContent``, so it cannot tell which provider it is talking to — that is
requirement 7.

There is no send method here, and no path to one. That is requirement 5 enforced by shape, and
``tests/test_no_send_path.py`` enforces it across the whole repository.

The error types live here rather than in each provider so that the orchestrator can catch one
kind of failure regardless of which mailbox raised it. Without that, P2-02 and P2-03 would each
invent their own and P2-12 would have to know both.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from email_agent.contracts import DraftContent, RawEmail, SavedDraft

__all__ = [
    "LABEL_DRAFTED",
    "LABEL_REVIEW",
    "ALL_LABELS",
    "BaseMailProvider",
    "ProviderError",
    "TransientProviderError",
    "CursorExpiredError",
    "AuthorisationError",
]

# ---------------------------------------------------------------------------
# Labels (docs/CONTRACTS.md section 2)
# ---------------------------------------------------------------------------

#: Applied when a draft was saved and passed validation.
LABEL_DRAFTED = "AI Draft"

#: Applied when there is no draft: low confidence, failed authentication, no match above
#: threshold, or failed validation. A human picks these up.
LABEL_REVIEW = "Needs review"

ALL_LABELS = (LABEL_DRAFTED, LABEL_REVIEW)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ProviderError(Exception):
    """Any mailbox failure. The orchestrator catches this and routes to 'Needs review'."""


class TransientProviderError(ProviderError):
    """Rate limited or a server error, after retries were exhausted.

    Distinct from ``ProviderError`` because the polling loop should try again next tick rather
    than treat the message as permanently broken.
    """


class CursorExpiredError(ProviderError):
    """The stored sync cursor is no longer usable.

    Gmail expires history ids; Graph returns 410 Gone for a stale delta token. Both mean the
    same thing to a caller: fall back to a bounded full sync. Raised so a provider cannot
    quietly return an empty list and let new mail go unprocessed.
    """


class AuthorisationError(ProviderError):
    """Credentials are missing, expired beyond refresh, or revoked. Needs a human to re-consent."""


# ---------------------------------------------------------------------------
# Base provider
# ---------------------------------------------------------------------------


class BaseMailProvider(ABC):
    """What every provider implements. Structurally matches ``contracts.MailProvider``.

    Subclasses must not add a send method. ``__init_subclass__`` refuses one at class-creation
    time, so the mistake surfaces on import rather than in review.
    """

    #: "gmail" | "outlook" | "fake"
    name: str = ""

    #: Fetch no more than this many messages when a cursor has expired and a full sync is needed.
    #: Bounded so a first run against a large mailbox cannot stall or blow memory.
    full_sync_limit: int = 200

    _FORBIDDEN_SUBCLASS_ATTRS = ("send", "send_mail", "sendMail", "send_message", "send_draft")

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for attr in cls._FORBIDDEN_SUBCLASS_ATTRS:
            if attr in cls.__dict__:
                raise TypeError(
                    f"{cls.__name__}.{attr} is not allowed: providers save drafts and never "
                    f"send. See requirement 5 in Plan.md."
                )

    @abstractmethod
    def fetch_new(self, cursor: str | None) -> tuple[Sequence[RawEmail], str]:
        """Return messages new since ``cursor``, and the cursor to store for next time.

        ``cursor`` is ``None`` on a first run. The returned cursor must be usable immediately:
        passing it straight back must yield no messages. Raises ``CursorExpiredError`` when the
        stored cursor is too old to use.
        """

    @abstractmethod
    def save_draft(self, content: DraftContent) -> SavedDraft:
        """Save a reply draft in the original thread. Never sends."""

    @abstractmethod
    def apply_label(self, provider_message_id: str, label: str) -> None:
        """Apply a Gmail label or Outlook category, creating it if missing. Idempotent."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r}>"

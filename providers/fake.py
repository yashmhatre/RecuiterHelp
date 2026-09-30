"""In-memory provider, seeded from a JSONL file.

This is the reason tickets P2-04 through P2-12 do not need an authorised mailbox. It implements
the same contract as the real providers, with the same cursor semantics, so a pipeline wired to
it behaves the way it will in production.

Seeded from the ``labels.example.jsonl`` record shape (see ``eval/dataset/schema.json``), so the
same fixtures serve the evaluation harness and the pipeline tests.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from email_agent.contracts import DraftContent, RawEmail, SavedDraft
from providers.base import ALL_LABELS, BaseMailProvider, CursorExpiredError, ProviderError

__all__ = ["FakeMailProvider", "record_to_raw_email"]

DEFAULT_SELF_ADDRESS = "us@example.com"


def record_to_raw_email(
    record: dict,
    *,
    self_address: str = DEFAULT_SELF_ADDRESS,
    received_at: datetime | None = None,
) -> RawEmail:
    """Convert one labelled-dataset record into a ``RawEmail``.

    Only the transport fields are read. The ground-truth labels in the record are ignored: a
    provider must never hand the pipeline the answers.
    """
    headers = {k.lower(): v for k, v in (record.get("headers") or {}).items()}
    raw_from = headers.get("from", "")
    from_name, from_email = _split_address(raw_from)

    return RawEmail(
        provider="fake",
        provider_message_id=record["id"],
        thread_id=record.get("thread_id") or f"thread-{record['id']}",
        from_name=from_name,
        from_email=from_email,
        reply_to=headers.get("reply-to"),
        to=[self_address],
        subject=record.get("subject", ""),
        body_text=record.get("body_text", ""),
        received_at=received_at or datetime(2026, 1, 1, tzinfo=UTC),
        headers=headers,
        is_from_self=from_email.lower() == self_address.lower(),
    )


def _split_address(raw: str) -> tuple[str, str]:
    """Split ``Jane Doe <jane@x.com>`` into name and address. Tolerates a bare address."""
    raw = (raw or "").strip()
    if "<" in raw and ">" in raw:
        name = raw[: raw.index("<")].strip().strip('"')
        address = raw[raw.index("<") + 1 : raw.rindex(">")].strip()
        return name, address
    return "", raw


class FakeMailProvider(BaseMailProvider):
    """A mailbox that lives in a list.

    Cursor semantics match the real providers: the cursor marks a position, passing it back
    yields nothing new, and an expired cursor raises ``CursorExpiredError`` rather than
    silently returning an empty batch.
    """

    name = "fake"

    def __init__(
        self,
        emails: Sequence[RawEmail] | None = None,
        *,
        self_address: str = DEFAULT_SELF_ADDRESS,
        existing_labels: Sequence[str] = ALL_LABELS,
    ) -> None:
        self.self_address = self_address
        self._emails: list[RawEmail] = list(emails or [])
        #: Labels that already exist in the mailbox. Applying an unknown one creates it.
        self.labels: set[str] = set(existing_labels)

        #: Everything the pipeline did, for tests to assert against.
        self.saved_drafts: list[DraftContent] = []
        self.applied_labels: list[tuple[str, str]] = []
        self.created_labels: list[str] = []
        self.fetch_calls: list[str | None] = []

        self._next_draft_id = 1
        self._expire_next_fetch = False

    # -- seeding ---------------------------------------------------------

    @classmethod
    def from_jsonl(
        cls, path: Path | str, *, self_address: str = DEFAULT_SELF_ADDRESS, **kwargs: object
    ) -> FakeMailProvider:
        """Seed from a labelled-dataset JSONL file."""
        emails: list[RawEmail] = []
        with open(path, encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                emails.append(
                    record_to_raw_email(
                        record,
                        self_address=self_address,
                        # Space arrivals a minute apart so ordering is deterministic and
                        # cursor behaviour is meaningful.
                        received_at=datetime(2026, 1, 1, 0, index % 60, tzinfo=UTC),
                    )
                )
        return cls(emails, self_address=self_address, **kwargs)  # type: ignore[arg-type]

    def add(self, email: RawEmail) -> None:
        """Deliver a new message, as if it had just arrived."""
        self._emails.append(email)

    def expire_cursor(self) -> None:
        """Make the next ``fetch_new`` with a non-None cursor raise ``CursorExpiredError``.

        Gmail expires history ids and Graph expires delta tokens. P2-12 needs to prove the
        polling loop survives that, which it cannot do against a mailbox that never expires.
        """
        self._expire_next_fetch = True

    # -- contract --------------------------------------------------------

    def fetch_new(self, cursor: str | None) -> tuple[Sequence[RawEmail], str]:
        self.fetch_calls.append(cursor)

        if cursor is not None and self._expire_next_fetch:
            self._expire_next_fetch = False
            raise CursorExpiredError(
                f"Fake cursor {cursor!r} has expired; fall back to a bounded full sync."
            )

        start = self._parse_cursor(cursor)
        batch = self._emails[start : start + self.full_sync_limit]
        return batch, str(start + len(batch))

    def save_draft(self, content: DraftContent) -> SavedDraft:
        if not content.thread_id:
            raise ProviderError("Cannot save a draft with no thread_id: the reply would not thread.")
        if not content.to:
            raise ProviderError("Cannot save a draft with no recipient.")
        for attachment in content.attachments:
            if not Path(attachment.file_path).is_file():
                raise ProviderError(
                    f"Attachment not found on disk: {attachment.file_path}. A real provider "
                    f"would fail the upload here too."
                )

        self.saved_drafts.append(content)
        draft_id = f"fake-draft-{self._next_draft_id}"
        self._next_draft_id += 1
        return SavedDraft(provider_draft_id=draft_id, thread_id=content.thread_id)

    def apply_label(self, provider_message_id: str, label: str) -> None:
        if not any(e.provider_message_id == provider_message_id for e in self._emails):
            raise ProviderError(f"No such message: {provider_message_id!r}")
        if label not in self.labels:
            self.labels.add(label)
            self.created_labels.append(label)
        if (provider_message_id, label) not in self.applied_labels:
            self.applied_labels.append((provider_message_id, label))

    # -- helpers ---------------------------------------------------------

    def _parse_cursor(self, cursor: str | None) -> int:
        if cursor is None:
            return 0
        try:
            position = int(cursor)
        except (TypeError, ValueError) as exc:
            raise CursorExpiredError(f"Unreadable cursor {cursor!r}") from exc
        if position < 0 or position > len(self._emails):
            raise CursorExpiredError(
                f"Cursor {cursor!r} is outside this mailbox ({len(self._emails)} messages)"
            )
        return position

    def labels_for(self, provider_message_id: str) -> list[str]:
        """Every label applied to one message, for test assertions."""
        return [label for mid, label in self.applied_labels if mid == provider_message_id]

    @property
    def message_count(self) -> int:
        return len(self._emails)

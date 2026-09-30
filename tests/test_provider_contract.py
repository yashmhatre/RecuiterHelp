"""The reusable provider contract suite.

Every provider must pass this. P2-02 and P2-03 import ``ProviderContractTests``, set
``make_provider``, and inherit the whole suite:

    from tests.test_provider_contract import ProviderContractTests

    class TestGmailProvider(ProviderContractTests):
        def make_provider(self, emails):
            return GmailProvider(credentials=StubCredentials(), transport=recorded(emails))

That is what makes requirement 7 checkable — "the same pipeline passes the test set on both
providers" is only meaningful if both are held to one definition of correct behaviour, written
once.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from email_agent.contracts import DraftAttachment, DraftContent, RawEmail, SavedDraft
from providers.base import (
    LABEL_DRAFTED,
    LABEL_REVIEW,
    BaseMailProvider,
    CursorExpiredError,
    ProviderError,
)
from providers.fake import FakeMailProvider

SELF_ADDRESS = "us@example.com"


def make_email(
    message_id: str,
    *,
    from_email: str = "recruiter@agency.example.com",
    thread_id: str | None = None,
    subject: str = "Senior Python Engineer",
    is_from_self: bool = False,
) -> RawEmail:
    return RawEmail(
        provider="fake",
        provider_message_id=message_id,
        thread_id=thread_id or f"thread-{message_id}",
        from_name="A Recruiter",
        from_email=from_email,
        reply_to=None,
        to=[SELF_ADDRESS],
        subject=subject,
        body_text="We have an opening.",
        received_at=datetime(2026, 1, 1, tzinfo=UTC),
        headers={"authentication-results": "spf=pass dkim=pass dmarc=pass"},
        is_from_self=is_from_self,
    )


def make_draft(
    email: RawEmail, attachments: Sequence[DraftAttachment] = (), profiles: Sequence[int] = (1,)
) -> DraftContent:
    return DraftContent(
        to=[email.from_email],
        subject=f"Re: {email.subject}",
        body_text="One strong match attached.",
        in_reply_to_message_id=email.provider_message_id,
        thread_id=email.thread_id,
        attachments=list(attachments),
        profiles_used=list(profiles),
    )


class ProviderContractTests:
    """Subclass this and implement ``make_provider``."""

    def make_provider(self, emails: Sequence[RawEmail]) -> BaseMailProvider:
        raise NotImplementedError("Provider test classes must implement make_provider")

    # -- shape -----------------------------------------------------------

    def test_declares_a_name(self):
        assert self.make_provider([]).name

    def test_has_no_send_method(self):
        """Requirement 5, checked per provider as well as repo-wide."""
        provider = self.make_provider([])

        for attr in ("send", "send_mail", "sendMail", "send_message", "send_draft"):
            assert not hasattr(provider, attr), f"{attr} must not exist on a provider"

    def test_implements_the_three_contract_methods(self):
        provider = self.make_provider([])

        assert callable(provider.fetch_new)
        assert callable(provider.save_draft)
        assert callable(provider.apply_label)

    # -- fetch and cursor ------------------------------------------------

    def test_first_fetch_with_no_cursor_returns_everything(self):
        provider = self.make_provider([make_email("m1"), make_email("m2")])

        emails, cursor = provider.fetch_new(None)

        assert [e.provider_message_id for e in emails] == ["m1", "m2"]
        assert cursor

    def test_returned_cursor_yields_nothing_new(self):
        """The core cursor guarantee. If this fails, every restart re-drafts old mail."""
        provider = self.make_provider([make_email("m1"), make_email("m2")])

        _, cursor = provider.fetch_new(None)
        second_batch, second_cursor = provider.fetch_new(cursor)

        assert list(second_batch) == []
        assert second_cursor

    def test_cursor_is_stable_when_nothing_arrived(self):
        provider = self.make_provider([make_email("m1")])

        _, cursor = provider.fetch_new(None)
        _, again = provider.fetch_new(cursor)
        _, third = provider.fetch_new(again)

        assert again == third

    def test_only_messages_after_the_cursor_are_returned(self):
        provider = self.make_provider([make_email("m1")])
        _, cursor = provider.fetch_new(None)

        self.deliver(provider, make_email("m2"))
        batch, _ = provider.fetch_new(cursor)

        assert [e.provider_message_id for e in batch] == ["m2"]

    def test_fetch_returns_raw_email_instances(self):
        provider = self.make_provider([make_email("m1")])

        emails, _ = provider.fetch_new(None)

        assert all(isinstance(e, RawEmail) for e in emails)

    def test_headers_are_lower_cased(self):
        """Downstream code looks up 'authentication-results' without guessing at casing."""
        provider = self.make_provider([make_email("m1")])

        emails, _ = provider.fetch_new(None)

        assert all(key == key.lower() for key in emails[0].headers)

    def test_received_at_is_timezone_aware(self):
        """A naive datetime here silently shifts the arrival-to-draft latency metric."""
        provider = self.make_provider([make_email("m1")])

        emails, _ = provider.fetch_new(None)

        assert emails[0].received_at.tzinfo is not None

    def test_empty_mailbox_returns_an_empty_batch_and_a_cursor(self):
        emails, cursor = self.make_provider([]).fetch_new(None)

        assert list(emails) == []
        assert cursor is not None

    def test_an_unusable_cursor_raises_rather_than_returning_nothing(self):
        """Silently returning an empty batch would mean new mail is never processed again."""
        provider = self.make_provider([make_email("m1")])

        with pytest.raises(CursorExpiredError):
            provider.fetch_new("definitely-not-a-valid-cursor")

    # -- drafts ----------------------------------------------------------

    def test_save_draft_returns_an_id_and_keeps_the_thread(self):
        email = make_email("m1")
        provider = self.make_provider([email])

        saved = provider.save_draft(make_draft(email))

        assert isinstance(saved, SavedDraft)
        assert saved.provider_draft_id
        assert saved.thread_id == email.thread_id

    def test_each_saved_draft_gets_a_distinct_id(self):
        email = make_email("m1")
        provider = self.make_provider([email])

        first = provider.save_draft(make_draft(email))
        second = provider.save_draft(make_draft(email))

        assert first.provider_draft_id != second.provider_draft_id

    def test_a_draft_with_no_thread_is_rejected(self):
        email = make_email("m1")
        provider = self.make_provider([email])
        orphan = DraftContent(
            to=[email.from_email],
            subject="Re: x",
            body_text="body",
            in_reply_to_message_id=email.provider_message_id,
            thread_id="",
            attachments=[],
            profiles_used=[],
        )

        with pytest.raises(ProviderError):
            provider.save_draft(orphan)

    def test_a_draft_with_no_recipient_is_rejected(self):
        email = make_email("m1")
        provider = self.make_provider([email])
        no_to = DraftContent(
            to=[],
            subject="Re: x",
            body_text="body",
            in_reply_to_message_id=email.provider_message_id,
            thread_id=email.thread_id,
            attachments=[],
            profiles_used=[],
        )

        with pytest.raises(ProviderError):
            provider.save_draft(no_to)

    def test_a_missing_attachment_file_is_rejected(self, tmp_path: Path):
        """Better to fail here than to save a draft whose resume silently did not attach."""
        email = make_email("m1")
        provider = self.make_provider([email])
        draft = make_draft(
            email,
            attachments=[
                DraftAttachment(
                    profile_id=1,
                    candidate_id=1,
                    file_path=str(tmp_path / "gone.pdf"),
                    filename="gone.pdf",
                )
            ],
        )

        with pytest.raises(ProviderError):
            provider.save_draft(draft)

    def test_a_draft_with_a_real_attachment_saves(self, tmp_path: Path):
        resume = tmp_path / "Someone_Engineer.pdf"
        resume.write_bytes(b"%PDF-1.4 fake")
        email = make_email("m1")
        provider = self.make_provider([email])
        draft = make_draft(
            email,
            attachments=[
                DraftAttachment(
                    profile_id=1,
                    candidate_id=7,
                    file_path=str(resume),
                    filename=resume.name,
                )
            ],
        )

        assert provider.save_draft(draft).provider_draft_id

    # -- labels ----------------------------------------------------------

    @pytest.mark.parametrize("label", [LABEL_DRAFTED, LABEL_REVIEW])
    def test_applying_a_contract_label_works(self, label: str):
        provider = self.make_provider([make_email("m1")])

        provider.apply_label("m1", label)

    def test_applying_a_label_twice_is_a_no_op(self):
        """The orchestrator may retry an email; a second label must not error or duplicate."""
        provider = self.make_provider([make_email("m1")])

        provider.apply_label("m1", LABEL_REVIEW)
        provider.apply_label("m1", LABEL_REVIEW)

    def test_a_label_that_does_not_exist_yet_is_created(self):
        provider = self.make_provider([make_email("m1")])

        provider.apply_label("m1", "Brand New Label")

    def test_labelling_an_unknown_message_raises(self):
        provider = self.make_provider([make_email("m1")])

        with pytest.raises(ProviderError):
            provider.apply_label("no-such-message", LABEL_REVIEW)

    # -- hook ------------------------------------------------------------

    def deliver(self, provider: BaseMailProvider, email: RawEmail) -> None:
        """Simulate a new message arriving. Real providers override with their own mechanism."""
        provider.add(email)  # type: ignore[attr-defined]


class TestFakeMailProvider(ProviderContractTests):
    """The fake is held to exactly the same contract as Gmail and Graph."""

    def make_provider(self, emails):
        return FakeMailProvider(emails, self_address=SELF_ADDRESS)

    # -- fake-only behaviour ---------------------------------------------

    def test_seeds_from_the_example_dataset(self):
        path = Path(__file__).resolve().parent.parent / "eval" / "dataset" / "labels.example.jsonl"
        provider = FakeMailProvider.from_jsonl(path)

        emails, _ = provider.fetch_new(None)

        assert len(emails) == 10
        assert all(e.from_email.endswith(".example.com") for e in emails)

    def test_seeding_does_not_leak_the_ground_truth_labels(self):
        """A provider handing the pipeline the answers would make every metric meaningless."""
        path = Path(__file__).resolve().parent.parent / "eval" / "dataset" / "labels.example.jsonl"
        provider = FakeMailProvider.from_jsonl(path)

        emails, _ = provider.fetch_new(None)

        for email in emails:
            assert not hasattr(email, "is_recruiter")
            assert not hasattr(email, "intent")
            assert "is_recruiter" not in email.headers

    def test_display_name_and_address_are_split(self):
        provider = FakeMailProvider(
            [make_email("m1")],
        )
        provider.add(
            RawEmail(
                provider="fake",
                provider_message_id="m2",
                thread_id="t2",
                from_name="",
                from_email="",
                reply_to=None,
                to=[SELF_ADDRESS],
                subject="s",
                body_text="b",
                received_at=datetime(2026, 1, 1, tzinfo=UTC),
                headers={},
                is_from_self=False,
            )
        )
        from providers.fake import record_to_raw_email

        parsed = record_to_raw_email(
            {"id": "x", "headers": {"from": "Jane Doe <jane@acme.example.com>"}}
        )

        assert parsed.from_name == "Jane Doe"
        assert parsed.from_email == "jane@acme.example.com"

    def test_bare_address_without_a_display_name_parses(self):
        from providers.fake import record_to_raw_email

        parsed = record_to_raw_email({"id": "x", "headers": {"from": "jane@acme.example.com"}})

        assert parsed.from_email == "jane@acme.example.com"
        assert parsed.from_name == ""

    def test_is_from_self_is_set_for_our_own_address(self):
        from providers.fake import record_to_raw_email

        parsed = record_to_raw_email(
            {"id": "x", "headers": {"from": f"Us <{SELF_ADDRESS}>"}}, self_address=SELF_ADDRESS
        )

        assert parsed.is_from_self

    def test_expire_cursor_simulates_a_stale_history_id(self):
        provider = FakeMailProvider([make_email("m1")])
        _, cursor = provider.fetch_new(None)
        provider.expire_cursor()

        with pytest.raises(CursorExpiredError):
            provider.fetch_new(cursor)

    def test_records_what_the_pipeline_did(self):
        email = make_email("m1")
        provider = FakeMailProvider([email])

        provider.save_draft(make_draft(email))
        provider.apply_label("m1", LABEL_DRAFTED)

        assert len(provider.saved_drafts) == 1
        assert provider.labels_for("m1") == [LABEL_DRAFTED]
        assert provider.fetch_calls == []

    def test_creating_a_new_label_is_recorded(self):
        provider = FakeMailProvider([make_email("m1")])

        provider.apply_label("m1", "Something New")

        assert provider.created_labels == ["Something New"]

    def test_contract_labels_already_exist_and_are_not_recreated(self):
        provider = FakeMailProvider([make_email("m1")])

        provider.apply_label("m1", LABEL_DRAFTED)

        assert provider.created_labels == []


# ---------------------------------------------------------------------------
# Base class and registry
# ---------------------------------------------------------------------------


def test_base_provider_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseMailProvider()  # type: ignore[abstract]


def test_a_subclass_that_adds_a_send_method_is_refused_at_import_time():
    """Requirement 5. The mistake fails on class creation, not in code review."""
    with pytest.raises(TypeError, match="not allowed"):

        class Sneaky(BaseMailProvider):
            name = "sneaky"

            def fetch_new(self, cursor):
                return [], "0"

            def save_draft(self, content):
                raise NotImplementedError

            def apply_label(self, provider_message_id, label):
                pass

            def send(self, content):  # send-guard: allow (the line under test)
                raise NotImplementedError


def test_registry_resolves_the_fake():
    from providers.registry import get_provider

    assert get_provider("fake").name == "fake"


def test_registry_rejects_an_unknown_name():
    from providers.registry import get_provider_class

    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider_class("hotmail")


def test_registry_name_lookup_is_case_insensitive():
    from providers.registry import get_provider_class

    assert get_provider_class("FAKE") is FakeMailProvider


def test_resolving_one_provider_does_not_import_the_other(monkeypatch):
    """A machine running Outlook must not need the Google libraries installed."""
    import sys

    for module in ("providers.gmail", "providers.outlook"):
        monkeypatch.delitem(sys.modules, module, raising=False)

    from providers.registry import get_provider_class

    get_provider_class("fake")

    assert "providers.gmail" not in sys.modules
    assert "providers.outlook" not in sys.modules


def test_registry_lists_both_real_providers():
    from providers.registry import KNOWN_PROVIDERS

    assert {"gmail", "outlook"} <= set(KNOWN_PROVIDERS)

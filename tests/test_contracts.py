"""Tests for P0-01's contracts module.

These guard two things: that the shapes other tickets build against actually exist, and that
requirement 5 (draft only, never send) holds at the level of the interface itself. The repo-wide
send guard is a separate, broader test owned by P2-01.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest

from email_agent import contracts
from email_agent.contracts import (
    AuthResult,
    Candidate,
    Classification,
    DraftAttachment,
    DraftContent,
    EmailStatus,
    ExtractedFields,
    Intent,
    MailProvider,
    Match,
    PrefilterResult,
    Profile,
    RawEmail,
    Resume,
    SavedDraft,
    ValidationIssue,
    ValidationReport,
    VerificationResult,
)


def test_the_imports_named_in_the_ticket_work():
    """P0-01 acceptance criterion, stated literally."""
    from email_agent.contracts import DraftContent, MailProvider, RawEmail  # noqa: F401


# ---------- requirement 5: no send path ----------


def test_mail_provider_has_no_send_method():
    """The interface is the first of three places requirement 5 is enforced; the other two are
    the OAuth scopes (P0-05) and the repo-wide grep (P2-01)."""
    members = {name for name, _ in inspect.getmembers(MailProvider)}

    assert not any("send" in name.lower() for name in members), sorted(
        name for name in members if "send" in name.lower()
    )


def test_mail_provider_declares_exactly_the_contracted_methods():
    declared = {
        name
        for name, value in vars(MailProvider).items()
        if not name.startswith("_") and callable(value)
    }

    assert declared == {"fetch_new", "save_draft", "apply_label"}


def test_contracts_module_defines_no_send_function():
    source = Path(contracts.__file__).read_text(encoding="utf-8")

    assert "def send" not in source


def test_contracts_module_imports_nothing_from_the_rest_of_the_package():
    """contracts.py is the floor. If it imports a sibling, every ticket inherits that dependency
    and the independence guarantee in docs/TICKETS.md is gone."""
    source = Path(contracts.__file__).read_text(encoding="utf-8")

    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")):
            assert "email_agent" not in stripped, f"contracts.py must not import siblings: {stripped}"
            for sibling in ("providers", "pipeline", "profiles", "eval"):
                assert not stripped.startswith(f"from {sibling}"), stripped
                assert not stripped.startswith(f"import {sibling}"), stripped


# ---------- enums ----------


def test_intent_values_match_the_contract():
    assert {i.value for i in Intent} == {
        "new_requirement",
        "resume_request",
        "follow_up",
        "interview",
        "other",
    }


def test_auth_result_values_match_the_contract():
    assert {a.value for a in AuthResult} == {"pass", "fail", "unknown"}


def test_email_status_values_match_the_contract():
    assert {s.value for s in EmailStatus} == {
        "fetched",
        "skipped_bulk",
        "skipped_auth",
        "not_recruiter",
        "needs_review",
        "drafted",
    }


def test_enums_are_string_valued_so_they_serialise_straight_to_the_database():
    assert Intent.RESUME_REQUEST == "resume_request"
    assert AuthResult.FAIL == "fail"
    assert EmailStatus.DRAFTED == "drafted"


# ---------- dataclass shapes ----------

ALL_DATACLASSES = [
    RawEmail,
    VerificationResult,
    PrefilterResult,
    ExtractedFields,
    Classification,
    Candidate,
    Profile,
    Resume,
    Match,
    DraftAttachment,
    DraftContent,
    ValidationIssue,
    ValidationReport,
    SavedDraft,
]


@pytest.mark.parametrize("cls", ALL_DATACLASSES, ids=lambda c: c.__name__)
def test_every_contract_type_is_a_frozen_dataclass(cls: type):
    """Frozen throughout: a pipeline stage must not be able to quietly edit what an earlier
    stage produced."""
    assert dataclasses.is_dataclass(cls)
    assert cls.__dataclass_params__.frozen, f"{cls.__name__} is not frozen"


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        (
            RawEmail,
            [
                "provider",
                "provider_message_id",
                "thread_id",
                "from_name",
                "from_email",
                "reply_to",
                "to",
                "subject",
                "body_text",
                "received_at",
                "headers",
                "is_from_self",
            ],
        ),
        (VerificationResult, ["result", "spf", "dkim", "dmarc", "flags", "reason"]),
        (PrefilterResult, ["keep", "rule"]),
        (
            ExtractedFields,
            [
                "role",
                "skills",
                "min_years_experience",
                "location",
                "candidate_names",
                "resume_requested",
            ],
        ),
        (Classification, ["is_recruiter", "confidence", "intent", "fields", "model"]),
        (
            DraftContent,
            [
                "to",
                "subject",
                "body_text",
                "in_reply_to_message_id",
                "thread_id",
                "attachments",
                "profiles_used",
            ],
        ),
        (DraftAttachment, ["profile_id", "candidate_id", "file_path", "filename"]),
        (Match, ["profile_id", "candidate_id", "score", "reason", "stage", "selected"]),
        (SavedDraft, ["provider_draft_id", "thread_id"]),
    ],
    ids=lambda v: v.__name__ if isinstance(v, type) else "fields",
)
def test_field_names_and_order_match_the_contract(cls: type, expected: list[str]):
    assert [f.name for f in dataclasses.fields(cls)] == expected


def test_draft_attachment_carries_the_candidate_id():
    """The zero-wrong-resumes target depends on this: the validator (P2-10) checks ownership
    from this field, not from the filename."""
    names = {f.name for f in dataclasses.fields(DraftAttachment)}

    assert {"candidate_id", "profile_id"} <= names


def test_validation_report_defaults_to_no_issues():
    report = ValidationReport(ok=True)

    assert report.issues == ()


def test_profile_candidate_is_optional_so_a_profile_can_be_loaded_alone():
    profile = Profile(
        id=1,
        candidate_id=2,
        title="Senior Python Engineer",
        skills=["python", "fastapi"],
        years_experience=7.0,
        summary="Backend work on payments systems.",
        active=True,
    )

    assert profile.candidate is None


# ---------- construction smoke test ----------


def test_the_types_compose_into_a_full_pipeline_result():
    """Builds one of everything the way a real run would, so a shape change that breaks
    downstream construction fails here rather than in six other tickets."""
    email = RawEmail(
        provider="gmail",
        provider_message_id="msg-1",
        thread_id="thread-1",
        from_name="A Recruiter",
        from_email="recruiter@agency.example",
        reply_to=None,
        to=["us@example.com"],
        subject="Senior Python Engineer, Pune",
        body_text="Looking for 5+ years Python.",
        received_at=datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
        headers={"authentication-results": "spf=pass dkim=pass dmarc=pass"},
        is_from_self=False,
    )
    classification = Classification(
        is_recruiter=True,
        confidence=0.93,
        intent=Intent.NEW_REQUIREMENT,
        fields=ExtractedFields(
            role="Senior Python Engineer",
            skills=["python"],
            min_years_experience=5.0,
            location="Pune",
            candidate_names=[],
            resume_requested=False,
        ),
        model="qwen3:8b",
    )
    match = Match(
        profile_id=42, candidate_id=7, score=0.88, reason="7 yrs Python", stage="rerank", selected=True
    )
    draft = DraftContent(
        to=[email.from_email],
        subject=f"Re: {email.subject}",
        body_text="One strong match attached.",
        in_reply_to_message_id=email.provider_message_id,
        thread_id=email.thread_id,
        attachments=[
            DraftAttachment(
                profile_id=match.profile_id,
                candidate_id=match.candidate_id,
                file_path="resumes/x.pdf",
                filename="Someone_Senior_Python_Engineer.pdf",
            )
        ],
        profiles_used=[match.profile_id],
    )
    report = ValidationReport(
        ok=False, issues=(ValidationIssue(check="within_word_limit", detail="too long"),)
    )
    resume = Resume(
        id=1,
        profile_id=match.profile_id,
        file_path="resumes/x.pdf",
        version=1,
        uploaded_at=datetime(2026, 9, 1, tzinfo=UTC),
        is_current=True,
    )

    assert classification.intent is Intent.NEW_REQUIREMENT
    assert draft.to == [email.from_email]
    assert draft.attachments[0].candidate_id == match.candidate_id
    assert report.issues[0].check == "within_word_limit"
    assert resume.is_current

"""Tests for P2-05 the pre-filter.

Each rule gets a test that trips it and one that does not. The test that matters most is
``test_no_genuine_recruiter_email_is_dropped``: a false drop is the only outcome in the whole
pipeline that leaves no trace for a human — no label, no draft, nothing in the mailbox.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from email_agent.contracts import RawEmail
from pipeline.prefilter import RULE_IMPLEMENTATIONS, load_rules, prefilter

EXAMPLE_DATASET = Path(__file__).resolve().parent.parent / "eval" / "dataset" / "labels.example.jsonl"


def email(
    *,
    from_email: str = "priya@techbridge.example.com",
    subject: str = "Senior Python Engineer, Pune",
    body: str = "We are hiring. Are you available?",
    headers: dict[str, str] | None = None,
    is_from_self: bool = False,
) -> RawEmail:
    return RawEmail(
        provider="fake",
        provider_message_id="m1",
        thread_id="t1",
        from_name="Priya Sharma",
        from_email=from_email,
        reply_to=None,
        to=["us@example.com"],
        subject=subject,
        body_text=body,
        received_at=datetime(2026, 1, 1, tzinfo=UTC),
        headers={k.lower(): v for k, v in (headers or {}).items()},
        is_from_self=is_from_self,
    )


def dropped_by(mail: RawEmail) -> str | None:
    result = prefilter(mail)
    return None if result.keep else result.rule


# ---------------------------------------------------------------------------
# Kept: the case that matters
# ---------------------------------------------------------------------------


def test_an_ordinary_recruiter_email_is_kept():
    result = prefilter(email())

    assert result.keep
    assert result.rule is None


def test_no_genuine_recruiter_email_in_the_example_set_is_dropped():
    """Zero false drops. A dropped email is silently lost."""
    wrongly_dropped: list[tuple[str, str]] = []

    with open(EXAMPLE_DATASET, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if not record["is_recruiter"]:
                continue
            headers = record.get("headers") or {}
            raw_from = headers.get("from", "")
            if "<" in raw_from:
                address = raw_from[raw_from.index("<") + 1 : raw_from.rindex(">")]
            else:
                address = raw_from
            rule = dropped_by(
                email(
                    from_email=address,
                    subject=record.get("subject", ""),
                    body=record.get("body_text", ""),
                    headers=headers,
                )
            )
            if rule:
                wrongly_dropped.append((record["id"], rule))

    assert not wrongly_dropped, f"recruiter emails dropped: {wrongly_dropped}"


def test_the_word_unsubscribe_in_the_body_does_not_drop_an_email():
    """Only the header counts. Plenty of legitimate signatures mention unsubscribing."""
    result = prefilter(
        email(body="We are hiring.\n\nTo unsubscribe from our updates, reply STOP.")
    )

    assert result.keep


def test_a_recruiter_email_mentioning_a_job_alert_is_kept():
    result = prefilter(
        email(subject="Following up on the job alert you saw", body="Are you interested?")
    )

    assert result.keep


def test_substring_matching_on_subjects_is_deliberate():
    """Documents the deliberate choice of substring matching: 'Automatic Reply' in a subject
    drops the email even mid-sentence, because a human never writes that phrase in a real
    subject line. Recorded so the behaviour is intentional rather than surprising."""
    assert dropped_by(email(subject="Automatic reply: Senior Python Engineer")) == "out_of_office"


# ---------------------------------------------------------------------------
# Every rule: trips and does not trip
# ---------------------------------------------------------------------------


def test_our_own_sent_mail_is_dropped():
    assert dropped_by(email(is_from_self=True)) == "own_mail"


def test_mail_not_from_us_is_not_dropped_by_that_rule():
    assert dropped_by(email(is_from_self=False)) != "own_mail"


@pytest.mark.parametrize("header", ["list-unsubscribe", "list-unsubscribe-post"])
def test_list_unsubscribe_header_is_dropped(header: str):
    assert dropped_by(email(headers={header: "<mailto:x@y.com>"})) == "list_unsubscribe"


def test_an_empty_list_unsubscribe_header_does_not_drop():
    assert prefilter(email(headers={"list-unsubscribe": "   "})).keep


@pytest.mark.parametrize("header", ["list-id", "list-post", "list-help"])
def test_mailing_list_headers_are_dropped(header: str):
    assert dropped_by(email(headers={header: "<list.example.com>"})) == "list_id"


@pytest.mark.parametrize("value", ["bulk", "list", "junk", "BULK"])
def test_precedence_bulk_is_dropped(value: str):
    assert dropped_by(email(headers={"precedence": value})) == "precedence_bulk"


def test_precedence_normal_is_not_dropped():
    assert prefilter(email(headers={"precedence": "normal"})).keep


@pytest.mark.parametrize("value", ["auto-generated", "auto-replied", "auto-notified"])
def test_auto_submitted_other_than_no_is_dropped(value: str):
    assert dropped_by(email(headers={"auto-submitted": value})) == "auto_submitted"


def test_auto_submitted_no_is_kept():
    """RFC 3834: 'no' is what ordinary human mail carries."""
    assert prefilter(email(headers={"auto-submitted": "no"})).keep


def test_auto_submitted_with_parameters_is_parsed():
    assert dropped_by(
        email(headers={"auto-submitted": "auto-generated; owner@example.com"})
    ) == "auto_submitted"


@pytest.mark.parametrize("header", ["x-autoreply", "x-autorespond", "x-auto-response-suppress"])
def test_autoreply_headers_are_dropped(header: str):
    assert dropped_by(email(headers={header: "yes"})) == "autoreply_header"


@pytest.mark.parametrize("sender", ["mailer-daemon@x.example.com", "postmaster@x.example.com"])
def test_bounce_senders_are_dropped(sender: str):
    assert dropped_by(email(from_email=sender)) in {"delivery_failure", "noreply_sender"}


@pytest.mark.parametrize(
    "subject",
    [
        "Undelivered Mail Returned to Sender",
        "Delivery Status Notification (Failure)",
        "Mail delivery failed: returning message to sender",
        "Undeliverable: Senior Python Engineer",
    ],
)
def test_delivery_failure_subjects_are_dropped(subject: str):
    assert dropped_by(email(subject=subject)) == "delivery_failure"


@pytest.mark.parametrize(
    "subject",
    [
        "Out of Office",
        "Automatic reply: your message",
        "Auto-Reply from Priya",
        "I am on annual leave until Monday",
    ],
)
def test_out_of_office_subjects_are_dropped(subject: str):
    assert dropped_by(email(subject=subject)) == "out_of_office"


def test_a_reply_prefix_does_not_hide_an_out_of_office():
    assert dropped_by(email(subject="Re: Out of Office")) == "out_of_office"


def test_a_normal_subject_is_not_dropped():
    assert prefilter(email(subject="Python role in Pune, 5 years")).keep


@pytest.mark.parametrize(
    "sender",
    [
        "noreply@jobboard.example.com",
        "no-reply@jobboard.example.com",
        "donotreply@jobboard.example.com",
        "bounces@jobboard.example.com",
    ],
)
def test_noreply_senders_are_dropped(sender: str):
    assert dropped_by(email(from_email=sender)) == "noreply_sender"


@pytest.mark.parametrize(
    "sender",
    [
        "jobs-listings@jobboard.example.com",
        "jobalerts@jobboard.example.com",
        "newsletter@techdigest.example.com",
        "alerts@jobboard.example.com",
        "linkedin-jobalert@jobboard.example.com",
    ],
)
def test_job_alert_senders_are_dropped(sender: str):
    assert dropped_by(email(from_email=sender)) == "job_alert_sender"


@pytest.mark.parametrize(
    "sender",
    [
        "alerta@agency.example.com",
        "jobsmith@agency.example.com",
        "alertness@agency.example.com",
        "newsletterexpert@agency.example.com",
    ],
)
def test_a_local_part_that_merely_contains_a_keyword_is_kept(sender: str):
    """'jobsmith' is a person's name, not a job-alert robot. Matching on a bare substring would
    drop them."""
    assert prefilter(email(from_email=sender)).keep


def test_a_real_recruiter_at_a_job_board_domain_is_kept():
    """The domain is not the signal; the sending mailbox is."""
    assert prefilter(email(from_email="priya.sharma@jobboard.example.com")).keep


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_every_ordered_rule_has_an_implementation():
    rules = load_rules()

    missing = [name for name in rules.order if name not in RULE_IMPLEMENTATIONS]

    assert not missing, f"configured but not implemented: {missing}"


def test_rules_load_from_yaml_and_a_sender_can_be_added_without_code(tmp_path: Path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "order: [job_alert_sender]\n"
        "rules:\n"
        "  job_alert_sender:\n"
        "    enabled: true\n"
        "    local_parts: []\n"
        "    addresses: [spammer@agency.example.com]\n"
        "    domains: []\n",
        encoding="utf-8",
    )

    result = prefilter(email(from_email="spammer@agency.example.com"), rules_path=str(path))

    assert not result.keep
    assert result.rule == "job_alert_sender"


def test_a_whole_domain_can_be_dropped_from_config(tmp_path: Path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "order: [job_alert_sender]\n"
        "rules:\n"
        "  job_alert_sender:\n"
        "    enabled: true\n"
        "    local_parts: []\n"
        "    addresses: []\n"
        "    domains: [spamboard.example.com]\n",
        encoding="utf-8",
    )

    assert not prefilter(
        email(from_email="anyone@spamboard.example.com"), rules_path=str(path)
    ).keep


def test_a_disabled_rule_is_skipped(tmp_path: Path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "order: [list_unsubscribe]\n"
        "rules:\n"
        "  list_unsubscribe:\n"
        "    enabled: false\n"
        "    headers: [list-unsubscribe]\n",
        encoding="utf-8",
    )

    assert prefilter(
        email(headers={"list-unsubscribe": "<mailto:x@y.com>"}), rules_path=str(path)
    ).keep


def test_order_naming_an_unknown_rule_is_rejected_at_load(tmp_path: Path):
    path = tmp_path / "rules.yaml"
    path.write_text("order: [nonexistent]\nrules:\n  list_id:\n    enabled: true\n", encoding="utf-8")

    with pytest.raises(ValueError, match="do not exist"):
        load_rules(str(path))


def test_a_configured_rule_with_no_implementation_raises(tmp_path: Path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "order: [made_up_rule]\nrules:\n  made_up_rule:\n    enabled: true\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="not implemented"):
        prefilter(email(), rules_path=str(path))


def test_a_missing_rules_file_raises():
    with pytest.raises(FileNotFoundError):
        load_rules("does/not/exist.yaml")


def test_first_matching_rule_wins_in_configured_order():
    """Both own_mail and list_unsubscribe apply; own_mail is ordered first."""
    result = prefilter(email(is_from_self=True, headers={"list-unsubscribe": "<mailto:x@y>"}))

    assert result.rule == "own_mail"


def test_every_drop_names_its_rule():
    """A drop with no rule name cannot be diagnosed from the log."""
    cases = [
        email(is_from_self=True),
        email(headers={"list-unsubscribe": "<x>"}),
        email(headers={"precedence": "bulk"}),
        email(subject="Out of Office"),
        email(from_email="noreply@x.example.com"),
    ]

    for case in cases:
        result = prefilter(case)

        assert not result.keep
        assert result.rule
        assert result.rule in RULE_IMPLEMENTATIONS


def test_result_is_immutable():
    import dataclasses

    result = prefilter(email())

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.keep = False  # type: ignore[misc]


def test_the_module_makes_no_network_or_model_calls():
    source = (Path(__file__).resolve().parent.parent / "pipeline" / "prefilter.py").read_text(
        encoding="utf-8"
    )

    for forbidden in ("requests", "httpx", "urllib", "socket", "ollama", "psycopg"):
        assert f"import {forbidden}" not in source


# ---------------------------------------------------------------------------
# campaign_subdomain: bulk-mail plumbing in the sending domain
#
# Added after two Nippon Life marketing emails reached the model from a real inbox. They carry
# no List-Unsubscribe, no List-Id and no Precedence header, so every header rule missed them.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "address",
    [
        "nimfupdates@campaign1.nipponindia.email",   # the real one, verbatim
        "news@campaign.brand.com",
        "x@campaigns.brand.com",
        "x@mailer2.brand.com",
        "x@sendgrid.brand.com",
        "x@newsletter.brand.com",
    ],
)
def test_campaign_subdomains_are_dropped(address):
    assert dropped_by(email(from_email=address)) == "campaign_subdomain"


@pytest.mark.parametrize(
    "address",
    [
        # The whole point of matching the leftmost label only: these are real senders.
        "priya@mail.agency.com",         # a small agency's own mail host
        "priya@email.agency.com",
        "priya@campaignmonitor.com",     # the label is not `campaign`
        "priya@agency.com",
        "priya@jobs.agency.com",
        "campaign@agency.com",           # local part, not the domain label
        "priya@recruiting.campaignco.com",
    ],
)
def test_real_senders_are_not_dropped_by_the_subdomain_rule(address):
    assert dropped_by(email(from_email=address)) != "campaign_subdomain"


def test_the_rule_needs_an_actual_subdomain():
    """A bare two-label domain has no sending subdomain to judge."""
    assert dropped_by(email(from_email="x@campaign.com")) != "campaign_subdomain"


def test_a_two_part_suffix_domain_is_not_mistaken_for_a_subdomain():
    """`campaign.co.uk` is a registrable domain, not plumbing under someone else's."""
    assert dropped_by(email(from_email="x@campaign.co.uk")) != "campaign_subdomain"
    assert dropped_by(email(from_email="x@campaign1.agency.co.uk")) == "campaign_subdomain"

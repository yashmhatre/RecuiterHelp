"""Tests for P2-04 sender verification.

This stage is the reason a spoofed sender never reaches a model, so the tests lean hard on the
directions in which being wrong is expensive: a FAIL that reads as PASS, and a forged header
that buys a pass.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from email_agent.contracts import AuthResult, RawEmail
from pipeline.verify import (
    FLAG_DISPLAY_NAME_MISMATCH,
    FLAG_FREEMAIL_CLAIMS_COMPANY,
    FLAG_LOOKALIKE_DOMAIN,
    FLAG_NO_AUTH_HEADER,
    FLAG_REPLY_TO_MISMATCH,
    FLAG_UNTRUSTED_AUTH_HEADER,
    domain_of,
    load_freemail_domains,
    verify,
)

ALL_PASS = (
    "mx.ourcompany.com; spf=pass smtp.mailfrom=agency.example.com; "
    "dkim=pass header.d=agency.example.com; dmarc=pass header.from=agency.example.com"
)


def email(
    *,
    auth: str | None = ALL_PASS,
    from_email: str = "jane@agency.example.com",
    from_name: str = "Jane Doe",
    reply_to: str | None = None,
    body: str = "We have an opening for a Python engineer.",
    extra_headers: dict[str, str] | None = None,
) -> RawEmail:
    headers: dict[str, str] = {}
    if auth is not None:
        headers["authentication-results"] = auth
    headers.update(extra_headers or {})
    return RawEmail(
        provider="fake",
        provider_message_id="m1",
        thread_id="t1",
        from_name=from_name,
        from_email=from_email,
        reply_to=reply_to,
        to=["us@example.com"],
        subject="Senior Python Engineer",
        body_text=body,
        received_at=datetime(2026, 1, 1, tzinfo=UTC),
        headers=headers,
        is_from_self=False,
    )


# ---------------------------------------------------------------------------
# The three-way verdict
# ---------------------------------------------------------------------------


def test_all_three_passing_gives_pass():
    result = verify(email())

    assert result.result is AuthResult.PASS
    assert (result.spf, result.dkim, result.dmarc) == ("pass", "pass", "pass")
    assert result.flags == ()


@pytest.mark.parametrize("method", ["spf", "dkim", "dmarc"])
def test_any_single_failure_gives_fail(method: str):
    auth = ALL_PASS.replace(f"{method}=pass", f"{method}=fail")

    result = verify(email(auth=auth))

    assert result.result is AuthResult.FAIL
    assert method in result.reason


@pytest.mark.parametrize("value", ["fail", "softfail", "neutral", "permerror", "temperror"])
def test_non_passing_spf_values_all_fail(value: str):
    auth = ALL_PASS.replace("spf=pass", f"spf={value}")

    assert verify(email(auth=auth)).result is AuthResult.FAIL


def test_missing_header_is_unknown_never_pass():
    """The single most costly mistake this module could make."""
    result = verify(email(auth=None))

    assert result.result is AuthResult.UNKNOWN
    assert FLAG_NO_AUTH_HEADER in result.flags
    assert "could not be verified" in result.reason


def test_empty_header_is_unknown():
    assert verify(email(auth="")).result is AuthResult.UNKNOWN


def test_header_missing_dmarc_is_unknown_not_pass():
    """Two of three passing is not authentication. DMARC is the one that ties From to the rest."""
    auth = "mx.ourcompany.com; spf=pass; dkim=pass"

    result = verify(email(auth=auth))

    assert result.result is AuthResult.UNKNOWN
    assert "dmarc" in result.reason


def test_unparseable_header_is_unknown():
    result = verify(email(auth="mx.ourcompany.com; something entirely unexpected"))

    assert result.result is AuthResult.UNKNOWN


def test_parsing_is_case_insensitive():
    assert verify(email(auth=ALL_PASS.upper())).result is AuthResult.PASS


def test_whitespace_around_equals_is_tolerated():
    auth = "mx.ourcompany.com; spf = pass; dkim = pass; dmarc = pass"

    assert verify(email(auth=auth)).result is AuthResult.PASS


# ---------------------------------------------------------------------------
# Forged headers
# ---------------------------------------------------------------------------


def test_a_forged_header_from_another_domain_cannot_buy_a_pass():
    """Anyone can add an Authentication-Results line to a message they send or forward. Only our
    own receiving service's verdict counts."""
    forged = "attacker.example.com; spf=pass; dkim=pass; dmarc=pass"

    result = verify(email(auth=forged), trusted_authserv=["ourcompany.com"])

    assert result.result is AuthResult.UNKNOWN
    assert FLAG_UNTRUSTED_AUTH_HEADER in result.flags


def test_our_own_header_is_used_when_several_are_present():
    ours = "mx.ourcompany.com; spf=fail; dkim=fail; dmarc=fail"
    forged = "attacker.example.com; spf=pass; dkim=pass; dmarc=pass"

    result = verify(
        email(auth=f"{forged}\n{ours}"), trusted_authserv=["ourcompany.com"]
    )

    assert result.result is AuthResult.FAIL, "the forged PASS must not win"


def test_discarding_an_untrusted_header_is_flagged_even_when_the_verdict_passes():
    ours = "mx.ourcompany.com; spf=pass; dkim=pass; dmarc=pass"
    upstream = "relay.elsewhere.example.com; spf=pass; dkim=pass; dmarc=pass"

    result = verify(email(auth=f"{upstream}\n{ours}"), trusted_authserv=["ourcompany.com"])

    assert result.result is AuthResult.PASS
    assert FLAG_UNTRUSTED_AUTH_HEADER in result.flags


def test_subdomain_of_a_trusted_authserv_is_trusted():
    auth = "mx1.mail.ourcompany.com; spf=pass; dkim=pass; dmarc=pass"

    assert verify(email(auth=auth), trusted_authserv=["ourcompany.com"]).result is AuthResult.PASS


def test_with_no_trusted_authserv_configured_the_topmost_header_is_used():
    """Single-hop mailbox: our server's header is the first one."""
    ours = "mx.ourcompany.com; spf=pass; dkim=pass; dmarc=pass"
    older = "relay.example.com; spf=fail; dkim=fail; dmarc=fail"

    assert verify(email(auth=f"{ours}\n{older}")).result is AuthResult.PASS


# ---------------------------------------------------------------------------
# Impersonation flags: one positive and one negative each
# ---------------------------------------------------------------------------


def test_reply_to_on_a_different_domain_is_flagged():
    result = verify(email(reply_to="collect@elsewhere.example.net"))

    assert FLAG_REPLY_TO_MISMATCH in result.flags


def test_reply_to_on_the_same_domain_is_not_flagged():
    result = verify(email(reply_to="jane.doe@agency.example.com"))

    assert FLAG_REPLY_TO_MISMATCH not in result.flags


def test_reply_to_on_a_subdomain_is_not_flagged():
    result = verify(email(reply_to="jane@mail.agency.example.com"))

    assert FLAG_REPLY_TO_MISMATCH not in result.flags


def test_absent_reply_to_is_not_flagged():
    assert FLAG_REPLY_TO_MISMATCH not in verify(email(reply_to=None)).flags


def test_freemail_sender_claiming_a_company_is_flagged():
    result = verify(
        email(
            from_email="jane.recruiter@gmail.com",
            from_name="Jane Doe",
            body="Regards,\nJane Doe\nSenior Consultant\nAcme Staffing Solutions Pvt Ltd",
            auth=ALL_PASS.replace("agency.example.com", "gmail.com"),
        )
    )

    assert FLAG_FREEMAIL_CLAIMS_COMPANY in result.flags


def test_freemail_sender_with_no_company_claim_is_not_flagged():
    """An independent recruiter on Gmail is ordinary, not suspicious."""
    result = verify(
        email(
            from_email="jane@gmail.com",
            from_name="Jane Doe",
            body="Hi, are you open to a Python role? Thanks, Jane",
            auth=ALL_PASS.replace("agency.example.com", "gmail.com"),
        )
    )

    assert FLAG_FREEMAIL_CLAIMS_COMPANY not in result.flags


def test_company_domain_sender_claiming_that_company_is_not_flagged():
    result = verify(
        email(
            from_email="jane@acmestaffing.example.com",
            body="Regards,\nJane\nAcme Staffing Solutions",
            auth=ALL_PASS.replace("agency.example.com", "acmestaffing.example.com"),
        )
    )

    assert FLAG_FREEMAIL_CLAIMS_COMPANY not in result.flags


def test_company_named_in_the_display_name_that_is_not_the_sending_domain_is_flagged():
    result = verify(
        email(from_name="Jane Doe (Globex Corp)", from_email="jane@unrelated.example.org",
              auth=ALL_PASS.replace("agency.example.com", "unrelated.example.org"))
    )

    assert FLAG_DISPLAY_NAME_MISMATCH in result.flags


def test_company_named_in_the_display_name_matching_the_domain_is_not_flagged():
    result = verify(
        email(from_name="Jane Doe (Globex)", from_email="jane@globex.example.com",
              auth=ALL_PASS.replace("agency.example.com", "globex.example.com"))
    )

    assert FLAG_DISPLAY_NAME_MISMATCH not in result.flags


def test_a_plain_display_name_is_not_flagged():
    assert FLAG_DISPLAY_NAME_MISMATCH not in verify(email(from_name="Jane Doe")).flags


def test_a_confusable_lookalike_domain_is_flagged():
    """rnicrosoft.com reads as microsoft.com at a glance."""
    result = verify(
        email(from_email="hr@rnicrosoft.com", auth=ALL_PASS.replace("agency.example.com", "rnicrosoft.com")),
        known_domains=["microsoft.com"],
    )

    assert FLAG_LOOKALIKE_DOMAIN in result.flags


def test_a_one_character_typo_domain_is_flagged():
    result = verify(
        email(from_email="hr@agencv.example.com",
              auth=ALL_PASS.replace("agency.example.com", "agencv.example.com")),
        known_domains=["agency.example.com"],
    )

    assert FLAG_LOOKALIKE_DOMAIN in result.flags


def test_an_exactly_known_domain_is_not_flagged():
    result = verify(email(), known_domains=["agency.example.com"])

    assert FLAG_LOOKALIKE_DOMAIN not in result.flags


def test_a_clearly_different_domain_is_not_flagged():
    result = verify(
        email(from_email="hr@totallyunrelated.example.io",
              auth=ALL_PASS.replace("agency.example.com", "totallyunrelated.example.io")),
        known_domains=["agency.example.com", "microsoft.com"],
    )

    assert FLAG_LOOKALIKE_DOMAIN not in result.flags


def test_no_known_domains_means_no_lookalike_flag():
    assert FLAG_LOOKALIKE_DOMAIN not in verify(email(), known_domains=[]).flags


# ---------------------------------------------------------------------------
# Combination and reporting
# ---------------------------------------------------------------------------


def test_a_genuine_recruiter_on_a_company_domain_raises_nothing():
    """The false-positive case. Flags on ordinary mail would train the reviewer to ignore them."""
    result = verify(
        email(
            from_email="priya@techbridge.example.com",
            from_name="Priya Sharma",
            reply_to="priya@techbridge.example.com",
            body="Hi,\n\nWe are hiring a senior Python engineer in Pune.\n\nRegards,\nPriya",
            auth=ALL_PASS.replace("agency.example.com", "techbridge.example.com"),
        ),
        trusted_authserv=["ourcompany.com"],
        known_domains=["techbridge.example.com", "agency.example.com"],
    )

    assert result.result is AuthResult.PASS
    assert result.flags == ()


def test_flags_are_reported_even_when_authentication_passes():
    """A domain can authenticate perfectly and still be an impersonation attempt."""
    result = verify(email(reply_to="collect@elsewhere.example.net"))

    assert result.result is AuthResult.PASS
    assert FLAG_REPLY_TO_MISMATCH in result.flags
    assert "Flagged anyway" in result.reason


def test_several_flags_are_all_reported():
    result = verify(
        email(
            from_email="jane@gmail.com",
            from_name="Jane Doe",
            reply_to="collect@elsewhere.example.net",
            body="Regards,\nJane\nAcme Recruitment Services Ltd",
            auth=ALL_PASS.replace("agency.example.com", "gmail.com"),
        )
    )

    assert FLAG_REPLY_TO_MISMATCH in result.flags
    assert FLAG_FREEMAIL_CLAIMS_COMPANY in result.flags


def test_flags_are_also_reported_on_a_failure():
    result = verify(
        email(auth=ALL_PASS.replace("dkim=pass", "dkim=fail"),
              reply_to="collect@elsewhere.example.net")
    )

    assert result.result is AuthResult.FAIL
    assert FLAG_REPLY_TO_MISMATCH in result.flags


def test_reason_is_always_a_non_empty_one_liner():
    """The reviewer reads this in the mailbox, so it has to stand alone."""
    for case in (email(), email(auth=None), email(auth=ALL_PASS.replace("spf=pass", "spf=fail"))):
        reason = verify(case).reason

        assert reason
        assert "\n" not in reason


def test_result_is_immutable():
    import dataclasses

    result = verify(email())

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.result = AuthResult.PASS  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("jane@acme.com", "acme.com"),
        ("Jane@ACME.COM", "acme.com"),
        ("jane@mail.acme.co.in", "mail.acme.co.in"),
        ("", ""),
        (None, ""),
        ("not-an-address", ""),
    ],
)
def test_domain_of(address, expected):
    assert domain_of(address) == expected


def test_freemail_list_loads_and_covers_the_obvious_providers():
    domains = load_freemail_domains()

    assert {"gmail.com", "outlook.com", "yahoo.com", "rediffmail.com"} <= domains


def test_freemail_list_ignores_comments_and_blanks(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("# comment\n\ngmail.com\n  yahoo.com  # trailing\n", encoding="utf-8")

    domains = load_freemail_domains(str(path))

    assert domains == {"gmail.com", "yahoo.com"}


def test_the_module_makes_no_network_or_model_calls():
    """Pure function over headers. Nothing here may become slow or flaky."""
    import pathlib

    from tests.test_no_send_path import find_send_paths

    source = pathlib.Path("pipeline/verify.py").read_text(encoding="utf-8")

    assert find_send_paths(source, "verify.py") == []
    for forbidden in ("requests", "httpx", "urllib", "socket", "ollama", "psycopg"):
        assert f"import {forbidden}" not in source

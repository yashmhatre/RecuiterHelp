"""Cheap deterministic rules that drop obvious non-mail before a model is ever loaded.

Two things shape this module.

First, **every drop records its rule name**. A dropped email produces no label, no draft and
nothing for a human to see, so it is the one outcome in the pipeline that is invisible by
default. If a genuine recruiter email goes missing, the log has to say which rule ate it.

Second, **when in doubt, keep**. The metric for this stage is zero false drops on genuine
recruiter mail, not how much bulk it catches. Deciding whether an email is really from a
recruiter is the model's job in P2-06; this stage only removes mail that is bulk or automated by
construction — a ``List-Unsubscribe`` header, a bounce, an out-of-office.

Rules live in ``config/prefilter_rules.yaml`` so P3-03 can tune them without a code change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from email_agent.contracts import PrefilterResult, RawEmail

__all__ = ["prefilter", "load_rules", "PrefilterRules", "DEFAULT_RULES_PATH"]

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES_PATH = REPO_ROOT / "config" / "prefilter_rules.yaml"


@dataclass(frozen=True)
class PrefilterRules:
    order: tuple[str, ...]
    rules: dict[str, dict[str, Any]]

    def config(self, name: str) -> dict[str, Any]:
        return self.rules.get(name, {})

    def enabled(self, name: str) -> bool:
        return bool(self.config(name).get("enabled", False))


@lru_cache(maxsize=4)
def load_rules(path: str | None = None) -> PrefilterRules:
    """Load and cache the rule file."""
    target = Path(path) if path else DEFAULT_RULES_PATH
    if not target.is_file():
        raise FileNotFoundError(f"Prefilter rules not found: {target}")

    loaded = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{target} must contain a mapping")

    rules = loaded.get("rules") or {}
    order = tuple(loaded.get("order") or rules.keys())

    unknown = [name for name in order if name not in rules]
    if unknown:
        raise ValueError(
            f"{target}: 'order' names rules that do not exist: {', '.join(unknown)}"
        )

    return PrefilterRules(order=order, rules=rules)


# ---------------------------------------------------------------------------
# Individual rules. Each returns True when the email should be dropped.
# ---------------------------------------------------------------------------


def _lowered(values: Any) -> set[str]:
    """Lower-cased string set from a YAML list.

    Coerces via ``str`` because YAML turns bare words into other types: `no` becomes the boolean
    false, `null` becomes None, and a bare `8` becomes an int. This file is hand-edited during
    P3-03 tuning, so a stray unquoted value must not crash the pipeline.
    """
    return {str(v).strip().lower() for v in (values or [])}


def _local_part(address: str | None) -> str:
    if not address or "@" not in address:
        return (address or "").strip().lower()
    return address.rsplit("@", 1)[0].strip().lower()


def _domain(address: str | None) -> str:
    if not address or "@" not in address:
        return ""
    return address.rsplit("@", 1)[1].strip().lower()


def _has_any_header(email: RawEmail, names: list[str]) -> bool:
    return any(email.headers.get(name.lower(), "").strip() for name in names)


def _rule_own_mail(email: RawEmail, _: dict[str, Any]) -> bool:
    return email.is_from_self


def _rule_headers_present(email: RawEmail, config: dict[str, Any]) -> bool:
    return _has_any_header(email, config.get("headers", []))


def _rule_header_value_in(email: RawEmail, config: dict[str, Any]) -> bool:
    value = email.headers.get(config.get("header", ""), "").strip().lower()
    return bool(value) and value in _lowered(config.get("values", []))


def _rule_header_value_not_in(email: RawEmail, config: dict[str, Any]) -> bool:
    """For Auto-Submitted: anything other than 'no' means machine-generated (RFC 3834)."""
    value = email.headers.get(config.get("header", ""), "").strip().lower()
    if not value:
        return False
    # "auto-generated; owner@example.com" -> "auto-generated"
    value = value.split(";", 1)[0].strip()
    return value not in _lowered(config.get("allowed", []))


def _rule_delivery_failure(email: RawEmail, config: dict[str, Any]) -> bool:
    local = _local_part(email.from_email)
    if local in _lowered(config.get("senders", [])):
        return True
    return _subject_matches(email.subject, config.get("subject_patterns", []))


def _rule_subject_patterns(email: RawEmail, config: dict[str, Any]) -> bool:
    return _subject_matches(email.subject, config.get("subject_patterns", []))


def _subject_matches(subject: str, patterns: list[str]) -> bool:
    """Match a pattern anywhere in the subject, after stripping reply and forward prefixes.

    Substring rather than regex: the patterns are edited by whoever tunes thresholds, and a
    broken regex there would be a silent change in behaviour.
    """
    cleaned = re.sub(r"^\s*(re|fw|fwd|aw|antw)\s*:\s*", "", subject or "", flags=re.IGNORECASE)
    cleaned = cleaned.strip().lower()
    return any(p.lower() in cleaned for p in patterns if p)


def _rule_sender_local_part(email: RawEmail, config: dict[str, Any]) -> bool:
    local = _local_part(email.from_email)
    if not local:
        return False

    for candidate in config.get("local_parts", []):
        candidate = candidate.lower()
        # Exact, or a separated segment: "jobs-listings@" and "linkedin-jobalerts@" both match,
        # while "jobsmith@" does not.
        if local == candidate or re.search(rf"(^|[._+-]){re.escape(candidate)}([._+-]|$)", local):
            return True

    address = (email.from_email or "").strip().lower()
    if address and address in _lowered(config.get("addresses", [])):
        return True

    domain = _domain(email.from_email)
    return bool(domain) and domain in _lowered(config.get("domains", []))


#: Two-part public suffixes common in this client's mail. Not the full PSL -- pulling in a
#: dependency to shave one edge case is not worth it, and an unlisted suffix fails safe by
#: keeping the email.
TWO_PART_SUFFIXES = frozenset({
    "co.uk", "org.uk", "ac.uk", "co.in", "net.in", "org.in", "com.au", "co.nz",
    "co.za", "com.sg", "com.br", "co.jp",
})


def _rule_campaign_subdomain(email: RawEmail, config: dict[str, Any]) -> bool:
    """Match on the sending domain's leftmost label when that label is bulk-mail plumbing.

    `nimfupdates@campaign1.nipponindia.email` carries no List-Unsubscribe, no List-Id and no
    Precedence header, so every header rule misses it, and the local part `nimfupdates` does not
    match `updates` because local parts match whole segments -- which is correct, since a
    substring match is how a real agency gets falsely dropped.

    The subdomain is the honest signal. Nobody's recruiter writes to them personally from
    `campaign1.`; that label exists because an ESP put it there to keep campaign traffic off
    the corporate domain's reputation. Matched on the leftmost label only, and only against
    labels that are purely infrastructure: `mail.` and `email.` are deliberately NOT in the
    list, because a small agency plausibly does send its real mail from `mail.agency.com`.
    """
    domain = _domain(email.from_email)
    if not domain:
        return False

    labels = domain.split(".")
    # There must be a label to the LEFT of the registrable domain, or we would be judging the
    # company name itself: `campaign.com` is somebody's actual business, `campaign1.x.com` is
    # plumbing. Two-part public suffixes push the boundary out by one.
    required = 4 if len(labels) >= 2 and ".".join(labels[-2:]) in TWO_PART_SUFFIXES else 3
    if len(labels) < required:
        return False

    label = labels[0]
    # A trailing shard number is part of the naming convention: campaign1, campaign2, em3.
    label = re.sub(r"\d+$", "", label)
    return bool(label) and label in _lowered(config.get("labels", []))


#: Rule name -> implementation. A rule in the YAML with no implementation here is a
#: configuration error, caught at load time by ``prefilter``.
RULE_IMPLEMENTATIONS = {
    "own_mail": _rule_own_mail,
    "list_unsubscribe": _rule_headers_present,
    "list_id": _rule_headers_present,
    "precedence_bulk": _rule_header_value_in,
    "auto_submitted": _rule_header_value_not_in,
    "autoreply_header": _rule_headers_present,
    "delivery_failure": _rule_delivery_failure,
    "out_of_office": _rule_subject_patterns,
    "noreply_sender": _rule_sender_local_part,
    "job_alert_sender": _rule_sender_local_part,
    "transactional_sender": _rule_sender_local_part,
    "campaign_subdomain": _rule_campaign_subdomain,
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def prefilter(email: RawEmail, *, rules_path: str | None = None) -> PrefilterResult:
    """Decide whether an email is worth putting through the rest of the pipeline.

    Returns ``keep=False`` with the name of the rule that dropped it, or ``keep=True`` with
    ``rule=None``. Evaluates in the configured order and stops at the first match.
    """
    rules = load_rules(rules_path)

    for name in rules.order:
        if not rules.enabled(name):
            continue
        implementation = RULE_IMPLEMENTATIONS.get(name)
        if implementation is None:
            raise ValueError(
                f"Prefilter rule {name!r} is configured but not implemented. "
                f"Known rules: {', '.join(sorted(RULE_IMPLEMENTATIONS))}"
            )
        if implementation(email, rules.config(name)):
            return PrefilterResult(keep=False, rule=name)

    return PrefilterResult(keep=True, rule=None)

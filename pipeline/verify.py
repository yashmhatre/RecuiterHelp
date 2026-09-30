"""Sender authentication and impersonation flags.

Requirement 6 in code: an email whose sender cannot be authenticated never gets a draft. Pure
function over headers — no network, no model, no database — so it is cheap, deterministic and
exhaustively testable.

This stage runs **before** any model call. A spoofed sender must not reach a model at all, both
because there is nothing useful to extract from it and because a hostile body should get as few
chances to be interpreted as possible.

What this module does not do
----------------------------
It does not decide what happens next. It returns a ``VerificationResult`` and the orchestrator
(P2-12) maps ``FAIL`` and ``UNKNOWN`` to the "Needs review" label with no draft. Keeping the
decision in one place is why every stage here returns a result instead of acting on it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from functools import lru_cache
from pathlib import Path

from email_agent.contracts import AuthResult, RawEmail, VerificationResult

__all__ = [
    "verify",
    "load_freemail_domains",
    "domain_of",
    "FLAG_REPLY_TO_MISMATCH",
    "FLAG_FREEMAIL_CLAIMS_COMPANY",
    "FLAG_DISPLAY_NAME_MISMATCH",
    "FLAG_LOOKALIKE_DOMAIN",
    "FLAG_NO_AUTH_HEADER",
    "FLAG_UNTRUSTED_AUTH_HEADER",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
FREEMAIL_PATH = REPO_ROOT / "config" / "freemail_domains.txt"

# Flag names. Stable strings: they are stored on the email row and read by a human reviewer.
FLAG_REPLY_TO_MISMATCH = "reply_to_domain_mismatch"
FLAG_FREEMAIL_CLAIMS_COMPANY = "freemail_claims_company"
FLAG_DISPLAY_NAME_MISMATCH = "display_name_domain_mismatch"
FLAG_LOOKALIKE_DOMAIN = "lookalike_domain"
FLAG_NO_AUTH_HEADER = "no_authentication_results"
FLAG_UNTRUSTED_AUTH_HEADER = "untrusted_authentication_results"

_METHOD_RE = re.compile(
    r"\b(spf|dkim|dmarc)\s*=\s*(pass|fail|softfail|neutral|none|temperror|permerror|policy|bestguesspass)",
    re.IGNORECASE,
)

#: Words in a display name or signature that suggest the sender speaks for an organisation.
_COMPANY_MARKERS = re.compile(
    r"\b(pvt\.?\s*ltd|private\s+limited|ltd\.?|llc|inc\.?|gmbh|corp\.?|corporation|"
    r"technologies|solutions|consult\w*|staffing|recruit\w*|talent|hr\s+team|"
    r"resourcing|manpower|placements?|services)\b",
    re.IGNORECASE,
)

#: Characters commonly swapped to build a lookalike domain.
_CONFUSABLES = {
    "0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b",
    "rn": "m", "vv": "w", "ii": "n",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_freemail_domains(path: str | None = None) -> frozenset[str]:
    """Load the free-mail domain list. Cached: it is read once per process."""
    target = Path(path) if path else FREEMAIL_PATH
    if not target.is_file():
        return frozenset()
    domains = set()
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            domains.add(line)
    return frozenset(domains)


def domain_of(address: str | None) -> str:
    """The domain part of an address, lower-cased. Empty string when there is not one."""
    if not address or "@" not in address:
        return ""
    return address.rsplit("@", 1)[1].strip().strip(">").lower()


def _registrable(domain: str) -> str:
    """Approximate the registrable domain, so ``mail.acme.com`` matches ``acme.com``.

    Deliberately simple: a full public-suffix list is a dependency and a data-freshness problem,
    and the consequence of getting this slightly wrong is one extra flag on an email a human is
    already going to read.
    """
    parts = [p for p in domain.split(".") if p]
    if len(parts) <= 2:
        return domain
    # Handle the common two-part suffixes we actually see (co.in, co.uk, com.au).
    if parts[-2] in {"co", "com", "net", "org", "gov", "ac"} and len(parts[-1]) <= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _normalise_confusables(domain: str) -> str:
    out = domain
    for wrong, right in _CONFUSABLES.items():
        out = out.replace(wrong, right)
    return out


def _edit_distance(left: str, right: str, limit: int = 2) -> int:
    """Levenshtein distance, capped. Returns ``limit + 1`` once it is clearly over."""
    if left == right:
        return 0
    if abs(len(left) - len(right)) > limit:
        return limit + 1

    previous = list(range(len(right) + 1))
    for i, lchar in enumerate(left, start=1):
        current = [i]
        for j, rchar in enumerate(right, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (lchar != rchar),
                )
            )
        if min(current) > limit:
            return limit + 1
        previous = current
    return previous[-1]


# ---------------------------------------------------------------------------
# Authentication-Results parsing
# ---------------------------------------------------------------------------


def _auth_header_values(email: RawEmail) -> list[str]:
    """Every Authentication-Results value, newest first.

    ``RawEmail.headers`` is a flat mapping, so a provider that saw several of these joins them
    with a newline. Both shapes are handled.
    """
    raw = email.headers.get("authentication-results")
    if not raw:
        return []
    return [part.strip() for part in str(raw).split("\n") if part.strip()]


def _trusted_value(values: Sequence[str], trusted_authserv: Iterable[str]) -> tuple[str | None, bool]:
    """Pick the header stamped by our own receiving service.

    Only our receiving MTA's verdict can be believed. Anyone can put an
    ``Authentication-Results: spf=pass dkim=pass dmarc=pass`` line in a message they send, or in
    a message they forward, and a naive parser would hand them a PASS. Returns the trusted value
    and whether any untrusted ones were discarded.
    """
    trusted = [t.lower() for t in trusted_authserv if t]
    if not trusted:
        # No configured receiving domain: fall back to the first (topmost) header, which is the
        # one our own server added.
        return (values[0] if values else None), False

    matched: str | None = None
    for value in values:
        authserv = value.split(";", 1)[0].strip().lower()
        if any(authserv == t or authserv.endswith("." + t) or authserv == t.lstrip(".") for t in trusted):
            matched = value
            break

    return matched, matched is not None and len(values) > 1


def _parse_methods(value: str) -> dict[str, str]:
    """Extract ``spf``/``dkim``/``dmarc`` results. First occurrence of each wins."""
    found: dict[str, str] = {}
    for method, result in _METHOD_RE.findall(value or ""):
        key = method.lower()
        if key not in found:
            found[key] = result.lower()
    return found


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------


def _impersonation_flags(
    email: RawEmail, freemail: frozenset[str], known_domains: frozenset[str]
) -> list[str]:
    flags: list[str] = []
    from_domain = domain_of(email.from_email)

    reply_to_domain = domain_of(email.reply_to)
    if reply_to_domain and from_domain and _registrable(reply_to_domain) != _registrable(from_domain):
        flags.append(FLAG_REPLY_TO_MISMATCH)

    is_freemail = from_domain in freemail or _registrable(from_domain) in freemail
    claims_company = bool(
        _COMPANY_MARKERS.search(email.from_name or "")
        or _COMPANY_MARKERS.search(_signature_block(email.body_text))
    )
    if is_freemail and claims_company:
        flags.append(FLAG_FREEMAIL_CLAIMS_COMPANY)

    if not is_freemail and from_domain:
        named = _company_in_display_name(email.from_name)
        # Compare against the whole domain, not the registrable part: a company often sits in a
        # subdomain label, as in careers.globex.com.
        flattened = re.sub(r"[^a-z0-9]", "", from_domain)
        if named and named not in flattened:
            flags.append(FLAG_DISPLAY_NAME_MISMATCH)

    if from_domain and _is_lookalike(from_domain, known_domains):
        flags.append(FLAG_LOOKALIKE_DOMAIN)

    return flags


def _signature_block(body: str, lines: int = 12) -> str:
    """The tail of the message, where a signature lives.

    Scanning the whole body would flag any email that merely mentions a company.
    """
    tail = [line for line in (body or "").splitlines() if line.strip()]
    return "\n".join(tail[-lines:])


def _company_in_display_name(display_name: str | None) -> str:
    """Pull a company token out of ``Jane Doe (Acme Corp)`` or ``Jane Doe | Acme``."""
    if not display_name:
        return ""
    match = re.search(r"[(|\-–]\s*([A-Za-z0-9 &.]{3,})\s*\)?\s*$", display_name.strip())
    if not match:
        return ""
    token = re.sub(r"\b(pvt|ltd|inc|llc|corp|corporation|limited|technologies|solutions)\b", "",
                   match.group(1), flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]", "", token.lower())


def _is_lookalike(from_domain: str, known_domains: frozenset[str]) -> bool:
    """Whether this domain is a near-miss for one we have corresponded with.

    Compares whole domains, not registrable parts. Both shapes of attack matter and the
    registrable reduction destroys each of them: ``rnicrosoft.com`` differs from
    ``microsoft.com`` in the registrable part, while ``agencv.example.com`` differs from
    ``agency.example.com`` only in a subdomain label. Reducing both to ``example.com`` would
    make the second pair look identical and the unrelated ``example.io`` look like a typo.
    """
    candidate = from_domain.lower()
    known = {k.lower() for k in known_domains if k}

    if candidate in known:
        return False

    for other in known:
        if _normalise_confusables(candidate) == _normalise_confusables(other):
            return True
        if 1 <= _edit_distance(candidate, other) <= 2:
            return True
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def verify(
    email: RawEmail,
    *,
    trusted_authserv: Iterable[str] = (),
    known_domains: Iterable[str] = (),
    freemail_path: str | None = None,
) -> VerificationResult:
    """Authenticate the sender and flag impersonation signals.

    Parameters
    ----------
    trusted_authserv:
        Our own receiving domain(s), as they appear at the start of an ``Authentication-Results``
        header. Only a header stamped by one of these is believed. Leave empty and the topmost
        header is used, which is the usual case for a single-hop mailbox.
    known_domains:
        Domains we have corresponded with, used for lookalike detection.
    """
    freemail = load_freemail_domains(freemail_path)
    known = frozenset(d.lower() for d in known_domains if d)

    values = _auth_header_values(email)
    flags = _impersonation_flags(email, freemail, known)

    if not values:
        # Absent headers are UNKNOWN, never PASS. An unauthenticated sender gets no draft.
        return VerificationResult(
            result=AuthResult.UNKNOWN,
            spf="none",
            dkim="none",
            dmarc="none",
            flags=tuple([FLAG_NO_AUTH_HEADER, *flags]),
            reason="No Authentication-Results header, so the sender could not be verified.",
        )

    trusted, discarded_untrusted = _trusted_value(values, trusted_authserv)
    if trusted is None:
        return VerificationResult(
            result=AuthResult.UNKNOWN,
            spf="none",
            dkim="none",
            dmarc="none",
            flags=tuple([FLAG_UNTRUSTED_AUTH_HEADER, *flags]),
            reason=(
                "No Authentication-Results header from our own receiving service. Any header "
                "present was added upstream and cannot be trusted."
            ),
        )

    if discarded_untrusted:
        flags.append(FLAG_UNTRUSTED_AUTH_HEADER)

    methods = _parse_methods(trusted)
    spf = methods.get("spf", "none")
    dkim = methods.get("dkim", "none")
    dmarc = methods.get("dmarc", "none")

    missing = [name for name, value in (("spf", spf), ("dkim", dkim), ("dmarc", dmarc)) if value == "none"]
    failed = [
        name
        for name, value in (("spf", spf), ("dkim", dkim), ("dmarc", dmarc))
        if value in {"fail", "softfail", "permerror", "temperror", "neutral", "policy"}
    ]

    if failed:
        result = AuthResult.FAIL
        reason = f"Authentication failed: {', '.join(f'{n}={methods.get(n)}' for n in failed)}."
    elif missing:
        result = AuthResult.UNKNOWN
        reason = f"Incomplete authentication: {', '.join(missing)} not reported."
    else:
        result = AuthResult.PASS
        reason = "SPF, DKIM and DMARC all pass."

    if result is AuthResult.PASS and flags:
        reason += f" Flagged anyway: {', '.join(flags)}."

    return VerificationResult(
        result=result,
        spf=spf,
        dkim=dkim,
        dmarc=dmarc,
        flags=tuple(flags),
        reason=reason,
    )

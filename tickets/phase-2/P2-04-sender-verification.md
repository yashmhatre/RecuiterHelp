# P2-04: Sender verification

**Phase:** 2 · **Est:** 1.5 days · **Blocked by:** nothing · **Status:** done

## Owns
- `pipeline/verify.py`
- `config/freemail_domains.txt`
- `tests/test_verify.py`

## Reads
- `docs/CONTRACTS.md` §1 (`RawEmail`, `VerificationResult`, `AuthResult`)

## Context
Requirement 6 in code: a failed-authentication sender never gets a draft. Pure function over
headers — no network, no model, no database. Easy to test exhaustively, so test it exhaustively.

## Scope
**Do**
- `verify(email: RawEmail) -> VerificationResult`.
- Parse `Authentication-Results` for SPF, DKIM and DMARC. **All three must pass** for
  `AuthResult.PASS`. Missing or unparseable headers give `UNKNOWN`, not `PASS`.
- Handle multiple `Authentication-Results` headers: trust only the one stamped by our own
  receiving domain, and ignore any others — a forged header inside the body of a relayed message
  must not be able to grant a pass.
- Raise these flags, each as a named string in `flags`:
  - `reply_to_domain_mismatch` — `Reply-To` domain differs from `From`
  - `freemail_claims_company` — sender is on the freemail list but the body or signature claims
    a company
  - `display_name_domain_mismatch` — display name names a company that is not the From domain
  - `lookalike_domain` — From domain is within edit distance 1-2 of a domain we have corresponded
    with before, or uses confusable characters
- `reason` must be a human-readable one-liner for the reviewer.

**Do not**
- Decide what happens next. The orchestrator (P2-12) maps `FAIL`/`UNKNOWN` to `Needs review`.

## Independence
Pure function over a `RawEmail` built inline in the tests. Needs no provider, model or database.

## Acceptance criteria
- [x] SPF pass + DKIM pass + DMARC pass → `PASS`; any one failing → `FAIL`
- [x] No `Authentication-Results` header → `UNKNOWN`, never `PASS`
- [x] A forged `Authentication-Results` from a non-receiving domain cannot produce `PASS`
- [x] Each of the four flags has a positive and a negative test case
- [x] A genuine recruiter on a company domain with a matching `Reply-To` raises no flags
- [ ] Every real `FAIL` case in the labelled set (P1-05) is caught — no false passes *(pending: the real labelled set does not exist yet)*

## Done when
`pytest tests/test_verify.py` passes with no external services.

## Outcome

Done. 50 tests, lint clean.

Decisions:

- **Two extra flags beyond the four in scope**, because the verdict needs to say *why* it is
  UNKNOWN: `no_authentication_results` (header absent) and `untrusted_authentication_results`
  (a header was present but not stamped by our own receiving service).
- **Only our own receiving service's header is believed.** Anyone can put
  `Authentication-Results: spf=pass dkim=pass dmarc=pass` in a message they send or forward, and
  a parser that reads the first header it finds hands them a PASS. `trusted_authserv` names our
  receiving domain; with several headers present, the forged one loses. With none configured the
  topmost header is used, which is our own server's on a single-hop mailbox.
- **Missing or partial results are UNKNOWN, never PASS.** Two of three passing is not
  authentication — DMARC is what ties the `From` header to the other two.
- **Lookalike detection compares whole domains, not registrable parts.** Both attack shapes
  matter and the registrable reduction destroys each: `rnicrosoft.com` differs from
  `microsoft.com` in the registrable part, while `agencv.example.com` differs from
  `agency.example.com` only in a subdomain label. Reducing both to `example.com` made the second
  pair identical and made an unrelated `example.io` look like a typo. Three tests caught this.
- **A freemail sender is not suspicious by itself.** Plenty of genuine independent recruiters use
  Gmail; the flag needs a company claim as well, read from the display name or the last dozen
  lines of the body rather than the whole message.

One acceptance criterion is genuinely blocked: "every real FAIL case in the labelled set is
caught" needs the labelled set, which does not exist yet. Re-run against it once P1-05 lands.

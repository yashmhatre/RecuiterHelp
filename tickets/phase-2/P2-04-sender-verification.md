# P2-04: Sender verification

**Phase:** 2 · **Est:** 1.5 days · **Blocked by:** nothing

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
- [ ] SPF pass + DKIM pass + DMARC pass → `PASS`; any one failing → `FAIL`
- [ ] No `Authentication-Results` header → `UNKNOWN`, never `PASS`
- [ ] A forged `Authentication-Results` from a non-receiving domain cannot produce `PASS`
- [ ] Each of the four flags has a positive and a negative test case
- [ ] A genuine recruiter on a company domain with a matching `Reply-To` raises no flags
- [ ] Every real `FAIL` case in the labelled set (P1-05) is caught — no false passes

## Done when
`pytest tests/test_verify.py` passes with no external services.

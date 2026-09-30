# P2-10: Validation gate

**Phase:** 2 · **Est:** 1.5 days · **Blocked by:** nothing

## Owns
- `pipeline/validate.py`
- `tests/test_validate.py`

## Reads
- `docs/CONTRACTS.md` §1 (`DraftContent`, `ValidationReport`, `ValidationIssue`), §4 (`draft.max_words`)

## Context
The last gate before a draft is saved. It is the mechanism behind the plan's hardest target —
zero wrong-candidate resumes — so it must not trust anything the model produced. Deterministic
code only.

## Scope
**Do**
- `validate(draft, email, profiles, resumes) -> ValidationReport`, running every check and
  returning **all** failures, not just the first.
- Checks, each a named `ValidationIssue.check`:
  - `recipient_is_authenticated_sender` — `draft.to` matches the verified `From`
  - `attachments_present` — every resume the body mentions is actually attached
  - `attachment_belongs_to_candidate` — each attached file's `candidate_id` matches a profile in
    `profiles_used`, cross-checked against the resume record, not the filename
  - `no_duplicate_candidates` — no two attachments for one candidate
  - `no_salary_figures` — no currency amounts, no LPA / CTC / per-annum figures, in body or subject
  - `facts_grounded` — named skills, years and locations in the body appear in the cited profile
  - `within_word_limit` — body is within `draft.max_words`
  - `attachment_files_exist` — every path exists and is non-empty on disk
  - `thread_preserved` — `thread_id` and `in_reply_to_message_id` are set and non-empty
- `ok` is true only when there are zero issues. No warning tier, no partial pass.

**Do not**
- Save, label, or repair the draft. A failing draft is discarded by P2-12 and routed to
  `Needs review`.

## Independence
Pure function over arguments constructed inline. Temp files stand in for resumes. No database,
no provider, no model.

## Acceptance criteria
- [ ] Each of the nine checks has a passing and a failing test
- [ ] A draft attaching one candidate resume while citing a different candidate fails
      `attachment_belongs_to_candidate` — including when the filename says otherwise
- [ ] Salary detection catches `12 LPA`, `1,200,000 INR`, `$95k` and `95,000 per annum`
- [ ] A body claiming a skill absent from the cited profile fails `facts_grounded`
- [ ] Multiple simultaneous failures are all reported in one report
- [ ] A fully valid draft returns `ok=True` with an empty issue list
- [ ] `ok=True` is impossible while any issue exists — asserted as a property test

## Done when
`pytest tests/test_validate.py` passes with no external services.

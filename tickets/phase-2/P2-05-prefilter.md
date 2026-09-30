# P2-05: Pre-filter

**Phase:** 2 · **Est:** 1 day · **Blocked by:** nothing

## Owns
- `pipeline/prefilter.py`
- `config/prefilter_rules.yaml`
- `tests/test_prefilter.py`

## Reads
- `docs/CONTRACTS.md` §1 (`RawEmail`, `PrefilterResult`)

## Context
Cheap deterministic rules that drop obvious non-mail before a model is ever loaded. Every drop
must name its rule so a wrongly dropped email can be diagnosed from the log alone.

## Scope
**Do**
- `prefilter(email: RawEmail) -> PrefilterResult`, dropping on:
  - `List-Unsubscribe` or `List-Id` present
  - `Precedence: bulk` / `list` / `junk`
  - `Auto-Submitted` other than `no`, or `X-Autoreply`
  - out-of-office and delivery-failure patterns
  - job-alert and newsletter senders (`noreply@`, `jobs-listings@`, `alerts@`, configurable list)
  - `email.is_from_self`
- Rules live in `config/prefilter_rules.yaml` so P3-03 can tune them without a code change.
- Every drop sets `rule` to the rule name. A kept email has `rule = None`.
- Order rules cheapest-first and stop at the first match.

**Do not**
- Try to decide recruiter-or-not. That is the model's job in P2-06. When in doubt, keep.

## Independence
Pure function over inline `RawEmail` fixtures. No dependencies at all.

## Acceptance criteria
- [ ] Each rule has a test that trips it and one that does not
- [ ] A genuine recruiter email that happens to contain the word "unsubscribe" in the body but
      has no `List-Unsubscribe` header is kept
- [ ] Our own sent mail is dropped as `is_from_self`
- [ ] Rules load from YAML; adding a sender to the list needs no code change
- [ ] **Zero false drops** across the recruiter emails in the labelled set — this is the metric
      that matters, since a dropped email is silently lost

## Done when
`pytest tests/test_prefilter.py` passes, including the zero-false-drop check against
`labels.example.jsonl`.

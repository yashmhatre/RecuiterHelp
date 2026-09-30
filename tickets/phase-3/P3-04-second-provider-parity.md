# P3-04: Cross-provider parity run

**Phase:** 3 · **Est:** 1 day · **Blocked by:** nothing

## Owns
- `eval/parity.py`
- `docs/provider-parity.md`
- `tests/test_parity.py`

## Reads
- `docs/CONTRACTS.md` §1 (`RawEmail`), §2 (labels)

## Context
Requirement 7: the same pipeline must pass the test set on both providers. The risk is not the
pipeline, it is normalisation — if Gmail and Graph produce different `RawEmail` values for the
same message, every downstream number diverges.

## Scope
**Do**
- Send a fixed set of ~20 emails to both a Gmail and an Outlook mailbox, fetch each through its
  own provider, and diff the resulting `RawEmail` objects field by field.
- Report every divergence: header casing, body whitespace and line endings, HTML-to-text
  differences, timezone handling on `received_at`, thread ID stability across replies,
  `Authentication-Results` presence and format.
- Run the full labelled set through both providers and compare all plan metrics side by side.
- Confirm label/category behaviour matches: same names, created on first use, idempotent.
- Write down every divergence that is acceptable and why, in `docs/provider-parity.md`. Anything
  that moves a metric is a bug against P2-02 or P2-03, filed separately.

**Do not**
- Fix provider bugs here. File them against the owning provider ticket.

## Independence
Works from recorded fixtures for the offline diff; the live part is marked `@pytest.mark.live` and
run by hand against both mailboxes.

## Acceptance criteria
- [ ] Field-by-field `RawEmail` diff across the ~20-message set, with every difference explained
- [ ] `received_at` is timezone-aware and identical for the same message on both providers
- [ ] Thread ID is stable across a reply on both providers
- [ ] Every plan metric within 2 percentage points between providers
- [ ] Label and category behaviour identical
- [ ] Divergences documented, and metric-affecting ones filed as provider bugs

## Done when
`eval/parity.py` reports no metric gap above 2 points and every divergence is documented.

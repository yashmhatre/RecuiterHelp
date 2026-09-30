# P4-01: Pilot feedback capture

**Phase:** 4 · **Est:** 1.5 days · **Blocked by:** nothing

## Owns
- `eval/feedback_cli.py`
- `docs/pilot-protocol.md`
- `tests/test_feedback_cli.py`

## Reads
- `docs/schema.reference.sql` (`draft_feedback`)

## Context
The plan asks for a record per draft — sent as is, edited, or discarded, plus any wrong match.
Without a low-friction way to record that, the pilot produces an opinion instead of a number.

## Scope
**Do**
- `feedback_cli.py`: list drafts awaiting a verdict, record `sent_as_is` / `edited` / `discarded`,
  a `wrong_match` flag, and free-text notes. Under ten seconds per draft, or the reviewer will
  stop using it.
- Where a draft was edited, capture the edited text so the diff against the generated draft can be
  read later — that diff is the most useful signal the pilot produces.
- `docs/pilot-protocol.md`: the daily routine, what counts as a "minor edit" (the plan's 60%
  target is meaningless without that definition), and the rule that **no draft is sent unreviewed**.
- An escalation path: any wrong-candidate resume stops the pilot the same day, gets added to the
  adversarial suite (P3-02), and is fixed before the pilot restarts.
- Pilot-period backups of the database, since this is the first time it holds real matching history.

**Do not**
- Add a send path. Sending stays manual in Gmail or Outlook, as requirement 5 says.

## Independence
Writes to `draft_feedback`, a table that exists in the reference DDL. Tests run against a
throwaway database seeded straight from `docs/schema.reference.sql`.

## Acceptance criteria
- [ ] All three outcomes and the `wrong_match` flag recordable, with notes
- [ ] Edited text captured so a diff against the original draft can be produced
- [ ] Recording a verdict twice for one draft updates rather than duplicates
- [ ] "Minor edit" is defined concretely enough that two reviewers agree
- [ ] The escalation rule for a wrong-candidate resume is written and agreed
- [ ] Reviewer records a real day of drafts in under ten seconds each

## Done when
`pytest tests/test_feedback_cli.py` passes and one real review day has been recorded.

# P4-02: Weekly pilot review and the go/no-go decision

**Phase:** 4 · **Est:** 1 day per week, 2 weeks · **Blocked by:** nothing

## Owns
- `eval/pilot_report.py`
- `docs/pilot-week-1.md`, `docs/pilot-week-2.md`
- `docs/decision-free-vs-paid.md`

## Reads
- `docs/schema.reference.sql` (`draft_feedback`, `drafts`, `matches`, `classifications`)

## Context
The plan's closing question is whether the free models are good enough. This ticket produces the
evidence and the recommendation, and answers the three open questions the plan leaves at the end.

## Scope
**Do**
- `pilot_report.py`: from the database, report per week — drafts produced, outcome split,
  wrong-match count, `Needs review` rate with reasons, arrival-to-draft latency p50 and p95, and
  the recruiter emails that produced **no** draft at all (the silent failure mode, which the
  outcome split cannot show).
- Compare pilot numbers against the Phase 3 holdout numbers. A gap between them means the labelled
  set was not representative; say so plainly rather than averaging it away.
- Write up each week with what went wrong and what was changed.
- `docs/decision-free-vs-paid.md`: a recommendation with numbers behind it — stay on local models,
  or move the classification and/or drafting step to a paid API at the roughly $15/month the plan
  estimates. Include the measured latency against the under-5-minute target, since a CPU-only
  14B model is the likeliest thing to miss it.
- Close out the plan's three open questions with decisions: which provider and account type the
  pilot used, how many candidates and profiles were loaded, and whether a draft carries all matches
  above threshold or a cap of 1-3.

**Do not**
- Enable auto-send. That is explicitly out of scope for v1, whatever the numbers say.

## Independence
Reads only from the database. Develop against a seeded throwaway database with synthetic feedback
rows.

## Acceptance criteria
- [ ] Weekly report covers every metric above, including the no-draft recruiter emails
- [ ] Pilot numbers are compared against the Phase 3 holdout, with any gap explained
- [ ] Both weekly write-ups completed
- [ ] `sent as is` or `minor edit` rate reported against the 60% target
- [ ] Wrong-candidate-resume count reported — target is 0
- [ ] A costed free-versus-paid recommendation is written
- [ ] All three of the plan's open questions answered with a decision

## Done when
Both weekly reviews are written and the go/no-go recommendation has been accepted.

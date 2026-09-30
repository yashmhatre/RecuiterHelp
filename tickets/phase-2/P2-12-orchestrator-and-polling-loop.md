# P2-12: Orchestrator and polling loop

**Phase:** 2 · **Est:** 2 days · **Blocked by:** nothing

## Owns
- `main.py`
- `pipeline/orchestrator.py`
- `tests/test_orchestrator.py`
- `docs/running.md`

## Reads
- `docs/CONTRACTS.md` §1 (every type), §2 (labels), §4 (`classify.min_confidence`,
  `poll.interval_seconds`)

## Context
The wiring: fetch, verify, prefilter, classify, match, draft, validate, save, label, record.
Every routing decision in the plan flow lives here and nowhere else, which is why each stage
ticket was told to return a result rather than decide.

## Scope
**Do**
- `process_email(email) -> EmailStatus`, implementing exactly this routing:

  | Condition | Outcome |
  |---|---|
  | `prefilter.keep` is false | `SKIPPED_BULK`, no label, no draft |
  | `verify` is `FAIL` or `UNKNOWN` | `Needs review` label, **no draft** |
  | `is_recruiter` is false | `NOT_RECRUITER`, no draft |
  | `confidence < classify.min_confidence` | `Needs review`, no draft |
  | no match at or above `match.min_score` | `Needs review`, no draft |
  | `validation.ok` is false | `Needs review`, **draft discarded, not saved** |
  | otherwise | save draft, apply `AI Draft` |

- Order matters: verification runs before any model call, so a spoofed sender never reaches one.
- Polling loop on `poll.interval_seconds`, reading and writing the cursor through the repo so a
  restart resumes where it stopped and never re-drafts a processed email.
- One email failing is caught, recorded, labelled `Needs review`, and the loop continues. One bad
  message must not stall the mailbox.
- Advance the cursor only after the batch is durably recorded.
- Graceful shutdown on SIGINT/SIGTERM: finish the current email, persist the cursor, exit 0.
- `--once` for a single pass and `--dry-run` that does everything except save the draft.

**Do not**
- Implement any stage logic. Every stage is a constructor-injected callable.

## Independence
Every stage is injected. Tests wire fakes for all of them plus `providers/fake.py`, so this is the
one ticket that proves the routing table without a single real dependency. If P2-01 has not landed,
write a ten-line in-test fake provider.

## Acceptance criteria
- [ ] Every row of the routing table has a test
- [ ] A failed-auth email reaches no model call — asserted by a fake that raises if called
- [ ] A validation failure results in no `save_draft` call at all
- [ ] An exception in any single stage is contained: that email is labelled `Needs review`, the
      loop continues, and the next email is processed
- [ ] Restarting mid-batch re-processes nothing already drafted — proven by running the same
      fixture batch twice and asserting one draft
- [ ] The cursor is not advanced when recording fails
- [ ] SIGTERM finishes the current email, persists the cursor and exits 0
- [ ] `--dry-run` saves nothing
- [ ] No send path exists in `main.py` or `pipeline/orchestrator.py`

## Done when
`pytest tests/test_orchestrator.py` passes with every stage faked.

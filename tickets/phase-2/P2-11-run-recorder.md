# P2-11: Run recorder — persistence and MLflow instrumentation

**Phase:** 2 · **Est:** 1 day · **Blocked by:** nothing

## Owns
- `pipeline/recorder.py`
- `tests/test_recorder.py`

## Reads
- `docs/CONTRACTS.md` §1 (all result types), §6 (tracing surface)
- `docs/schema.reference.sql` (`emails`, `classifications`, `matches`, `drafts`)

## Context
Step 9 of the plan: every classification, match score, reason and draft ID is written to Postgres
and to MLflow. Putting it in one module keeps persistence out of the pipeline stages and means the
orchestrator has one thing to call per stage.

## Scope
**Do**
- One `Recorder` class with a method per stage: `record_email`, `record_verification`,
  `record_classification`, `record_matches`, `record_draft`, `record_skipped`.
- Each method writes the database row **and** calls `log_stage` from the §6 tracing surface.
- Take the repository and the tracing module as constructor arguments.
- Idempotency: recording the same email twice updates rather than duplicates, so a crash and
  restart mid-pipeline is safe.
- Store the full `ValidationReport` as JSON on the draft row, including the passing case, so a
  reviewer can see what was checked.
- Never log resume text, full email bodies, candidate emails or phone numbers to MLflow — IDs,
  counts, scores and durations only. The database may hold the sender; MLflow may not.

**Do not**
- Decide routing or call any pipeline stage.

## Independence
Repo and tracing are both injected. Tests use an in-memory fake repo and a recording fake tracer,
so neither P1-01 nor P0-04 needs to have landed.

## Acceptance criteria
- [ ] Each stage writes the expected row and emits exactly one `log_stage` call
- [ ] Recording the same email twice leaves one row per table
- [ ] A tracing exception does not fail the database write
- [ ] A database failure raises — persistence is not best-effort, unlike tracing
- [ ] No candidate email, phone, resume text or email body reaches the tracer — asserted by
      scanning everything the fake tracer received
- [ ] The validation report is stored for passing drafts too

## Done when
`pytest tests/test_recorder.py` passes with fakes for both dependencies.

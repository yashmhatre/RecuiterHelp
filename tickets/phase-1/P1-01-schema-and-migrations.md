# P1-01: Database schema, migrations and repository layer

**Phase:** 1 · **Est:** 2 days · **Blocked by:** nothing

## Owns
- `db/migrations/*.sql` (or Alembic versions)
- `email_agent/db/models.py`
- `email_agent/db/repo.py`
- `tests/test_migrations.py`, `tests/test_repo.py`

## Reads
- `docs/schema.reference.sql` — the frozen DDL, column names final
- `docs/CONTRACTS.md` §1 for the dataclasses that `repo.py` returns

## Context
Turns the frozen reference DDL into real, ordered, reversible migrations, plus the thin
repository functions the pipeline uses. The pipeline tickets do not write SQL.

## Scope
**Do**
- Migrations covering every table in the reference DDL, each with a working downgrade.
- `models.py`: ORM or plain row mappers matching the DDL exactly.
- `repo.py`: the small, named set of operations the pipeline needs, each returning
  `contracts.py` dataclasses, never ORM objects:
  `upsert_email`, `get_email_by_provider_id`, `save_classification`, `save_matches`,
  `save_draft`, `get_cursor`, `set_cursor`, `get_profile`, `get_current_resume`,
  `list_active_profiles`.
- `upsert_email` must be idempotent on `(provider, provider_message_id)` — a re-fetch after a
  restart must not duplicate rows or re-draft.
- Enforce the one-current-resume-per-profile unique index.

**Do not**
- Add matching queries (P2-07 owns the hybrid search SQL) or embedding writes (P1-04).

## Independence
Runs against a throwaway Postgres from `docker-compose.yml`, or `testcontainers`. Do not import
`db/engine.py`; take a connection/session as an argument so the tests can pass their own. If
P0-03 has not landed, the test fixture builds its own engine in ten lines.

## Acceptance criteria
- [ ] Migrate up from empty, then down to empty, then up again — all clean
- [ ] Every reference-DDL table, column, index and constraint exists after migrating up
- [ ] `upsert_email` called twice with the same message id leaves exactly one row
- [ ] Inserting a second `is_current` resume for one profile is rejected by the DB
- [ ] Deleting a candidate cascades to profiles and resumes
- [ ] Every `repo.py` function returns `contracts.py` types

## Done when
`pytest tests/test_migrations.py tests/test_repo.py` passes against a fresh database.

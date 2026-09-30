# P0-03: PostgreSQL + pgvector environment and connection layer

**Phase:** 0 · **Est:** 1 day · **Blocked by:** nothing

## Owns
- `docker-compose.yml`
- `email_agent/db/engine.py`
- `scripts/healthcheck_db.py`
- `tests/test_db_engine.py`
- `docs/setup-postgres.md`

## Reads
- `docs/schema.reference.sql` (for the extension list only)

## Context
A running Postgres with `vector` and `pg_trgm`, plus one place that hands out connections. The
tables themselves are P1-01's job; this ticket stops at the connection.

## Scope
**Do**
- `docker-compose.yml` with `pgvector/pgvector:pg16`, a named volume, healthcheck, and port from
  `.env`.
- `engine.py`: pooled connection factory from `DATABASE_URL`, a `session()` context manager that
  commits on success and rolls back on exception, and sane pool limits for a single-process poller.
- `healthcheck_db.py`: verifies connectivity and that both extensions are installed.
- `docs/setup-postgres.md`: the Docker path and the native-install path, plus backup/restore
  commands (the risk table calls for encrypted backups — document `pg_dump` piped through `age`
  or `gpg`).

**Do not**
- Create tables, write migrations, or define ORM models. P1-01 owns all of that.

## Independence
Tests use `testcontainers-python`, or skip with a clear message when Docker is unavailable.
The `session()` rollback semantics are unit-tested against SQLite in-memory, which needs no
server at all.

## Acceptance criteria
- [ ] `docker compose up -d` gives a reachable Postgres with `vector` and `pg_trgm` present
- [ ] `session()` commits on clean exit and rolls back when the block raises
- [ ] Credentials come only from the environment; none are committed
- [ ] Healthcheck exits non-zero with a readable message when the DB is down
- [ ] Backup and restore commands in the doc are copy-pasteable and were run once

## Done when
`pytest tests/test_db_engine.py` passes, and `docker compose up -d && python scripts/healthcheck_db.py` succeeds.

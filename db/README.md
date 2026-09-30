# `db/` — SQL assets only

This directory holds SQL and Alembic configuration. It is deliberately **not** a Python package.

Python database code lives in `email_agent/db/` (engine, models, repository). Keeping the two
apart is why `db/` has no `__init__.py` — nothing here is importable.

- `migrations/` — ordered migrations, owned by ticket P1-01
- the frozen reference DDL is `docs/schema.reference.sql`, not a file in here

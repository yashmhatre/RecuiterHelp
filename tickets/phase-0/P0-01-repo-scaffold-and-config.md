# P0-01: Repo scaffold, contracts module and config loader

**Phase:** 0 · **Est:** 1 day · **Blocked by:** nothing · **Status:** done

## Owns
- `email_agent/__init__.py` and the empty package tree from Plan.md ("Project structure")
- `email_agent/contracts.py`
- `email_agent/config.py`
- `config/settings.yaml`
- `.env.example`
- `pyproject.toml`, `requirements.txt`
- `tests/test_config.py`, `tests/test_contracts.py`
- `db/README.md`

## Reads
- `docs/CONTRACTS.md` §1 (types), §4 (thresholds)

## Context
Every other ticket imports `contracts.py` and `config.py`. Both are transcriptions of a frozen
document, so this ticket is pure typing work with no design decisions left in it.

## Scope
**Do**
- Create the package tree: `config/`, `providers/`, `pipeline/`, `db/`, `profiles/`, `eval/`,
  `resumes/.gitkeep`, `tests/`.
- Transcribe `docs/CONTRACTS.md` §1 into `email_agent/contracts.py` **verbatim**. Types only —
  no logic, no I/O, no imports from the rest of the package.
- `config.py`: load `config/settings.yaml`, overlay env vars (`EA_MATCH__MIN_SCORE` overrides
  `match.min_score`), expose typed accessors, fail loudly on an unknown key.
- `config/settings.yaml` carries exactly the §4 defaults.
- `.env.example` lists every secret name with an empty value: DB URL, Ollama host, MLflow URI,
  provider client id/secret/tenant, mailbox address. No real values.
- Pin dependency versions.

**Do not**
- Write any pipeline logic, DB access or provider code.

## Independence
Nothing to stub — this ticket is the floor. It must not import anything from the other tickets.

## Acceptance criteria
- [x] `from email_agent.contracts import RawEmail, DraftContent, MailProvider` works
- [x] `MailProvider` has no `send` method, and `grep -ri "def send" email_agent/` is empty
- [x] Every §4 key resolves to its documented default with no env vars set
- [x] An env override changes the value; an unknown `EA_*` key raises at startup
- [x] `.env` is gitignored and `.env.example` is committed

## Done when
`pytest tests/test_config.py` passes on a clean clone.

## Outcome

Done. 77 tests, lint clean.

Two files added to scope beyond the original list: `tests/test_contracts.py` (the shape and
no-send assertions did not belong in `test_config.py`) and `db/README.md`.

Decisions taken here that every later ticket inherits:

- **Package layout.** Importable code lives in `email_agent/` (`contracts.py`, `config.py`,
  plus empty `models/`, `auth/`, `db/`). `providers/`, `pipeline/`, `profiles/`, `eval/` and
  `tests/` are top-level packages, matching the paths in every other ticket's `Owns` list.
  Top-level `db/` is **SQL assets only** and deliberately has no `__init__.py` — Python database
  code goes in `email_agent/db/`. See `db/README.md`.
- **Env override rule.** `EA_` + dotted path with `__` for `.`, as specified. An `EA_` variable
  containing `__` must resolve to a known key or loading fails, so a mistyped
  `EA_MATCH__MIN_SCOR` cannot silently leave the pilot on the wrong threshold. `EA_` variables
  that are not settings (`EA_PROVIDER`, `EA_MAILBOX_ADDRESS`, `EA_RESUME_DIR`) are listed in
  `config.RESERVED_ENV` and documented in `.env.example`; a test asserts the two stay in step.
- **Dependencies are grouped per ticket** in `pyproject.toml` extras (`models`, `db`, `tracing`,
  `providers`, `documents`, `dev`, `testing`), so working one ticket does not mean installing
  MLflow and the Google client. All pins verified to resolve on Python 3.11.
- **Cross-field validation** beyond the contract: `match.rerank_pool` must be at least
  `match.max_profiles`, since the re-ranker cannot select more profiles than it is handed.
- **`Settings.with_overrides()`** added for P3-03, so the sweep varies a configuration without
  mutating the environment between runs.

### Contract change made here

`docs/CONTRACTS.md` section 1 now imports `Sequence` from `collections.abc` rather than `typing`
(the `typing` alias is deprecated). Doc and code changed together, in their own commit, before
anything was built against the old spelling. No shape changed.

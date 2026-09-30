# P0-01: Repo scaffold, contracts module and config loader

**Phase:** 0 · **Est:** 1 day · **Blocked by:** nothing

## Owns
- `email_agent/__init__.py` and the empty package tree from Plan.md ("Project structure")
- `email_agent/contracts.py`
- `email_agent/config.py`
- `config/settings.yaml`
- `.env.example`
- `pyproject.toml`, `requirements.txt`
- `tests/test_config.py`

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
- [ ] `from email_agent.contracts import RawEmail, DraftContent, MailProvider` works
- [ ] `MailProvider` has no `send` method, and `grep -ri "def send" email_agent/` is empty
- [ ] Every §4 key resolves to its documented default with no env vars set
- [ ] An env override changes the value; an unknown `EA_*` key raises at startup
- [ ] `.env` is gitignored and `.env.example` is committed

## Done when
`pytest tests/test_config.py` passes on a clean clone.

# What every file is for

| File | Does | Why |
|---|---|---|
| `Plan.md` | The spec | Source of every requirement and target |
| `docs/CONTRACTS.md` | Frozen types, model schemas, thresholds | Lets 28 tickets be built in parallel without reading each other's code |
| `docs/schema.reference.sql` | Frozen DDL | DB fixtures without waiting on migrations |
| `docs/TICKETS.md` | Ticket index, requirement coverage | Proves no requirement is unassigned |
| `tickets/` | 28 tickets, disjoint file ownership | Any one finishable on a clean clone |
| `email_agent/contracts.py` | Shared dataclasses, `MailProvider` | Common vocabulary; no `send` method, so requirement 5 holds by shape |
| `email_agent/config.py` | `settings.yaml` + `EA_*` env overlay | One home for thresholds; a mistyped override fails loudly |
| `config/settings.yaml` | The 7 thresholds | Only P3-03 may change them |
| `.env.example` | Secret names, no values | Real `.env` is gitignored |
| `pyproject.toml` | Deps grouped per ticket | Work one ticket without installing MLflow |
| `db/` | SQL only, not importable | Keeps SQL apart from `email_agent/db/` code |
| `eval/dataset/schema.json` | Validates one labelled email | Bad ground truth corrupts every metric |
| `eval/validate_dataset.py` | Checks records, count, intent spread | Gates the dataset before accuracy is measured |
| `eval/label_cli.py` | Import, label, resume, anonymise | Labelling is the slow path; keeps real senders out of git |
| `eval/agreement.py` | Labels 30 emails twice, reports disagreement | If two passes disagree >5%, a 95% target is inside the noise and unmeasurable |
| `labels.example.jsonl` | 10 synthetic records | Fixtures for other tickets; real labels gitignored |
| `tests/` | 159 tests | Each ticket's proof it works standalone |

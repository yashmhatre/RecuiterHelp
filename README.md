# Recruiter Email Agent

Watches one mailbox (Gmail or Outlook), identifies genuine recruiter emails, matches the
requirement against our candidate profiles, and **saves a reply as a draft** in the same thread
with the right resumes attached.

A person reviews and sends every draft. The agent has no send path — that is enforced by the
provider interface, by the OAuth scopes requested, and by a repo-wide test.

Full plan: [Plan.md](Plan.md).

## Repository layout

```
Plan.md                      the plan this repo implements
docs/
  CONTRACTS.md               frozen types, schemas, thresholds — read this first
  schema.reference.sql       frozen DDL, column names final
  TICKETS.md                 ticket index, sequencing, requirement coverage
tickets/
  TEMPLATE.md
  phase-0/ … phase-4/        28 independently buildable tickets
email_agent/
  contracts.py               frozen shared types, imported by every stage
  config.py                  settings loader
  models/ auth/ db/          filled in by ticket
providers/                   base, fake, gmail, outlook
pipeline/                    verify, prefilter, classify, match, draft, validate, orchestrator
profiles/                    resume import and embedding scripts
eval/                        dataset, harness, metrics, adversarial cases
db/                          SQL assets only, NOT importable (see db/README.md)
config/settings.yaml         the tunable thresholds
resumes/                     gitignored
```

## Getting started

```bash
python -m venv .venv && . .venv/Scripts/activate   # or bin/activate
pip install -e ".[dev]"                            # add the groups your ticket needs
pytest
```

Dependencies are grouped per ticket in `pyproject.toml`, so you install only what you need:
`.[documents,dev]` for resume parsing, `.[models,dev]` for the model stages, `.[db,dev,testing]`
for anything touching Postgres.

## How the work is organised

Tickets are independent by construction: a frozen contract instead of cross-ticket dependencies,
injected collaborators so every stage is testable with fakes, and exclusive file ownership so two
tickets never touch the same file. Any ticket can be picked up on a clean clone and finished
without waiting for another. See [docs/TICKETS.md](docs/TICKETS.md).

Start with **P1-05** (labelled dataset) and **P3-02** (adversarial suite) — both are slow, both
block nothing, and every Phase 3 target depends on them.

## Ground rules

- No send path, ever. `Mail.ReadWrite` only on Graph; no `gmail.send` on Gmail.
- No real candidate data in the repo. Resumes, `.env` and the labelled email set are gitignored.
- A failed sender-authentication check never produces a draft.
- Thresholds live in `config/settings.yaml`. Nothing hardcodes them.
- Contracts change in their own PR, never inside a feature ticket.

## Status

| | |
|---|---|
| Planning | Complete — 28 tickets, contracts frozen |
| P0-01 scaffold, contracts, config | Done |
| P1-05 dataset tooling | Done, agreement check included; labelling outstanding |
| Everything else | Not started |

`pytest` currently runs 159 tests. What each file is for: [docs/COMPONENTS.md](docs/COMPONENTS.md).

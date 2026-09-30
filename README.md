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
```

Code lands under `email_agent/`, `providers/`, `pipeline/`, `db/`, `profiles/`, `eval/` and
`tests/` as tickets are completed — see [P0-01](tickets/phase-0/P0-01-repo-scaffold-and-config.md).

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

Planning complete. No implementation code yet.

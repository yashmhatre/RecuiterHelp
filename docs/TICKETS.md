# Ticket index

28 tickets across 5 phases. **Every ticket is independently buildable, testable and mergeable.**

## What "independent" means here

No ticket waits on another ticket's code. It is achieved three ways, and every ticket states
which ones it uses:

1. **A frozen contract instead of a dependency.** `docs/CONTRACTS.md` and
   `docs/schema.reference.sql` are committed before any ticket starts. A ticket that needs a type,
   a table shape, a threshold or a model response schema reads it from there.
2. **Injected collaborators.** Every stage takes its model client, repository, parser, provider
   and tracer as arguments. Tests pass fakes. Nothing constructs its own dependencies at import
   time.
3. **Disjoint file ownership.** Each ticket's `Owns` list is exclusive. Two tickets never edit the
   same file, so they never conflict on merge.

Where a ticket would otherwise need a file another ticket owns (`contracts.py`,
`embedding_text.py`), the file's full content is in the contract doc. Whoever needs it first
creates it; the content is identical either way, so the merge is a no-op.

## Sequencing

Phases are **calendar guidance, not gates**. Tickets can be pulled forward freely. Two worth
starting on day one whatever else is happening:

- **P1-05 (labelled dataset)** — 3 days of human labelling, blocks nothing, and every Phase 3
  target is measured against it. Start it first.
- **P3-02 (adversarial suite)** — hand-written fixtures, needs no pipeline, and the one target
  with zero tolerance.

## Phase 0 — Setup

| ID | Title | Est |
|---|---|---|
| [P0-01](../tickets/phase-0/P0-01-repo-scaffold-and-config.md) | Repo scaffold, contracts module and config loader | 1d |
| [P0-02](../tickets/phase-0/P0-02-ollama-model-client.md) | Ollama runtime and JSON model client | 1d |
| [P0-03](../tickets/phase-0/P0-03-postgres-pgvector.md) | PostgreSQL + pgvector environment and connection layer | 1d |
| [P0-04](../tickets/phase-0/P0-04-mlflow-tracing.md) | MLflow server and the tracing module | 1d |
| [P0-05](../tickets/phase-0/P0-05-oauth-and-token-store.md) | OAuth app registration and token store | 1d |

## Phase 1 — Data

| ID | Title | Est |
|---|---|---|
| [P1-01](../tickets/phase-1/P1-01-schema-and-migrations.md) | Database schema, migrations and repository layer | 2d |
| [P1-02](../tickets/phase-1/P1-02-resume-parsing.md) | Resume file parsing to clean text | 1d |
| [P1-03](../tickets/phase-1/P1-03-profile-extraction-and-review.md) | Profile extraction and the review CLI | 2d |
| [P1-04](../tickets/phase-1/P1-04-embeddings.md) | Profile embeddings and the vector index | 1d |
| [P1-05](../tickets/phase-1/P1-05-labelled-email-dataset.md) | Labelled email dataset (200-300 emails) | 3d |

## Phase 2 — Pipeline

| ID | Title | Est |
|---|---|---|
| [P2-01](../tickets/phase-2/P2-01-provider-interface-and-fakes.md) | Provider interface, fake provider and the no-send guard | 1d |
| [P2-02](../tickets/phase-2/P2-02-gmail-provider.md) | Gmail provider | 2d |
| [P2-03](../tickets/phase-2/P2-03-outlook-provider.md) | Outlook / Microsoft Graph provider | 2d |
| [P2-04](../tickets/phase-2/P2-04-sender-verification.md) | Sender verification | 1.5d |
| [P2-05](../tickets/phase-2/P2-05-prefilter.md) | Pre-filter | 1d |
| [P2-06](../tickets/phase-2/P2-06-classify-and-extract.md) | Classification and field extraction | 2d |
| [P2-07](../tickets/phase-2/P2-07-match-filters-and-hybrid-search.md) | Hard filters and hybrid search | 2d |
| [P2-08](../tickets/phase-2/P2-08-match-rerank-and-selection.md) | Model re-rank and final selection | 1.5d |
| [P2-09](../tickets/phase-2/P2-09-draft-composition.md) | Draft composition | 2d |
| [P2-10](../tickets/phase-2/P2-10-validation-gate.md) | Validation gate | 1.5d |
| [P2-11](../tickets/phase-2/P2-11-run-recorder.md) | Run recorder — persistence and MLflow instrumentation | 1d |
| [P2-12](../tickets/phase-2/P2-12-orchestrator-and-polling-loop.md) | Orchestrator and polling loop | 2d |

## Phase 3 — Test and tune

| ID | Title | Est |
|---|---|---|
| [P3-01](../tickets/phase-3/P3-01-eval-harness.md) | Evaluation harness and metrics | 2d |
| [P3-02](../tickets/phase-3/P3-02-adversarial-suite.md) | Adversarial test suite | 2d |
| [P3-03](../tickets/phase-3/P3-03-tuning-and-threshold-sweep.md) | Prompt, threshold and rule tuning | 3d |
| [P3-04](../tickets/phase-3/P3-04-second-provider-parity.md) | Cross-provider parity run | 1d |

## Phase 4 — Pilot

| ID | Title | Est |
|---|---|---|
| [P4-01](../tickets/phase-4/P4-01-pilot-feedback-capture.md) | Pilot feedback capture | 1.5d |
| [P4-02](../tickets/phase-4/P4-02-pilot-review-and-go-no-go.md) | Weekly pilot review and the go/no-go decision | 2w part-time |

## Requirement coverage

Every requirement in Plan.md maps to at least one ticket, and each is verifiable from that
ticket's acceptance criteria alone.

| Req | Tickets |
|---|---|
| 1 — 95% classification accuracy | P2-06, P1-05, P3-01, P3-03 |
| 2 — Multiple profiles per candidate | P1-01, P1-03, P2-08 |
| 3 — Reply with matching profiles and resumes | P2-07, P2-08, P2-09 |
| 4 — Best-suited tools, tested on real email | P0-02, P0-03, P3-01, P4-02 |
| 5 — Draft only, no send path | P0-05, P2-01, P2-02, P2-03, P2-12 |
| 6 — Genuine recruiter; resume requests handled | P2-04, P2-05, P2-09, P3-02 |
| 7 — Gmail and Outlook both supported | P2-01, P2-02, P2-03, P3-04 |
| 8 — One mailbox, resumable sync | P1-01, P2-02, P2-03, P2-12 |

## Ticket hygiene

- A ticket that turns out to need another ticket's code is **mis-scoped**. Fix the scope or move
  the shared piece into `docs/CONTRACTS.md` — do not add a dependency.
- Changing a contract is its own PR, flagged in every open ticket it touches.
- Every ticket ends with a `pytest` command that passes on a clean clone with nothing else merged.
  If it does not, the ticket is not independent.

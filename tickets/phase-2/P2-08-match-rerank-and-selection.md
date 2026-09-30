# P2-08: Model re-rank and final selection

**Phase:** 2 · **Est:** 1.5 days · **Blocked by:** nothing

## Owns
- `pipeline/match_rerank.py`
- `config/prompts/rerank.txt`
- `tests/test_match_rerank.py`

## Reads
- `docs/CONTRACTS.md` §1 (`Match`), §3 (`rerank.v1`), §4 (`match.min_score`, `match.max_profiles`)

## Context
Takes the hybrid pool and produces the short list that gets drafted. The one-profile-per-candidate
rule lives here, and it is the main defence against a draft that offers the same person twice.

## Scope
**Do**
- `rerank(requirement, candidates: list[Profile], model_client) -> list[Match]` using the
  `rerank.v1` schema, `stage="rerank"`.
- Selection, in this order:
  1. Drop anything below `match.min_score`.
  2. **Keep at most one profile per `candidate_id`** — the highest-scoring one.
  3. Cap at `match.max_profiles`.
  4. Set `selected=True` on survivors.
- Named-candidate path: when `ExtractedFields.candidate_names` is non-empty, resolve each name to
  a candidate and use that candidate's best-matching profile, whatever the general ranking said.
  A name that resolves to nothing produces zero selections and a reason string saying so — never
  a silent substitution of a different person.
- A `profile_id` the model invents (not in the input pool) is discarded, not trusted.
- Empty ranking or a post-retry schema failure returns an empty list, which routes to
  `Needs review` downstream.

**Do not**
- Compose the draft or read resume files.

## Independence
Both the profile pool and `model_client` are arguments. Tests build `Profile` objects inline and
use a fake model returning canned rankings — no database, no Ollama, no P2-07.

## Acceptance criteria
- [ ] Two profiles belonging to one candidate never both survive selection
- [ ] Nothing below `min_score` is selected, even when that leaves zero matches
- [ ] Never more than `max_profiles` selected
- [ ] A named candidate wins over a higher-scoring different candidate
- [ ] An unknown named candidate yields zero selections and an explanatory reason
- [ ] A hallucinated `profile_id` is discarded
- [ ] Every returned `Match` carries a non-empty one-line `reason`

## Done when
`pytest tests/test_match_rerank.py` passes with a fake model client.

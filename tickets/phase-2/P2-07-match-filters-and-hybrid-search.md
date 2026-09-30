# P2-07: Hard filters and hybrid search

**Phase:** 2 · **Est:** 2 days · **Blocked by:** nothing

## Owns
- `pipeline/match_search.py`
- `tests/test_match_search.py`

## Reads
- `docs/CONTRACTS.md` §1 (`ExtractedFields`, `Profile`, `Match`), §4 (`match.hybrid_alpha`,
  `match.rerank_pool`)
- `docs/schema.reference.sql` (`profiles`)
- `email_agent/embedding_text.py` from P1-04 — **the contract is "same serialisation both sides"**

## Context
Retrieval, split from re-ranking so the two can be built and tuned separately. This half is
deterministic and cheap; the next half is a model call.

## Scope
**Do**
- Hard filters first, from `ExtractedFields`: location compatibility (remote, hybrid, on-site,
  city and region aliases), `notice_period_days` against any stated deadline, and
  `years_experience >= min_years_experience` with a configurable tolerance band.
- Hybrid retrieval: pgvector cosine similarity on `profiles.embedding` combined with keyword
  match on `skills` (GIN array overlap plus `pg_trgm` on title and summary).
- Normalise both scores to 0-1 before combining, then weight by `match.hybrid_alpha`. Document
  the normalisation — raw cosine and `ts_rank` are not comparable and must not be added directly.
- Return the top `match.rerank_pool` as `Match` with `stage="hybrid"`, `selected=False`.
- Only `active = true` and `reviewed = true` profiles are eligible.
- Query must be a single round trip; no N+1 per profile.

**Do not**
- Call a model, apply `min_score`, or cap profiles per candidate. That is P2-08.

## Independence
If P1-04 has not landed, copy `build_embedding_text` into place from the contract — identical
content, first one to merge wins. Tests seed a throwaway Postgres from
`docs/schema.reference.sql` with ~20 synthetic profiles and a deterministic fake embedder, so
neither P1-01 nor P1-04 nor Ollama is required.

## Acceptance criteria
- [ ] A profile failing any hard filter never appears, whatever its similarity
- [ ] Location aliases work: "Bangalore"/"Bengaluru", and a "remote" requirement does not exclude
      on-site candidates unless the requirement says on-site
- [ ] `hybrid_alpha = 1.0` gives pure vector order; `0.0` gives pure keyword order
- [ ] Both component scores are normalised to 0-1 before weighting
- [ ] Exactly `rerank_pool` results returned when more than that qualify
- [ ] Unreviewed and inactive profiles are excluded
- [ ] One SQL round trip, verified by query count in the test

## Done when
`pytest tests/test_match_search.py` passes against a seeded throwaway database.

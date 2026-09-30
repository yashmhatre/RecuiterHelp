# P1-04: Profile embeddings and the vector index

**Phase:** 1 · **Est:** 1 day · **Blocked by:** nothing

## Owns
- `profiles/embed_profiles.py`
- `email_agent/embedding_text.py`
- `tests/test_embed_profiles.py`

## Reads
- `docs/CONTRACTS.md` §1 (`Profile`), §3 (`embed()` shape)
- `docs/schema.reference.sql` (`profiles.embedding VECTOR(768)`)

## Context
Embeds reviewed profiles so hybrid search has something to search. The text that gets embedded is
a decision in its own right, so it lives in one named function that both this ticket and the
query side use.

## Scope
**Do**
- `build_embedding_text(profile) -> str`: the canonical serialisation — title, skills, years,
  summary — in a fixed order. **The same function must be used for the query side**, so put it in
  `email_agent/embedding_text.py` and nowhere else.
- `embed_profiles.py`: embed profiles where `reviewed = true` and (`embedding IS NULL` or the
  profile changed since it was embedded), in batches, resumable after interruption.
- `--force` to re-embed everything after a model change.
- Record the embedding model name and dimension in run output; refuse to write a vector whose
  dimension does not match the column.
- Verify the HNSW cosine index is used by the planner and note the `EXPLAIN` output in the PR.

**Do not**
- Write the search query (P2-07) or embed unreviewed profiles.

## Independence
Inject the embedding function; tests pass a deterministic fake returning a fixed 768-dim vector.
No Ollama needed. DB assertions run against a throwaway Postgres with the reference DDL applied
directly from `docs/schema.reference.sql` — this ticket does not need P1-01's migrations.

## Acceptance criteria
- [ ] Only `reviewed = true` profiles get embedded
- [ ] A second run embeds nothing new; `--force` re-embeds all
- [ ] Killing the process mid-run and restarting loses no work and repeats none
- [ ] A dimension mismatch is refused with a clear error naming both dimensions
- [ ] `build_embedding_text` is deterministic and defined in exactly one place
- [ ] `EXPLAIN` on a cosine nearest-neighbour query shows an index scan, not a sequential scan

## Done when
`pytest tests/test_embed_profiles.py` passes with a fake embedder.

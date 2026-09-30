# P0-02: Ollama runtime and JSON model client

**Phase:** 0 · **Est:** 1 day · **Blocked by:** nothing

## Owns
- `email_agent/models/ollama_client.py`
- `email_agent/models/__init__.py`
- `scripts/setup_ollama.sh`, `scripts/setup_ollama.ps1`
- `scripts/healthcheck_models.py`
- `tests/test_ollama_client.py`
- `docs/setup-ollama.md`

## Reads
- `docs/CONTRACTS.md` §3 (model call contract)

## Context
Two pipeline stages call a model and both need the same thing: a JSON response that matches a
schema, or a clean failure. That retry-and-validate behaviour belongs in one place so the
pipeline tickets never touch HTTP.

## Scope
**Do**
- Pull scripts for `qwen3:8b`, `qwen3:14b`, `nomic-embed-text`.
- `generate_json(prompt, schema, model, timeout) -> dict`: sets `format=json`, thinking off,
  `temperature=0`, validates against the JSON schema, **retries once**, then raises
  `ModelSchemaError`. This is the single retry §3 specifies.
- `embed(texts) -> list[list[float]]`, batched, returning 768-dim vectors.
- Record latency and token counts on the returned object so callers can log them.
- `healthcheck_models.py`: exits non-zero with a readable message if Ollama is down or a model
  is missing.
- `docs/setup-ollama.md`: RAM guidance (16 GB for 8B, 32 GB or GPU for 14B) and the CPU
  fallback to 8B for drafting.

**Do not**
- Write any prompt text — prompts belong to P2-06 and P2-08.
- Import anything from `pipeline/`.

## Independence
Tests run against a local `respx`/`responses` HTTP mock of the Ollama API. Add one
`@pytest.mark.integration` test, skipped unless `OLLAMA_HOST` is reachable, so CI is green
without Ollama installed.

## Acceptance criteria
- [ ] A schema-valid response returns a parsed dict
- [ ] A malformed response retries exactly once, then raises `ModelSchemaError`
- [ ] A response that is valid JSON but violates the schema is treated as malformed
- [ ] `embed()` returns 768 floats per input and batches inputs into one call
- [ ] Timeout raises `ModelTimeoutError`, not a bare `requests` exception
- [ ] Healthcheck reports each missing model by name

## Done when
`pytest tests/test_ollama_client.py` passes with no Ollama running.
